"""
Auto MDF InvoISys - Controle de Automação MDF-e (Execução Única)

Versão v0.5.0-Alpha-GUI:
- Executa um script por vez (não permite múltiplas execuções simultâneas)
- Interface não interfere com execução (scripts rodam de forma independente)
- GUI completamente responsiva
- Monitoramento em tempo real sem bloquear a GUI
- Histórico de todas as execuções
- Verificação de dependências sob demanda (quando erros ocorrem)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import os
import sys
import time
import subprocess
import json
import queue
from pathlib import Path
from datetime import datetime
from progress_manager import ProgressManager
import importlib.util

BASE_DIR = Path(__file__).resolve().parent
BRIDGE_PREFIX = "__MDF_GUI_BRIDGE__"
BRIDGE_ACK = "__MDF_GUI_ACK__"
BRIDGE_CANCEL = "__MDF_GUI_CANCEL__"


class DependencyChecker:
    """Verifica e gerencia instalação de dependências"""
    
    # Cache de verificação (válido por 5 minutos)
    _cache = {}
    _cache_timeout = 300  # segundos
    
    def __init__(self):
        self.required_packages = ['pyautogui', 'pyperclip']
        self.missing_packages = []
    
    def check_dependencies(self, use_cache=True):
        """Verifica se todas as dependências estão instaladas"""
        # Verificar cache primeiro
        if use_cache:
            cache_key = tuple(sorted(self.required_packages))
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self.missing_packages = cached_result
                return len(self.missing_packages) == 0
        
        # Verificação real
        self.missing_packages = []
        
        for package in self.required_packages:
            if not self._is_package_installed(package):
                self.missing_packages.append(package)
        
        # Atualizar cache
        if use_cache:
            self._save_to_cache(cache_key, self.missing_packages[:])
        
        return len(self.missing_packages) == 0
    
    @classmethod
    def _get_from_cache(cls, key):
        """Obtém resultado do cache se ainda válido"""
        if key in cls._cache:
            result, timestamp = cls._cache[key]
            if time.time() - timestamp < cls._cache_timeout:
                return result
            else:
                # Cache expirado, remover
                del cls._cache[key]
        return None
    
    @classmethod
    def _save_to_cache(cls, key, result):
        """Salva resultado no cache"""
        cls._cache[key] = (result, time.time())
    
    @classmethod
    def clear_cache(cls):
        """Limpa o cache de verificação"""
        cls._cache.clear()
    
    def _is_package_installed(self, package_name):
        """Verifica se um pacote está instalado"""
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    
    def get_missing_packages(self):
        """Retorna lista de pacotes faltantes"""
        return self.missing_packages
    
    @staticmethod
    def install_dependencies():
        """Tenta instalar as dependências automaticamente"""
        try:
            requirements_path = BASE_DIR / 'requirements.txt'

            # Verificar se requirements.txt existe
            if not requirements_path.exists():
                return False, "Arquivo 'requirements.txt' não encontrado"
            
            # Tentar instalar com pip
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_path), '--quiet'],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(BASE_DIR)
            )
            
            # Limpar cache após instalação
            DependencyChecker.clear_cache()
            
            if result.returncode == 0:
                return True, "Dependências instaladas com sucesso!"
            else:
                return False, f"Erro ao instalar: {result.stderr}"
        
        except Exception as e:
            return False, f"Erro: {str(e)}"


class ScriptExecutor:
    """Gerencia a execução independente de um script"""
    
    MAX_OUTPUT_LINES = 1000  # Limite máximo de linhas para evitar overflow de memória
    
    def __init__(self, script_path, script_name, execution_id):
        self.script_path = script_path
        self.script_name = script_name
        self.execution_id = execution_id
        self.process = None
        self.start_time = None
        self.end_time = None
        self.status = "idle"  # idle, running, paused, completed, error
        self.progress_file = BASE_DIR / f"progress_{execution_id}.json"
        self.output_lines = []
        self.monitoring_thread = None
        self.is_running = False
        self.update_queue = queue.Queue()  # Fila thread-safe para comunicação
        self.stdin_pipe = None
    
    def start(self):
        """Inicia a execução do script"""
        try:
            self.status = "running"
            self.is_running = True
            self.start_time = datetime.now()
            self.output_lines = []
            
            # Criar variável de ambiente com o ID de execução
            env = os.environ.copy()
            env['MDF_EXECUTION_ID'] = self.execution_id
            env['MDF_BRIDGE_ACTIVE'] = '1'
            env['MDF_BRIDGE_PREFIX'] = BRIDGE_PREFIX
            env['MDF_BRIDGE_ACK'] = BRIDGE_ACK
            env['MDF_BRIDGE_CANCEL'] = BRIDGE_CANCEL
            
            # Iniciar processo de forma completamente isolada
            self.process = subprocess.Popen(
                [sys.executable, self.script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                cwd=str(BASE_DIR)
            )
            self.stdin_pipe = self.process.stdin
            
            # Iniciar thread de monitoramento
            self.monitoring_thread = threading.Thread(
                target=self._monitor_execution,
                daemon=True
            )
            self.monitoring_thread.start()
            
            return True
        except Exception as e:
            self.status = "error"
            self.is_running = False
            self.output_lines.append(f"❌ Erro ao iniciar: {str(e)}")
            return False
    
    def _monitor_execution(self):
        """Monitora a execução do processo em thread separada"""
        try:
            # Ler output do processo linha por linha
            for line in self.process.stdout:
                if line:
                    line_stripped = line.rstrip()

                    if line_stripped.startswith(BRIDGE_PREFIX):
                        try:
                            payload_raw = line_stripped[len(BRIDGE_PREFIX):]
                            payload = json.loads(payload_raw)
                            self.update_queue.put(('dialog', payload), block=False)
                        except Exception:
                            self.output_lines.append(line_stripped)
                        continue

                    self.output_lines.append(line_stripped)
                    
                    # Limitar memória: manter apenas últimas MAX_OUTPUT_LINES linhas
                    if len(self.output_lines) > self.MAX_OUTPUT_LINES:
                        self.output_lines = self.output_lines[-self.MAX_OUTPUT_LINES:]
                    
                    # Eventos de linha não são necessários para a UI
            
            # Aguardar processo terminar
            self.process.wait()
            
            # Atualizar status baseado no código de retorno
            if self.process.returncode == 0:
                self.status = "completed"
                success_msg = "✅ Script concluído com sucesso!"
                self.output_lines.append(success_msg)
                self.update_queue.put(('status', 'completed'), block=False)
            else:
                failsafe_triggered = False
                for line in self.output_lines:
                    normalized = line.lower()
                    normalized_compact = normalized.replace('-', '').replace(' ', '')
                    if (
                        'pyautogui.failsafeexception' in normalized
                        or 'failsafe' in normalized_compact
                        or 'fail-safe' in normalized
                        or 'fail safe' in normalized
                    ):
                        failsafe_triggered = True
                        break

                if failsafe_triggered:
                    self.status = "failsafe"
                    message = "🛑 Execução interrompida pelo usuário (FailSafe)."
                    self.output_lines.append(message)
                    self.update_queue.put(('status', 'failsafe'), block=False)
                else:
                    self.status = "error"
                    error_msg = f"⚠️ Script terminou com código: {self.process.returncode}"
                    self.output_lines.append(error_msg)
                    self.update_queue.put(('status', 'error'), block=False)
        
        except Exception as e:
            self.status = "error"
            error_msg = f"❌ Erro no monitoramento: {str(e)}"
            self.output_lines.append(error_msg)
            self.update_queue.put(('status', 'error'), block=False)
        
        finally:
            self.end_time = datetime.now()
            self.is_running = False
    
    def stop(self):
        """Para a execução do script"""
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            
            self.status = "stopped"
            self.is_running = False
            self.output_lines.append("⏹ Script parado pelo usuário")
            self.update_queue.put(('status', 'stopped'), block=False)
    
    def send_bridge_response(self, message):
        """Envia resposta para o script via stdin"""
        if not self.stdin_pipe or self.stdin_pipe.closed:
            return

        try:
            if message is None:
                message = BRIDGE_CANCEL
            self.stdin_pipe.write(f"{message}\n")
            self.stdin_pipe.flush()
        except Exception:
            pass

    def cleanup(self):
        """Limpa recursos e memória ao finalizar"""
        # Limpar output para liberar memória
        if not self.is_running and len(self.output_lines) > 100:
            # Manter apenas últimas 100 linhas após conclusão
            self.output_lines = self.output_lines[-100:]
        
        # Limpar arquivo de progresso temporário
        if os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except:
                pass

        if self.stdin_pipe and not self.stdin_pipe.closed:
            try:
                self.stdin_pipe.close()
            except:
                pass
        self.stdin_pipe = None
    
    def get_elapsed_time(self):
        """Retorna tempo decorrido em formato HH:MM:SS"""
        if not self.start_time:
            return "00:00:00"
        
        end = self.end_time if self.end_time else datetime.now()
        elapsed = int((end - self.start_time).total_seconds())
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_progress(self):
        """Lê o arquivo de progresso se existir"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        return None


class DependencyInstallWindow:
    """Janela separada para instalação de dependências"""
    
    def __init__(self, parent, missing_packages, all_packages=None, initial_message=None):
        self.parent = parent
        self.missing_packages = missing_packages
        self.all_packages = all_packages or []
        self.initial_message = initial_message
        self.installation_complete = False

        self.window = tk.Toplevel(parent)
        self.window.title("⚠️  Instalação de Dependências (OBRIGATÓRIO)")
        self.window.geometry("640x520")
        self.window.minsize(620, 460)
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.lift()
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # Centralizar na tela
        self.window.transient(parent)
        self.window.grab_set()
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Cria widgets da janela de instalação"""
        
        # Área principal com suporte a rolagem
        body_frame = ttk.Frame(self.window)
        body_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(body_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        content_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=content_frame, anchor='nw')

        def _update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))

        content_frame.bind('<Configure>', _update_scroll_region)

        # Permitir rolagem com roda do mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        content_frame.bind('<Enter>', lambda _: canvas.bind_all('<MouseWheel>', _on_mousewheel))
        content_frame.bind('<Leave>', lambda _: canvas.unbind_all('<MouseWheel>'))

        # Garantir atualização inicial do scroll
        self.window.after(0, _update_scroll_region)

        # Header
        header_frame = ttk.Frame(content_frame)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        warning_label = ttk.Label(
            header_frame,
            text="⚠️  INSTALAÇÃO DE DEPENDÊNCIAS OBRIGATÓRIA",
            font=('Segoe UI', 12, 'bold'),
            foreground='#ef4444'
        )
        warning_label.pack(anchor=tk.W)
        
        description = ttk.Label(
            header_frame,
            text="As seguintes dependências precisam ser instaladas antes da primeira execução:",
            font=('Segoe UI', 10),
            foreground='#666'
        )
        description.pack(anchor=tk.W, pady=(10, 0))
        
        # Lista de pacotes
        packages_frame = ttk.LabelFrame(content_frame, text="Pacotes Faltantes", padding=15)
        packages_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        if self.missing_packages:
            for package in self.missing_packages:
                pkg_label = ttk.Label(
                    packages_frame,
                    text=f"• {package}",
                    font=('Segoe UI', 10),
                    foreground='#ef4444'
                )
                pkg_label.pack(anchor=tk.W, pady=3)
        else:
            ttk.Label(
                packages_frame,
                text="Nenhuma dependência obrigatória faltando.",
                font=('Segoe UI', 10),
                foreground='#10b981'
            ).pack(anchor=tk.W, pady=3)
            if self.all_packages:
                ttk.Label(
                    packages_frame,
                    text="Dependências monitoradas:",
                    font=('Segoe UI', 9, 'italic'),
                    foreground='#666'
                ).pack(anchor=tk.W, pady=(10, 3))
                for package in self.all_packages:
                    ttk.Label(
                        packages_frame,
                        text=f"• {package}",
                        font=('Segoe UI', 9),
                        foreground='#1e3a8a'
                    ).pack(anchor=tk.W)
        
        # Informações sobre instalação
        info_frame = ttk.LabelFrame(content_frame, text="Opções de Instalação", padding=15)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        option1_label = ttk.Label(
            info_frame,
            text="Opção 1: Instalação Automática (Recomendado)",
            font=('Segoe UI', 10, 'bold'),
            foreground='#0066cc'
        )
        option1_label.pack(anchor=tk.W, pady=(0, 5))
        
        option1_desc = ttk.Label(
            info_frame,
            text="Clique em 'Instalar Agora' para instalar automaticamente.\nA instalação usa a conta do usuário Windows.",
            font=('Segoe UI', 9),
            foreground='#666'
        )
        option1_desc.pack(anchor=tk.W, pady=(0, 15))
        
        option2_label = ttk.Label(
            info_frame,
            text="Opção 2: Instalação Manual",
            font=('Segoe UI', 10, 'bold'),
            foreground='#0066cc'
        )
        option2_label.pack(anchor=tk.W, pady=(0, 5))
        
        option2_desc = ttk.Label(
            info_frame,
            text="Execute um dos arquivos de instalação no diretório do projeto:\n"
            "• install.bat (cria um virtualenv isolado)\n"
            "• install_user.bat (instala no perfil do usuário)",
            font=('Segoe UI', 9),
            foreground='#666'
        )
        option2_desc.pack(anchor=tk.W, pady=(0, 0))
        
        # Status de instalação
        status_text = self.initial_message or "Aguardando ação..."
        status_color = '#666'
        if self.initial_message and '✅' in self.initial_message:
            status_color = '#10b981'
        elif self.initial_message and '⚠️' in self.initial_message:
            status_color = '#f59e0b'
        
        footer_frame = ttk.Frame(self.window)
        footer_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        self.status_label = ttk.Label(
            footer_frame,
            text=status_text,
            font=('Segoe UI', 9),
            foreground=status_color
        )
        self.status_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Botões
        button_frame = ttk.Frame(footer_frame)
        button_frame.pack(fill=tk.X)
        
        self.install_btn = ttk.Button(
            button_frame,
            text="📥 Instalar Agora",
            command=self._install_now,
            style='Accent.TButton'
        )
        self.install_btn.pack(side=tk.LEFT, padx=5)
        
        self.retry_btn = ttk.Button(
            button_frame,
            text="🔄 Verificar Novamente",
            command=self._check_again
        )
        self.retry_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(
            button_frame,
            text="❌ Cancelar",
            command=self.on_cancel
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def _install_now(self):
        """Instala as dependências automaticamente"""
        self.install_btn.config(state=tk.DISABLED)
        self.retry_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        
        self.status_label.config(
            text="⏳ Instalando dependências... Por favor, aguarde (pode levar 1-2 minutos)...",
            foreground='#f59e0b'
        )
        self.window.update()
        
        # Executar instalação em thread
        threading.Thread(target=self._run_installation, daemon=True).start()
    
    def _run_installation(self):
        """Executa a instalação em background"""
        success, message = DependencyChecker.install_dependencies()
        
        if success:
            self.status_label.config(text=f"✅ {message}", foreground='#10b981')
            self.installation_complete = True
            
            # Aguardar 2 segundos e fechar
            time.sleep(2)
            self.window.destroy()
        else:
            self.status_label.config(
                text=f"❌ {message}\n\nTente usar o install.bat ou install_user.bat manualmente.",
                foreground='#ef4444'
            )
            
            self.install_btn.config(state=tk.NORMAL)
            self.retry_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.NORMAL)
    
    def _check_again(self):
        """Verifica as dependências novamente"""
        checker = DependencyChecker()
        if checker.check_dependencies():
            self.status_label.config(
                text="✅ Todas as dependências estão instaladas!",
                foreground='#10b981'
            )
            self.installation_complete = True
            
            time.sleep(1)
            self.window.destroy()
        else:
            self.status_label.config(
                text="❌ Ainda há pacotes faltantes. Tente novamente.",
                foreground='#ef4444'
            )
    
    def on_cancel(self):
        """Cancela a instalação"""
        if messagebox.askyesno(
            "Cancelar",
            "As dependências são OBRIGATÓRIAS para usar a automação.\n\n"
            "Tem certeza que deseja cancelar?"
        ):
            self.window.destroy()
            self.parent.destroy()


class MDFAutomationGUIv2:
    """Interface gráfica principal com execução única"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Auto MDF InvoISys - Control Center v0.5.0-Alpha-GUI")
        self.root.geometry("1080x720")
        self.root.minsize(920, 600)
        self.root.resizable(True, True)
        self.root.attributes("-topmost", False)
        self.topmost_var = tk.BooleanVar(value=False)
        self.execution_window_state = {'was_iconified': False, 'was_topmost': False}
        
        # Inicializar verificador de dependências (sem verificação obrigatória)
        self.dependency_checker = DependencyChecker()
        
        # Gerenciamento de execução (UMA POR VEZ)
        self.current_execution: ScriptExecutor = None
        self.execution_history: list = []
        self.update_thread = None
        self.should_continue_updating = True
        
        # Configurar estilo
        self._setup_styles()
        
        # Criar interface
        self.create_widgets()
        self.load_scripts()
        
        # Iniciar thread de atualização
        self.start_update_loop()
        
        # Handler para fechar a janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _setup_styles(self):
        """Configura estilos da interface"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'), foreground='#1e3a8a')
        style.configure('Status.TLabel', font=('Segoe UI', 10), foreground='#666')
        style.configure('Success.TLabel', foreground='#10b981')
        style.configure('Error.TLabel', foreground='#ef4444')
        style.configure('Warning.TLabel', foreground='#f59e0b')
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Running.TLabel', foreground='#0066cc')
    
    def _toggle_topmost(self):
        """Alterna o estado 'sempre no topo' da janela principal"""
        self.root.attributes("-topmost", self.topmost_var.get())

    def create_widgets(self):
        """Cria todos os widgets da interface"""
        
        # Criar notebook (abas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Aba 1: Controle de Execução
        self.control_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.control_frame, text="🎛️  Controle")
        self._create_control_tab()
        
        # Aba 2: Execução Atual
        self.execution_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.execution_frame, text="▶️  Em Execução")
        self._create_execution_tab()
        
        # Aba 3: Histórico
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="📜 Histórico")
        self._create_history_tab()
    
    def _create_control_tab(self):
        """Cria a aba de controle"""
        
        # Cabeçalho
        header_frame = ttk.Frame(self.control_frame)
        header_frame.pack(fill=tk.X, padx=15, pady=15)
        
        title = ttk.Label(header_frame, text="🚀 Auto MDF InvoISys - Control Center v0.5.0-Alpha-GUI", style='Title.TLabel')
        title.pack(anchor=tk.W)
        
        subtitle = ttk.Label(header_frame, text="Execute scripts de automação com monitoramento em tempo real", style='Status.TLabel')
        subtitle.pack(anchor=tk.W, pady=(5, 0))

        pin_frame = ttk.Frame(self.control_frame)
        pin_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        self.topmost_checkbox = ttk.Checkbutton(
            pin_frame,
            text="📌 Manter janela principal sempre visível (opcional)",
            variable=self.topmost_var,
            command=self._toggle_topmost
        )
        self.topmost_checkbox.pack(anchor=tk.W)
        
        # Seção de seleção e execução
        select_frame = ttk.LabelFrame(self.control_frame, text="📋 Selecionar Script", padding=10)
        select_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        ttk.Label(select_frame, text="Escolha o script:").pack(anchor=tk.W, pady=(0, 5))
        
        self.script_var = tk.StringVar()
        self.script_combo = ttk.Combobox(select_frame, textvariable=self.script_var, state='readonly', width=60)
        self.script_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Botões de controle
        button_frame = ttk.Frame(select_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(
            button_frame, 
            text="▶ Iniciar Execução", 
            command=self.start_new_execution,
            style='Accent.TButton'
        )
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹ Parar",
            command=self.stop_execution,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(button_frame, text="🗑 Limpar Histórico", command=self.clear_history).pack(side=tk.LEFT, padx=2)
        
        # Separador e botão de dependências
        ttk.Separator(select_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        deps_label = ttk.Label(
            select_frame,
            text="⚙️  Gerenciamento de Dependências",
            font=('Segoe UI', 10, 'bold'),
            foreground='#1e3a8a'
        )
        deps_label.pack(anchor=tk.W, pady=(0, 8))
        
        deps_frame = ttk.Frame(select_frame)
        deps_frame.pack(fill=tk.X)
        
        self.install_deps_btn = ttk.Button(
            deps_frame,
            text="📥 Instalar Dependências",
            command=self._install_dependencies_manual
        )
        self.install_deps_btn.pack(side=tk.LEFT, padx=2)
        
        self.check_deps_btn = ttk.Button(
            deps_frame,
            text="✓ Verificar Dependências",
            command=self._check_dependencies_status
        )
        self.check_deps_btn.pack(side=tk.LEFT, padx=2)
        
        # Informações
        info_frame = ttk.LabelFrame(self.control_frame, text="ℹ️  Informações", padding=10)
        info_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.info_label = ttk.Label(info_frame, text="Pronto para iniciar", foreground='#666')
        self.info_label.pack(anchor=tk.W)
        
        self.stats_label = ttk.Label(info_frame, text="", foreground='#666')
        self.stats_label.pack(anchor=tk.W, pady=(5, 0))
    
    def _create_execution_tab(self):
        """Cria a aba de script em execução"""
        
        header = ttk.Label(
            self.execution_frame,
            text="📊 Script em Execução (em segundo plano)",
            font=('Segoe UI', 12, 'bold'),
            foreground='#1e3a8a'
        )
        header.pack(fill=tk.X, padx=15, pady=15)
        
        # Container para a execução atual
        self.execution_container = ttk.Frame(self.execution_frame)
        self.execution_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Placeholder inicial
        placeholder = ttk.Label(
            self.execution_container,
            text="Nenhum script em execução.\nSelecione um script na aba 'Controle' e clique 'Iniciar Execução'.",
            foreground='#999',
            font=('Segoe UI', 11)
        )
        placeholder.pack(expand=True)
        self.execution_placeholder = placeholder
        self.current_execution_widget = None
    
    def _create_history_tab(self):
        """Cria a aba de histórico"""
        
        header = ttk.Label(
            self.history_frame,
            text="📜 Histórico de Execuções",
            font=('Segoe UI', 12, 'bold'),
            foreground='#1e3a8a'
        )
        header.pack(fill=tk.X, padx=15, pady=15)
        
        # Botões
        button_frame = ttk.Frame(self.history_frame)
        button_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        ttk.Button(button_frame, text="💾 Salvar Histórico", command=self.save_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🗑 Limpar Histórico", command=self.clear_history).pack(side=tk.LEFT, padx=2)
        
        # Texto de histórico
        self.history_text = scrolledtext.ScrolledText(
            self.history_frame,
            height=20,
            width=100,
            font=('Consolas', 9)
        )
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Configurar tags de cor
        self.history_text.tag_configure('info', foreground='#0066cc')
        self.history_text.tag_configure('success', foreground='#10b981')
        self.history_text.tag_configure('error', foreground='#ef4444')
        self.history_text.tag_configure('warning', foreground='#f59e0b')
        self.history_text.tag_configure('timestamp', foreground='#666')
    
    def load_scripts(self):
        """Carrega os scripts disponíveis"""
        self.scripts = {}
        current_dir = BASE_DIR

        script_files = list(current_dir.glob('*.py'))

        for script_file in script_files:
            name = script_file.name.lower()
            display_name = script_file.stem

            # Filtrar scripts de automação
            if any(x in name for x in ['itu', 'sorocaba', 'dhl']) and 'gui' not in name and 'progress' not in name:
                self.scripts[display_name] = str(script_file.resolve())

        if not self.scripts:
            for script_file in script_files:
                if script_file.name not in ['AutoMDF-Start.py', 'progress_manager.py', 'mdf_automation_gui.py']:
                    self.scripts[script_file.stem] = str(script_file.resolve())

        self.script_combo['values'] = list(self.scripts.keys())
        if self.scripts:
            self.script_combo.current(0)

        self.info_label.config(text=f"Scripts encontrados: {len(self.scripts)} em {str(current_dir)}")
    
    def start_new_execution(self):
        """Inicia uma nova execução de script"""
        # Verificar dependências antes de executar
        if not self.dependency_checker.check_dependencies():
            missing = self.dependency_checker.get_missing_packages()
            response = messagebox.showwarning(
                "Dependências Faltando",
                f"❌ As seguintes dependências estão faltando:\n\n"
                f"{', '.join(missing)}\n\n"
                f"É OBRIGATÓRIO instalar as dependências antes de executar scripts.\n\n"
                f"Deseja instalar agora?",
                type=messagebox.YESNO
            )
            
            if response == messagebox.YES:
                self._install_dependencies_manual()
            
            return
        
        # Verificar se já há execução em andamento
        if self.current_execution and self.current_execution.is_running:
            messagebox.showwarning(
                "Execução em Andamento",
                f"Um script já está em execução: {self.current_execution.script_name}\n\n"
                f"Tempo decorrido: {self.current_execution.get_elapsed_time()}\n\n"
                f"Aguarde a conclusão ou clique em 'Parar' para interromper."
            )
            return
        
        script_name = self.script_var.get()
        
        if not script_name:
            messagebox.showwarning("Aviso", "Selecione um script primeiro!")
            return
        
        script_path = self.scripts.get(script_name)
        if not script_path or not os.path.exists(script_path):
            messagebox.showerror("Erro", f"Script não encontrado: {script_path}")
            return
        
        # Criar executor
        execution_id = f"{script_name}_{int(time.time())}"
        
        executor = ScriptExecutor(script_path, script_name, execution_id)
        self.current_execution = executor

        # Reorganizar janelas: alertas (topmost) > GUI > navegador
        previous_state = {
            'was_iconified': self.root.state() in ('iconic', 'iconified', 'withdrawn'),
            'was_topmost': self.topmost_var.get()
        }
        self.execution_window_state = previous_state

        if previous_state['was_iconified']:
            self.root.deiconify()

        # Trazer a GUI para frente sem deixá-la permanentemente topmost
        if previous_state['was_topmost']:
            self.topmost_var.set(False)
            self._toggle_topmost()

        self.root.attributes('-topmost', True)
        self.root.update_idletasks()
        self.root.lift()
        self.root.attributes('-topmost', False)
        self.root.update_idletasks()

        if hasattr(self, 'topmost_checkbox'):
            self.topmost_checkbox.state(['disabled'])

        window_event_message = "🪟 Janela principal posicionada acima do navegador (alertas permanecem em primeiro plano)."
        
        # Iniciar execução em thread
        threading.Thread(
            target=executor.start,
            daemon=True
        ).start()
        
        # Criar widget de execução
        self._create_execution_widget(executor)

        # Registrar evento da janela no log da execução
        self._append_log_message(window_event_message, 'info')
        
        # Log
        self._log_to_history(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando: {script_name}", 'info')
        
        # Trocar para aba de execuções
        self.notebook.select(1)
        
        # Atualizar botões
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.script_combo.config(state=tk.DISABLED)
        
        # Atualizar stats
        self._update_stats()
    
    def _create_execution_widget(self, executor):
        """Cria widget para exibir a execução atual"""
        
        # Limpar placeholder
        if self.execution_placeholder:
            self.execution_placeholder.pack_forget()
        
        # Remover widget anterior se existir
        if self.current_execution_widget:
            self.current_execution_widget.destroy()
        
        # Frame da execução
        exec_frame = ttk.LabelFrame(
            self.execution_container,
            text=f"🔹 {executor.script_name}",
            padding=10
        )
        exec_frame.pack(fill=tk.BOTH, expand=True)
        
        # Informações da execução
        info_line = ttk.Frame(exec_frame)
        info_line.pack(fill=tk.X, pady=(0, 8))

        status_label = ttk.Label(info_line, text="🔄 Executando...", foreground='#0066cc')
        status_label.pack(side=tk.LEFT, padx=(0, 20))

        time_label = ttk.Label(info_line, text="00:00:00")
        time_label.pack(side=tk.LEFT, padx=(0, 20))

        # Barra de progresso compacta para executar scripts longos
        progress_frame = ttk.Frame(exec_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate', maximum=100)
        progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        progress_label = ttk.Label(progress_frame, text="0%")
        progress_label.pack(side=tk.LEFT)

        # Botões de controle
        button_frame = ttk.Frame(exec_frame)
        button_frame.pack(fill=tk.X, pady=(0, 8))

        copy_btn = ttk.Button(
            button_frame,
            text="📋 Copiar Log",
            command=lambda: self._copy_log()
        )
        copy_btn.pack(side=tk.LEFT, padx=2)

        # Output do script
        output_text = scrolledtext.ScrolledText(exec_frame, height=8, width=100, font=('Consolas', 9))
        output_text.pack(fill=tk.BOTH, expand=True)
        output_text.tag_configure('info', foreground='#0066cc')
        output_text.tag_configure('success', foreground='#10b981')
        output_text.tag_configure('error', foreground='#ef4444')
        output_text.tag_configure('warning', foreground='#f97316')
        
        # Armazenar referências
        self.current_execution_widget = exec_frame
        self.execution_widgets = {
            'frame': exec_frame,
            'status_label': status_label,
            'time_label': time_label,
            'progress_bar': progress_bar,
            'progress_label': progress_label,
            'output_text': output_text,
            'last_status': None,
            'last_progress_step': -1,
            'last_output_index': 0,
            'finalized': False
        }

        self._append_log_message(
            f"🟢 Preparando execução do script '{executor.script_name}'. Acompanhe as atualizações abaixo.",
            'info'
        )
    
    def stop_execution(self):
        """Para a execução atual"""
        if self.current_execution and self.current_execution.is_running:
            if messagebox.askyesno("Confirmação", f"Deseja parar o script '{self.current_execution.script_name}'?"):
                self.current_execution.stop()
                self._log_to_history(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Parado: {self.current_execution.script_name}",
                    'warning'
                )
    
    def _copy_log(self):
        """Copia o log para clipboard"""
        if hasattr(self, 'execution_widgets') and self.execution_widgets:
            log_content = self.execution_widgets['output_text'].get('1.0', tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            messagebox.showinfo("Sucesso", "Log copiado para clipboard!")

    def _append_log_message(self, text, tag='info'):
        """Adiciona uma linha amigável ao log da execução atual"""
        if not hasattr(self, 'execution_widgets') or not self.execution_widgets:
            return

        output_text = self.execution_widgets.get('output_text')
        if not output_text:
            return

        output_text.insert(tk.END, text + '\n', tag)
        output_text.see(tk.END)

    def _status_to_log_message(self, status, executor):
        """Retorna mensagem amigável para o status informado"""
        script_name = executor.script_name
        elapsed = executor.get_elapsed_time()

        if status == "running":
            return f"🚀 Execução iniciada para o script '{script_name}'."
        if status == "completed":
            return f"✅ Script concluído com sucesso em {elapsed}."
        if status == "failsafe":
            return f"🛑 Execução interrompida manualmente (FailSafe) após {elapsed}."
        if status == "error":
            return f"❌ Ocorreu um erro durante a execução (tempo decorrido: {elapsed}). Confira os detalhes acima."
        if status == "stopped":
            return f"⏹ Execução cancelada pelo usuário após {elapsed}."
        if status == "idle":
            return "⏳ Script aguardando início da execução."

        return None

    def _status_to_tag(self, status):
        """Seleciona a tag de cor adequada para mensagens de status"""
        return {
            "running": 'info',
            "completed": 'success',
            "failsafe": 'warning',
            "error": 'error',
            "stopped": 'warning',
            "idle": 'info'
        }.get(status, 'info')
    
    def start_update_loop(self):
        """Inicia loop de atualização da interface"""
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def _update_loop(self):
        """Loop de atualização em background"""
        while self.should_continue_updating:
            try:
                self.root.after(800, self._update_execution)  # Otimizado: 500ms → 800ms
                time.sleep(0.8)
            except:
                pass
    
    def _update_execution(self):
        """Atualiza status da execução atual"""
        if not self.root.winfo_exists():
            return
        
        if self.current_execution and hasattr(self, 'execution_widgets') and self.execution_widgets:
            executor = self.current_execution
            widgets = self.execution_widgets
            self._process_executor_events(executor)
            
            # Atualizar status
            if executor.status == "running":
                status_text = "🔄 Executando..."
                status_color = '#0066cc'
            elif executor.status == "completed":
                status_text = "✅ Concluído"
                status_color = '#10b981'
            elif executor.status == "failsafe":
                status_text = "🛑 FailSafe acionado"
                status_color = '#f97316'
            elif executor.status == "error":
                status_text = "❌ Erro"
                status_color = '#ef4444'
            elif executor.status == "stopped":
                status_text = "⏹ Parado"
                status_color = '#f59e0b'
            else:
                status_text = "⏳ Aguardando..."
                status_color = '#666'
            
            widgets['status_label'].config(text=status_text, foreground=status_color)
            widgets['time_label'].config(text=executor.get_elapsed_time())

            previous_status = widgets.get('last_status')
            current_status = executor.status
            if previous_status != current_status:
                status_message = self._status_to_log_message(current_status, executor)
                if status_message:
                    self._append_log_message(status_message, self._status_to_tag(current_status))
                widgets['last_status'] = current_status
            
            # Atualizar output
            last_index = widgets.get('last_output_index', 0)
            new_lines = executor.output_lines[last_index:]
            
            for line in new_lines:
                if line:
                    tag = 'info'
                    if '✅' in line or 'sucesso' in line.lower():
                        tag = 'success'
                    elif '🛑' in line or 'failsafe' in line.lower() or 'fail-safe' in line.lower():
                        tag = 'warning'
                    elif '❌' in line or 'erro' in line.lower():
                        tag = 'error'
                    
                    self._append_log_message(line, tag)
            if new_lines:
                widgets['last_output_index'] = last_index + len(new_lines)
            
            # Atualizar progresso se disponível
            progress = executor.get_progress()
            if progress:
                percentage = max(0, min(100, int(progress.get('percentage', 0))))
                widgets['progress_label'].config(text=f"{percentage}%")
                widgets['progress_bar'].config(value=percentage)
                step = percentage // 10
                last_step = widgets.get('last_progress_step', -1)
                if step > 0 and step != last_step:
                    self._append_log_message(f"📈 Progresso atualizado: {percentage}% concluído.")
                    widgets['last_progress_step'] = step
            
            # Se execução terminou
            if not executor.is_running and not widgets.get('finalized'):
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.script_combo.config(state='readonly')

                # Limpar memória
                executor.cleanup()

                # Adicionar ao histórico apenas uma vez por execução
                if executor.status == "completed":
                    widgets['progress_bar'].config(value=100)
                    widgets['progress_label'].config(text="100%")
                    widgets['last_progress_step'] = 10
                    self._log_to_history(
                        f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Concluído: {executor.script_name} ({executor.get_elapsed_time()})",
                        'success'
                    )
                elif executor.status == "failsafe":
                    self._log_to_history(
                        f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 FailSafe acionado: {executor.script_name} ({executor.get_elapsed_time()})",
                        'warning'
                    )
                elif executor.status == "error":
                    # VERIFICAR DEPENDÊNCIAS APENAS QUANDO HÁ ERRO
                    self._log_to_history(
                        f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erro: {executor.script_name} ({executor.get_elapsed_time()})",
                        'error'
                    )

                    # Verificar se é erro de dependências
                    output_combined = '\n'.join(executor.output_lines).lower()
                    if any(keyword in output_combined for keyword in ['modulenotfounderror', 'importerror', 'no module named']):
                        self._log_to_history(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Detectado erro de módulo - Verificando dependências...",
                            'warning'
                        )
                        self._check_and_suggest_dependencies()

                widgets['finalized'] = True
                self.current_execution = None
                state_snapshot = getattr(self, 'execution_window_state', {'was_iconified': False, 'was_topmost': False})

                if state_snapshot.get('was_iconified'):
                    self.root.iconify()
                else:
                    self.root.deiconify()
                    self.root.lift()

                self.topmost_var.set(state_snapshot.get('was_topmost', False))
                self._toggle_topmost()
                if not state_snapshot.get('was_topmost', False):
                    # Garantir que não fique preso em topmost ao restaurar
                    self.root.attributes('-topmost', False)

                if hasattr(self, 'topmost_checkbox'):
                    self.topmost_checkbox.state(['!disabled'])

                self._append_log_message("🪟 Janela principal restaurada após a execução.", 'info')
                self.execution_window_state = {'was_iconified': False, 'was_topmost': False}
        
        # Atualizar stats
        self._update_stats()

    def _process_executor_events(self, executor):
        """Processa eventos enviados pelo executor (ex: prompts)"""
        if not executor:
            return

        while True:
            try:
                event_type, payload = executor.update_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == 'dialog':
                self._handle_dialog_event(executor, payload)
            else:
                # Eventos de status já são tratados no fluxo principal
                continue

    def _handle_dialog_event(self, executor, payload):
        """Mostra diálogos solicitados pelo script dentro da GUI"""
        dialog_type = payload.get('type')
        title = payload.get('title') or "Auto MDF InvoISys"
        message = payload.get('text') or ""

        if dialog_type == 'alert':
            self._append_log_message(f"🔔 Alerta do script: {message}", 'info')
            messagebox.showinfo(title, message, parent=self.root)
            executor.send_bridge_response(BRIDGE_ACK)
            return

        if dialog_type == 'prompt':
            self._append_log_message(f"📝 Entrada solicitada: {message}", 'info')
            default = payload.get('default', '')
            response = simpledialog.askstring(title, message, parent=self.root, initialvalue=default)
            if response is None:
                executor.send_bridge_response(BRIDGE_CANCEL)
            else:
                executor.send_bridge_response(response)
            return

        if dialog_type == 'confirm':
            self._append_log_message(f"❓ Confirmação solicitada: {message}", 'info')
            buttons = payload.get('buttons') or ['OK', 'Cancel']
            choice = self._show_custom_confirm(title, message, buttons)
            if choice is None:
                executor.send_bridge_response(BRIDGE_CANCEL)
            else:
                executor.send_bridge_response(choice)
            return

        # Caso não reconheça, apenas confirma para evitar travar o script
        executor.send_bridge_response(BRIDGE_ACK)

    def _show_custom_confirm(self, title, message, buttons):
        """Exibe diálogo de confirmação com botões personalizados"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)

        result = {'value': None}

        def on_select(value):
            result['value'] = value
            dialog.destroy()

        def on_close():
            result['value'] = None
            dialog.destroy()

        dialog.protocol('WM_DELETE_WINDOW', on_close)

        label = ttk.Label(dialog, text=message, justify=tk.LEFT, wraplength=440)
        label.pack(padx=24, pady=(20, 12))

        button_frame = ttk.Frame(dialog)
        button_frame.pack(padx=24, pady=(0, 20), fill=tk.X)

        for idx, button_text in enumerate(buttons):
            btn = ttk.Button(button_frame, text=button_text, command=lambda val=button_text: on_select(val))
            btn.grid(row=idx // 3, column=idx % 3, padx=4, pady=4, sticky='ew')

        for col in range(min(3, len(buttons))):
            button_frame.grid_columnconfigure(col, weight=1)

        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        dialog.focus_force()
        dialog.wait_window()

        return result['value']
    
    def _update_stats(self):
        """Atualiza estatísticas"""
        if self.current_execution:
            status = self.current_execution.status
            if self.current_execution.is_running:
                status_display = "em execução"
            else:
                status_display = status
                if status == "failsafe":
                    status_display = "FailSafe acionado"
            
            stats_text = f"Status: {status_display} | Tempo: {self.current_execution.get_elapsed_time()}"
        else:
            stats_text = "Nenhuma execução em andamento"
        
        self.stats_label.config(text=stats_text)
    
    def _log_to_history(self, message, msg_type='info'):
        """Adiciona mensagem ao histórico"""
        self.history_text.insert(tk.END, message + '\n', msg_type)
        self.history_text.see(tk.END)
    
    def save_history(self):
        """Salva o histórico em arquivo"""
        history_content = self.history_text.get('1.0', tk.END)
        
        filename = f"mdf_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(history_content)
            
            messagebox.showinfo("Sucesso", f"Histórico salvo em:\n{filename}")
            self._log_to_history(f"[{datetime.now().strftime('%H:%M:%S')}] Histórico salvo: {filename}", 'info')
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar histórico:\n{str(e)}")
    
    def clear_history(self):
        """Limpa o histórico"""
        if messagebox.askyesno("Confirmação", "Deseja realmente limpar o histórico?"):
            self.history_text.delete('1.0', tk.END)
            self._log_to_history(f"[{datetime.now().strftime('%H:%M:%S')}] Histórico limpo", 'info')
    
    def _install_dependencies_manual(self):
        """Abre janela para instalar dependências manualmente"""
        # Atualiza status das dependências para mostrar informação real
        if not self.dependency_checker.check_dependencies(use_cache=False):
            missing = self.dependency_checker.get_missing_packages()
            initial_message = "⚠️ Dependências obrigatórias pendentes."
        else:
            missing = []
            initial_message = "✅ Todas as dependências estão instaladas. Você pode reinstalar se desejar."

        install_window = DependencyInstallWindow(
            self.root,
            missing_packages=missing,
            all_packages=list(self.dependency_checker.required_packages),
            initial_message=initial_message
        )
        self.root.wait_window(install_window.window)
        
        if install_window.installation_complete:
            # Re-verificar dependências
            self.dependency_checker = DependencyChecker()
            self._check_dependencies_status()
    
    def _check_dependencies_status(self):
        """Verifica e exibe status das dependências"""
        self.dependency_checker = DependencyChecker()
        
        if self.dependency_checker.check_dependencies():
            messagebox.showinfo(
                "✅ Dependências OK",
                "Todas as dependências estão instaladas corretamente!\n\n"
                "Você pode executar os scripts sem problemas."
            )
            self._log_to_history(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Verificação de dependências: OK",
                'success'
            )
        else:
            missing = self.dependency_checker.get_missing_packages()
            response = messagebox.showwarning(
                "❌ Dependências Faltando",
                f"As seguintes dependências estão faltando:\n\n"
                f"{', '.join(missing)}\n\n"
                f"É obrigatório instalar antes de usar a automação.\n\n"
                f"Deseja instalar agora?",
                type=messagebox.YESNO
            )
            
            if response == messagebox.YES:
                self._install_dependencies_manual()
            
            self._log_to_history(
                f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Verificação de dependências: Faltando {', '.join(missing)}",
                'error'
            )
    
    def _check_and_suggest_dependencies(self):
        """Verifica dependências quando erro é detectado e sugere instalação"""
        self.dependency_checker = DependencyChecker()
        
        if not self.dependency_checker.check_dependencies():
            missing = self.dependency_checker.get_missing_packages()
            
            response = messagebox.showwarning(
                "⚠️  Erro de Módulo Detectado",
                f"O script encontrou um erro de módulo não encontrado.\n\n"
                f"Dependências faltando: {', '.join(missing)}\n\n"
                f"Deseja instalar as dependências agora?",
                type=messagebox.YESNO
            )
            
            if response == messagebox.YES:
                self._install_dependencies_manual()
            
            self._log_to_history(
                f"[{datetime.now().strftime('%H:%M:%S')}] 📥 Faltando: {', '.join(missing)}",
                'error'
            )
        else:
            self._log_to_history(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Todas as dependências estão instaladas",
                'success'
            )
    
    def on_closing(self):
        """Handler para fechar a janela"""
        if messagebox.askokcancel("Sair", "Deseja sair? Script em execução será parado."):
            self.should_continue_updating = False
            
            # Parar execução se estiver rodando
            if self.current_execution and self.current_execution.is_running:
                self.current_execution.stop()
            
            self.root.destroy()


def main():
    root = tk.Tk()
    app = MDFAutomationGUIv2(root)
    root.mainloop()


if __name__ == "__main__":
    main()
