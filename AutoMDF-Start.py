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
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
import sys
import time
import subprocess
import json
import queue
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from progress_manager import ProgressManager
import importlib.util

try:
    import pyautogui  # type: ignore
except Exception:
    pyautogui = None

if os.name == 'nt':
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    SW_RESTORE = 9

    SetWindowPos = _user32.SetWindowPos  # type: ignore[attr-defined]
    SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        wintypes.INT,
        wintypes.INT,
        wintypes.INT,
        wintypes.INT,
        wintypes.UINT,
    ]
    SetWindowPos.restype = wintypes.BOOL

    SetForegroundWindow = _user32.SetForegroundWindow
    BringWindowToTop = _user32.BringWindowToTop
    ShowWindow = _user32.ShowWindow
    EnumWindows = _user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    IsWindowVisible = _user32.IsWindowVisible
    GetWindowTextLengthW = _user32.GetWindowTextLengthW
    GetWindowTextW = _user32.GetWindowTextW
    GetForegroundWindow = _user32.GetForegroundWindow
else:
    ctypes = None  # type: ignore
    wintypes = None  # type: ignore
    SetWindowPos = None
    SetForegroundWindow = None
    BringWindowToTop = None
    ShowWindow = None
    EnumWindows = None
    EnumWindowsProc = None
    IsWindowVisible = None
    GetWindowTextLengthW = None
    GetWindowTextW = None
    GetForegroundWindow = None

try:
    import pygetwindow as gw  # type: ignore
except Exception:
    gw = None

BROWSER_WINDOW_KEYWORDS = [
    'google chrome',
    'microsoft edge',
    'mozilla firefox',
    'brave',
    'opera',
    'opera gx'
]

BASE_DIR = Path(__file__).resolve().parent
BRIDGE_PREFIX = "__MDF_GUI_BRIDGE__"
BRIDGE_ACK = "__MDF_GUI_ACK__"
BRIDGE_CANCEL = "__MDF_GUI_CANCEL__"


class BrowserFocusGuardian:
    """Mantém o navegador ativo enquanto a GUI permanece visível."""

    def __init__(
        self,
        gui_title_supplier,
        browser_keywords,
        tab_resolver=None,
        pause_resolver=None,
        launcher=None,
    ):
        self._gui_title_supplier = gui_title_supplier
        self._browser_keywords = [kw.lower() for kw in browser_keywords]
        self._tab_resolver = tab_resolver
        self._pause_resolver = pause_resolver
        self._launcher = launcher
        self._stop_event = threading.Event()
        self._thread = None
        self._last_browser_window = None
        self._lock = threading.Lock()
        self._last_launch_attempt = 0.0
        self._console_keywords = [
            'prompt de comando',
            'command prompt',
            'windows powershell',
            'powershell',
            'cmd.exe',
            'python.exe',
            'py.exe'
        ]

    def start(self):
        if gw is None:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="BrowserFocusGuardian", daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=0.5)
        self._thread = None

    def force_browser_focus(self):
        if self._is_paused():
            return False
        if gw is None:
            if self._launch_browser_via_taskbar():
                time.sleep(0.6)
            return False
        success = self._activate_browser_window()
        if success:
            return True
        if self._launch_browser_via_taskbar():
            time.sleep(0.6)
            success = self._activate_browser_window()
        return success

    def remember_browser_window(self, window):
        if gw is None or window is None:
            return
        if self._is_browser_window(window):
            with self._lock:
                self._last_browser_window = window

    def _run(self):
        while not self._stop_event.wait(0.75):
            if self._is_paused():
                continue
            self._guard_focus()

    def _guard_focus(self):
        if gw is None:
            return
        try:
            active = gw.getActiveWindow()
        except Exception:
            active = None

        if self._is_browser_window(active):
            self.remember_browser_window(active)
            return

        if self._is_gui_window(active) or self._is_console_window(active):
            self._activate_browser_window()

    def _activate_browser_window(self):
        if self._is_paused():
            return False

        target = None
        with self._lock:
            if self._last_browser_window and self._is_browser_window(self._last_browser_window):
                target = self._last_browser_window

        if target is None:
            target = self._find_browser_candidate()

        if target is None:
            if self._activate_via_winapi():
                self._select_target_tab()
                return True
            if self._launch_browser_via_taskbar():
                time.sleep(0.6)
            return False

        try:
            if getattr(target, 'isMinimized', False):
                target.restore()
            target.activate()
            self.remember_browser_window(target)
            time.sleep(0.12)
            self._select_target_tab()
            return True
        except Exception:
            if self._activate_via_winapi():
                self._select_target_tab()
                return True
            return False

    def _find_browser_candidate(self):
        if gw is None:
            return None
        try:
            for window in gw.getAllWindows():
                if self._is_browser_window(window):
                    return window
        except Exception:
            return None
        return None

    def _is_browser_window(self, window):
        if gw is None or window is None:
            return False
        try:
            title = (window.title or '').lower()
        except Exception:
            return False
        if not title:
            return False
        return any(keyword in title for keyword in self._browser_keywords)

    def _is_gui_window(self, window):
        if window is None:
            return False
        try:
            title = (window.title or '').lower()
        except Exception:
            return False
        gui_title = (self._gui_title_supplier() or '').lower()
        if gui_title and gui_title in title:
            return True
        return 'auto mdf invoisys' in title

    def _is_console_window(self, window):
        if window is None:
            return False
        try:
            title = (window.title or '').lower()
        except Exception:
            return False
        if not title:
            return False
        return any(keyword in title for keyword in self._console_keywords)

    def _select_target_tab(self):
        tab_index = self._resolve_target_tab()
        if tab_index is None or pyautogui is None:
            return
        try:
            pyautogui.hotkey('ctrl', str(tab_index))
            time.sleep(0.12)
        except Exception:
            pass

    def _resolve_target_tab(self):
        if self._tab_resolver is None:
            return None
        try:
            value = self._tab_resolver()
        except Exception:
            return None
        try:
            tab_index = int(value)
        except (TypeError, ValueError):
            return None
        if tab_index <= 0:
            return None
        return min(tab_index, 9)

    def _is_paused(self):
        if self._pause_resolver is None:
            return False
        try:
            return bool(self._pause_resolver())
        except Exception:
            return False

    def _activate_via_winapi(self):
        if ctypes is None or EnumWindows is None or EnumWindowsProc is None:
            return False
        if GetWindowTextLengthW is None or GetWindowTextW is None or IsWindowVisible is None:
            return False

        handles: list[int] = []
        gui_title = (self._gui_title_supplier() or '').lower()

        def enum_proc(hwnd, _lparam):
            try:
                if not IsWindowVisible(hwnd):
                    return True
                length = GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value.lower()
            except Exception:
                return True

            if not title:
                return True
            if gui_title and gui_title in title:
                return True
            if 'auto mdf invoisys' in title:
                return True
            for keyword in self._browser_keywords:
                if keyword in title:
                    handles.append(hwnd)
                    break
            return True

        try:
            callback = EnumWindowsProc(enum_proc)
            EnumWindows(callback, 0)
        except Exception:
            return False

        for hwnd in handles:
            try:
                if ShowWindow is not None:
                    ShowWindow(hwnd, SW_RESTORE)
            except Exception:
                pass
            try:
                if SetForegroundWindow is not None and SetForegroundWindow(hwnd):
                    time.sleep(0.12)
                    return True
            except Exception:
                pass
            try:
                if BringWindowToTop is not None:
                    BringWindowToTop(hwnd)
                    time.sleep(0.12)
                    return True
            except Exception:
                continue
        return False

    def _launch_browser_via_taskbar(self):
        if self._launcher is None:
            return False
        now = time.time()
        if now - self._last_launch_attempt < 1.5:
            return False
        self._last_launch_attempt = now
        try:
            return bool(self._launcher())
        except Exception:
            return False


class WindowVisibilityController:
    """Mantém a GUI no topo sem roubar o foco do navegador."""

    def __init__(self, root):
        self.root = root
        self._mode = 'idle'  # idle, passive, interactive
        self._user_topmost = False
        self._current_enable = False
        self._current_no_activate = False
        self._is_windows = os.name == 'nt' and SetWindowPos is not None
        self._hwnd = None

    def set_user_topmost(self, enabled: bool):
        self._user_topmost = bool(enabled)
        if self._mode == 'idle':
            self._apply_topmost(self._user_topmost, no_activate=False, force=True)

    def enter_passive(self):
        self._mode = 'passive'
        self._apply_topmost(True, no_activate=True, force=True)

    def enter_interactive(self):
        self._mode = 'interactive'
        self._apply_topmost(True, no_activate=False, force=True)

    def release(self):
        self._mode = 'idle'
        self._apply_topmost(self._user_topmost, no_activate=False, force=True)

    def maintain(self):
        if self._mode == 'passive':
            self._apply_topmost(True, no_activate=True)
        elif self._mode == 'interactive':
            self._apply_topmost(True, no_activate=False)

    def invalidate_handle(self):
        if self._is_windows:
            self._hwnd = None

    def _apply_topmost(self, enable: bool, *, no_activate: bool = False, force: bool = False):
        if self._is_windows:
            hwnd = self._get_hwnd()
            if not hwnd:
                return
            if not force and enable == self._current_enable and no_activate == self._current_no_activate:
                return
            flags = SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
            if no_activate:
                flags |= SWP_NOACTIVATE
            try:
                SetWindowPos(hwnd, HWND_TOPMOST if enable else HWND_NOTOPMOST, 0, 0, 0, 0, flags)
            except Exception:
                pass
            if not enable:
                try:
                    self.root.attributes('-topmost', False)
                except Exception:
                    pass
            self._current_no_activate = no_activate if enable else False
        else:
            if not force and enable == self._current_enable:
                return
            try:
                self.root.attributes('-topmost', enable)
            except Exception:
                pass
            self._current_no_activate = False

        self._current_enable = enable

        try:
            if enable:
                self.root.deiconify()
                if not no_activate:
                    self.root.lift()
        except Exception:
            pass

    def _get_hwnd(self):
        if not self._is_windows:
            return None
        if self._hwnd:
            return self._hwnd
        try:
            hwnd = self.root.winfo_id()
        except Exception:
            hwnd = None
        if hwnd:
            self._hwnd = hwnd
        return self._hwnd
@dataclass(frozen=True)
class DependencySpec:
    package: str
    description: str
    required: bool = True


class DependencyChecker:
    """Verifica e gerencia instalação de dependências"""

    DEPENDENCIES: tuple[DependencySpec, ...] = (
        DependencySpec('pyautogui', 'Automação do mouse e do teclado'),
        DependencySpec('pyperclip', 'Copiar e colar via área de transferência'),
        DependencySpec('pygetwindow', 'Detectar e focar janelas automaticamente', required=False),
    )

    # Cache de verificação (válido por 5 minutos)
    _cache: dict[tuple[str, bool], tuple[list[str], list[str], float]] = {}
    _cache_timeout = 300  # segundos

    def __init__(self):
        self.required_packages = [dep.package for dep in self.DEPENDENCIES if dep.required]
        self.optional_packages = [dep.package for dep in self.DEPENDENCIES if not dep.required]
        self.missing_packages: list[str] = []
        self.missing_optional_packages: list[str] = []

    def check_dependencies(self, include_optional=False, use_cache=True):
        """Retorna True se todas as dependências obrigatórias estiverem instaladas."""
        cache_key = (','.join(sorted(self.required_packages + (self.optional_packages if include_optional else []))), include_optional)

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                self.missing_packages, self.missing_optional_packages = cached
                return len(self.missing_packages) == 0

        missing_required: list[str] = []
        missing_optional: list[str] = []

        for dep in self.DEPENDENCIES:
            if not dep.required and not include_optional:
                continue
            if not self._is_package_installed(dep.package):
                if dep.required:
                    missing_required.append(dep.package)
                else:
                    missing_optional.append(dep.package)

        self.missing_packages = missing_required
        self.missing_optional_packages = missing_optional

        if use_cache:
            self._save_to_cache(cache_key, missing_required[:], missing_optional[:])

        return len(self.missing_packages) == 0

    @classmethod
    def _get_from_cache(cls, key):
        """Obtém resultado do cache se ainda válido"""
        if key in cls._cache:
            missing_required, missing_optional, timestamp = cls._cache[key]
            if time.time() - timestamp < cls._cache_timeout:
                return missing_required[:], missing_optional[:]
            del cls._cache[key]
        return None

    @classmethod
    def _save_to_cache(cls, key, missing_required, missing_optional):
        """Salva resultado no cache"""
        cls._cache[key] = (missing_required[:], missing_optional[:], time.time())

    @classmethod
    def clear_cache(cls):
        """Limpa o cache de verificação"""
        cls._cache.clear()

    def _is_package_installed(self, package_name):
        """Verifica se um pacote está instalado"""
        spec = importlib.util.find_spec(package_name)
        return spec is not None

    def get_missing_packages(self):
        """Retorna lista de pacotes obrigatórios faltantes"""
        return self.missing_packages

    def get_missing_optional_packages(self):
        """Retorna lista de pacotes opcionais recomendados faltantes"""
        return self.missing_optional_packages

    @classmethod
    def install_dependencies(cls, include_optional=True):
        """Instala dependências obrigatórias e, opcionalmente, as recomendadas."""
        packages_to_install: list[DependencySpec] = []
        for spec in cls.DEPENDENCIES:
            if spec.required or include_optional:
                packages_to_install.append(spec)

        if not packages_to_install:
            return True, "Nenhum pacote para instalar.", ""

        install_logs: list[str] = []

        try:
            upgrade_cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel']
            upgrade_result = subprocess.run(
                upgrade_cmd,
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR)
            )
            install_logs.append(upgrade_result.stdout.strip())
            if upgrade_result.stderr:
                install_logs.append(upgrade_result.stderr.strip())
        except Exception as exc:
            install_logs.append(f"Falha ao atualizar pip: {exc}")

        required_failures: list[str] = []
        optional_failures: list[str] = []

        for spec in packages_to_install:
            cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', spec.package]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR)
            )
            log_chunk = result.stdout.strip()
            err_chunk = result.stderr.strip()
            if log_chunk:
                install_logs.append(log_chunk)
            if err_chunk:
                install_logs.append(err_chunk)

            if result.returncode != 0:
                if spec.required:
                    required_failures.append(f"{spec.package}: {err_chunk or 'erro não informado'}")
                else:
                    optional_failures.append(f"{spec.package}: {err_chunk or 'erro não informado'}")

        cls.clear_cache()

        combined_log = "\n".join(chunk for chunk in install_logs if chunk).strip()

        if required_failures:
            message = "Não foi possível instalar todos os pacotes obrigatórios."
            detail_lines = required_failures + optional_failures
            if combined_log:
                detail_lines.append(combined_log)
            details = "\n".join(detail_lines).strip()
            return False, message, details.strip()

        if optional_failures:
            message = "Pacotes obrigatórios instalados. Alguns opcionais falharam."
            detail_lines = optional_failures
            if combined_log:
                detail_lines.append(combined_log)
            details = "\n".join(detail_lines).strip()
            return True, message, details.strip()

        return True, "Dependências instaladas com sucesso!", ""


class ScriptExecutor:
    """Gerencia a execução independente de um script"""
    
    MAX_OUTPUT_LINES = 1000  # Limite máximo de linhas para evitar overflow de memória
    
    def __init__(self, script_path, script_name, execution_id, target_tab=0):
        self.script_path = script_path
        self.script_name = script_name
        self.execution_id = execution_id
        self.target_tab = target_tab
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
            env['MDF_PROGRESS_FILE'] = str(self.progress_file)
            if isinstance(self.target_tab, int) and self.target_tab > 0:
                env['MDF_BROWSER_TAB'] = str(self.target_tab)
            
            # Iniciar processo de forma completamente isolada
            creationflags = 0
            if os.name == 'nt':
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            self.process = subprocess.Popen(
                [sys.executable, self.script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                creationflags=creationflags,
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
        paths_to_try = [self.progress_file]
        default_path = BASE_DIR / ProgressManager.DEFAULT_FILE_NAME
        if default_path not in paths_to_try:
            paths_to_try.append(default_path)

        for progress_path in paths_to_try:
            try:
                if os.path.exists(progress_path):
                    with open(progress_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except json.JSONDecodeError:
                # Arquivo pode estar sendo escrito; tentar novamente em ciclo futuro
                continue
            except Exception:
                continue

        return None


class DependencyInstallWindow:
    """Janela separada para instalação de dependências"""
    
    def __init__(self, parent, checker, initial_message=None):
        self.parent = parent
        self.checker = checker
        self.initial_message = initial_message or "Aguardando ação..."
        self.installation_complete = False
        self.missing_packages = checker.get_missing_packages()
        self.missing_optional = checker.get_missing_optional_packages()
        self.dependency_specs = checker.DEPENDENCIES

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
        packages_frame = ttk.LabelFrame(content_frame, text="Dependências obrigatórias", padding=15)
        packages_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

        required_specs = [spec for spec in self.dependency_specs if spec.required]
        if self.missing_packages:
            for spec in required_specs:
                if spec.package in self.missing_packages:
                    ttk.Label(
                        packages_frame,
                        text=f"• {spec.package} — {spec.description}",
                        font=('Segoe UI', 10),
                        foreground='#ef4444'
                    ).pack(anchor=tk.W, pady=3)
        else:
            ttk.Label(
                packages_frame,
                text="Todas as dependências obrigatórias estão presentes.",
                font=('Segoe UI', 10),
                foreground='#10b981'
            ).pack(anchor=tk.W, pady=3)

        optional_specs = [spec for spec in self.dependency_specs if not spec.required]
        if optional_specs:
            optional_frame = ttk.LabelFrame(content_frame, text="Pacotes recomendados", padding=15)
            optional_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

            if self.missing_optional:
                for spec in optional_specs:
                    color = '#0ea5e9' if spec.package not in self.missing_optional else '#f97316'
                    ttk.Label(
                        optional_frame,
                        text=f"• {spec.package} — {spec.description}",
                        font=('Segoe UI', 9),
                        foreground=color
                    ).pack(anchor=tk.W, pady=2)
            else:
                ttk.Label(
                    optional_frame,
                    text="Todos os recursos recomendados estão instalados (ótimo!).",
                    font=('Segoe UI', 9),
                    foreground='#0ea5e9'
                ).pack(anchor=tk.W, pady=2)
        
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
            "• install.bat (cria e usa o ambiente .venv do projeto)\n"
            "• install_user.bat (instala no perfil do usuário Windows)",
            font=('Segoe UI', 9),
            foreground='#666'
        )
        option2_desc.pack(anchor=tk.W, pady=(0, 0))
        
        # Status de instalação
        status_text = self.initial_message
        status_color = '#666'
        if '✅' in status_text:
            status_color = '#10b981'
        elif '⚠️' in status_text:
            status_color = '#f59e0b'
        elif 'ℹ️' in status_text:
            status_color = '#0ea5e9'
        
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
        success, message, details = DependencyChecker.install_dependencies(include_optional=True)

        post_check = DependencyChecker()
        post_check.check_dependencies(include_optional=True, use_cache=False)
        self.missing_packages = post_check.get_missing_packages()
        self.missing_optional = post_check.get_missing_optional_packages()

        full_message = message
        if details:
            full_message = f"{message}\n\n{details}"

        if success:
            self.status_label.config(text=f"✅ {full_message}", foreground='#10b981')
            self.installation_complete = True

            # Aguardar 2 segundos e fechar
            time.sleep(2)
            self.window.destroy()
        else:
            self.status_label.config(
                text=f"❌ {full_message}\n\nTente usar o install.bat ou install_user.bat manualmente.",
                foreground='#ef4444'
            )

            self.install_btn.config(state=tk.NORMAL)
            self.retry_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.NORMAL)
    
    def _check_again(self):
        """Verifica as dependências novamente"""
        checker = DependencyChecker()
        checker.check_dependencies(include_optional=True, use_cache=False)

        missing_required = checker.get_missing_packages()
        missing_optional = checker.get_missing_optional_packages()

        self.missing_packages = missing_required
        self.missing_optional = missing_optional

        if not missing_required:
            if missing_optional:
                optional_text = ", ".join(missing_optional)
                self.status_label.config(
                    text=f"✅ Obrigatórios instalados. Pacotes recomendados pendentes: {optional_text}",
                    foreground='#0ea5e9'
                )
            else:
                self.status_label.config(
                    text="✅ Todas as dependências estão instaladas!",
                    foreground='#10b981'
                )
            self.installation_complete = True

            time.sleep(1)
            self.window.destroy()
        else:
            self.status_label.config(
                text=f"❌ Ainda faltam: {', '.join(missing_required)}",
                foreground='#ef4444'
            )
    
    def on_cancel(self):
        """Cancela a instalação"""
        if self.missing_packages:
            confirm = messagebox.askyesno(
                "Cancelar",
                "As dependências obrigatórias continuam faltando.\n\n"
                "Tem certeza que deseja sair sem instalar?"
            )
            if confirm:
                self.window.destroy()
        else:
            self.window.destroy()


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
        self._last_browser_window = None
        self._active_overlay = None
        self.target_tab_var = tk.IntVar(value=1)
        self._last_taskbar_activation = 0.0
        self._taskbar_launch_done = False
        self._taskbar_launch_attempts = 0
        self._refocus_job = None
        self.focus_guardian = BrowserFocusGuardian(
            lambda: self.root.title(),
            BROWSER_WINDOW_KEYWORDS,
            tab_resolver=self._get_focus_guardian_tab,
            pause_resolver=self._is_overlay_active,
            launcher=self._launch_browser_via_taskbar
        )
        self._visibility_controller = WindowVisibilityController(self.root)
        self._visibility_job = None
        
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

        # Respeitar configuração inicial de topmost do usuário
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self._visibility_controller.set_user_topmost(self.topmost_var.get())
        
        # Iniciar thread de atualização
        self.start_update_loop()
        
        # Handler para fechar a janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<Unmap>', self._handle_visibility_event, add='+')
        self.root.bind('<Map>', self._handle_visibility_event, add='+')
        self.root.bind('<FocusIn>', self._handle_root_focus_in, add='+')
        self.root.bind('<ButtonRelease-1>', self._handle_root_pointer_release, add='+')
    
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
        if hasattr(self, '_visibility_controller'):
            self._visibility_controller.set_user_topmost(self.topmost_var.get())
        else:
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

        tab_select_frame = ttk.Frame(select_frame)
        tab_select_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            tab_select_frame,
            text="Aba do navegador alvo (0 = manter atual):"
        ).pack(side=tk.LEFT)

        try:
            spinbox = ttk.Spinbox(
                tab_select_frame,
                from_=0,
                to=9,
                textvariable=self.target_tab_var,
                width=4
            )
        except Exception:
            spinbox = tk.Spinbox(
                tab_select_frame,
                from_=0,
                to=9,
                textvariable=self.target_tab_var,
                width=4
            )
        spinbox.pack(side=tk.LEFT, padx=(8, 0))
        
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

    def _handle_visibility_event(self, event=None):
        if (
            self.current_execution
            and self.current_execution.is_running
            and self.root.state() in ('iconic', 'iconified', 'withdrawn')
        ):
            self.root.after(150, self._restore_gui_visibility)

    def _restore_gui_visibility(self):
        if not self.root.winfo_exists():
            return
        if (
            self.current_execution
            and self.current_execution.is_running
            and self.root.state() in ('iconic', 'iconified', 'withdrawn')
        ):
            self.root.deiconify()
            if hasattr(self, '_visibility_controller'):
                self._visibility_controller.maintain()
            else:
                self.root.lift()
            if hasattr(self, 'focus_guardian') and self.focus_guardian:
                self.focus_guardian.force_browser_focus()
            if self._visibility_job is None:
                self._visibility_job = self.root.after(600, self._visibility_guard_loop)

    def _start_visibility_guard(self):
        self._stop_visibility_guard()
        self._visibility_guard_loop()

    def _stop_visibility_guard(self):
        if self._visibility_job is not None:
            try:
                self.root.after_cancel(self._visibility_job)
            except Exception:
                pass
            self._visibility_job = None

    def _visibility_guard_loop(self):
        self._visibility_job = None
        if not self.root.winfo_exists():
            return
        if self.current_execution:
            if self.current_execution.is_running:
                state = self.root.state()
                if state in ('iconic', 'iconified', 'withdrawn'):
                    self.root.deiconify()
                    if hasattr(self, '_visibility_controller'):
                        self._visibility_controller.maintain()
                    else:
                        self.root.after(50, self.root.lift)
                elif hasattr(self, '_visibility_controller'):
                    self._visibility_controller.maintain()
                if hasattr(self, 'focus_guardian') and self.focus_guardian:
                    self.focus_guardian.force_browser_focus()
            self._visibility_job = self.root.after(600, self._visibility_guard_loop)

    def _resolve_target_tab_value(self):
        try:
            value = int(self.target_tab_var.get())
        except Exception:
            value = 0
        if value < 0:
            value = 0
        if value > 9:
            value = 9
        return value

    def _get_focus_guardian_tab(self):
        value = self._resolve_target_tab_value()
        return value if value > 0 else None

    def _switch_to_target_tab(self):
        tab_index = self._get_focus_guardian_tab()
        if tab_index is None or pyautogui is None:
            return
        key = str(tab_index)
        key_down = False
        try:
            pyautogui.keyDown('ctrl')
            key_down = True
            pyautogui.press(key)
        except Exception:
            pass
        finally:
            if key_down:
                try:
                    pyautogui.keyUp('ctrl')
                except Exception:
                    pass
        time.sleep(0.12)

    def _mark_browser_focus_acquired(self):
        self._taskbar_launch_done = True

    def _is_browser_title(self, title):
        if not title:
            return False
        lower = title.lower()
        gui_title = (self.root.title() or '').lower()
        if gui_title and gui_title in lower:
            return False
        if 'auto mdf invoisys' in lower:
            return False
        return any(keyword in lower for keyword in BROWSER_WINDOW_KEYWORDS)

    def _is_browser_foreground(self):
        if ctypes is None or GetForegroundWindow is None:
            return False
        if GetWindowTextLengthW is None or GetWindowTextW is None:
            return False
        try:
            hwnd = GetForegroundWindow()
        except Exception:
            return False
        if not hwnd:
            return False
        try:
            length = GetWindowTextLengthW(hwnd)
        except Exception:
            return False
        if length <= 0:
            return False
        buffer = ctypes.create_unicode_buffer(length + 1)
        try:
            GetWindowTextW(hwnd, buffer, length + 1)
        except Exception:
            return False
        return self._is_browser_title(buffer.value)

    def _activate_browser_via_winapi(self):
        if ctypes is None or EnumWindows is None or EnumWindowsProc is None:
            return False
        if IsWindowVisible is None or GetWindowTextLengthW is None or GetWindowTextW is None:
            return False

        handles: list[int] = []
        gui_title = (self.root.title() or '').lower()

        def enum_proc(hwnd, _lparam):
            try:
                if not IsWindowVisible(hwnd):
                    return True
                length = GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
            except Exception:
                return True

            if not title:
                return True
            lower = title.lower()
            if gui_title and gui_title in lower:
                return True
            if 'auto mdf invoisys' in lower:
                return True
            for keyword in BROWSER_WINDOW_KEYWORDS:
                if keyword in lower:
                    handles.append(hwnd)
                    break
            return True

        try:
            callback = EnumWindowsProc(enum_proc)
            EnumWindows(callback, 0)
        except Exception:
            return False

        for hwnd in handles:
            try:
                if ShowWindow is not None:
                    ShowWindow(hwnd, SW_RESTORE)
            except Exception:
                pass
            try:
                if SetForegroundWindow is not None and SetForegroundWindow(hwnd):
                    time.sleep(0.12)
                    self._mark_browser_focus_acquired()
                    return True
            except Exception:
                pass
            try:
                if BringWindowToTop is not None:
                    BringWindowToTop(hwnd)
                    time.sleep(0.12)
                    self._mark_browser_focus_acquired()
                    return True
            except Exception:
                continue
        return False

    def _launch_browser_via_taskbar(self):
        if pyautogui is None:
            return False
        if self._taskbar_launch_done:
            return False
        if self._taskbar_launch_attempts >= 1:
            return False
        now = time.time()
        if now - self._last_taskbar_activation < 1.5:
            return False
        self._last_taskbar_activation = now
        self._taskbar_launch_attempts += 1
        try:
            pyautogui.hotkey('win', '1')
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def _is_overlay_active(self):
        overlay = getattr(self, '_active_overlay', None)
        return bool(overlay and overlay.winfo_exists())

    def _handle_root_focus_in(self, event=None):
        if self._is_overlay_active():
            return
        if not (self.current_execution and self.current_execution.is_running):
            return
        self._schedule_browser_refocus()

    def _handle_root_pointer_release(self, event=None):
        if self._is_overlay_active():
            return
        if not (self.current_execution and self.current_execution.is_running):
            return
        self._schedule_browser_refocus()

    def _schedule_browser_refocus(self, delay=0):
        if not self.root.winfo_exists():
            return
        if self._refocus_job is not None:
            try:
                self.root.after_cancel(self._refocus_job)
            except Exception:
                pass
            self._refocus_job = None

        def callback():
            self._refocus_job = None
            self._redirect_focus_to_browser()

        if delay and delay > 0:
            self._refocus_job = self.root.after(delay, callback)
        else:
            self._refocus_job = self.root.after_idle(callback)

    def _redirect_focus_to_browser(self):
        if not self.root.winfo_exists():
            return
        if self._is_overlay_active():
            return
        if not (self.current_execution and self.current_execution.is_running):
            return
        focus_acquired = False

        if hasattr(self, 'focus_guardian') and self.focus_guardian:
            try:
                focus_acquired = bool(self.focus_guardian.force_browser_focus())
            except Exception:
                focus_acquired = False

        if not focus_acquired:
            focus_acquired = bool(self._restore_external_focus())

        if hasattr(self, '_visibility_controller'):
            self._visibility_controller.enter_passive()

        if not focus_acquired:
            self._schedule_browser_refocus(delay=200)
    
    def start_new_execution(self):
        """Inicia uma nova execução de script"""
        # Verificar dependências antes de executar
        self.dependency_checker.check_dependencies(include_optional=True)
        missing_required = self.dependency_checker.get_missing_packages()
        missing_optional = self.dependency_checker.get_missing_optional_packages()

        if missing_required:
            response = messagebox.showwarning(
                "Dependências Faltando",
                f"❌ As seguintes dependências estão faltando:\n\n"
                f"{', '.join(missing_required)}\n\n"
                f"É OBRIGATÓRIO instalar as dependências antes de executar scripts.\n\n"
                f"Deseja instalar agora?",
                type=messagebox.YESNO
            )

            if response == messagebox.YES:
                self._install_dependencies_manual()

            return

        if missing_optional:
            if messagebox.askyesno(
                "Pacotes recomendados",
                "Os pacotes recomendados ajudam a manter o navegador em foco durante a automação.\n\n"
                f"Faltando: {', '.join(missing_optional)}\n\n"
                "Deseja instalá-los agora?"
            ):
                self._install_dependencies_manual()
                # Revalidar e impedir execução caso o usuário cancele o instalador
                self.dependency_checker.check_dependencies(include_optional=True, use_cache=False)
                if self.dependency_checker.get_missing_packages():
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
        
        # Resolver aba alvo do navegador (0 = manter atual)
        target_tab_value = self._resolve_target_tab_value()
        self._taskbar_launch_done = False
        self._taskbar_launch_attempts = 0

        # Criar executor
        execution_id = f"{script_name}_{int(time.time())}"
        
        executor = ScriptExecutor(script_path, script_name, execution_id, target_tab=target_tab_value)
        self.current_execution = executor

        # Reorganizar janelas: manter GUI acessível sem roubar foco do navegador
        previous_state = {
            'was_iconified': self.root.state() in ('iconic', 'iconified', 'withdrawn'),
            'was_topmost': self.topmost_var.get()
        }
        self.execution_window_state = previous_state

        if previous_state['was_iconified']:
            self.root.deiconify()

        self.root.update_idletasks()

        if hasattr(self, 'topmost_checkbox'):
            self.topmost_checkbox.state(['disabled'])

        if hasattr(self, '_visibility_controller'):
            self._visibility_controller.set_user_topmost(previous_state['was_topmost'])
            self._visibility_controller.enter_passive()

        self.topmost_var.set(True)

        if hasattr(self, 'focus_guardian') and self.focus_guardian:
            self.focus_guardian.start()

        self._start_visibility_guard()
        self._launch_browser_via_taskbar()

        if gw is not None:
            self.root.after(250, self._restore_external_focus)
            if target_tab_value > 0:
                window_event_message = (
                    f"🪟 Janela principal mantida visível sem capturar foco. Navegador direcionado para a aba {target_tab_value}."
                )
            else:
                window_event_message = (
                    "🪟 Janela principal mantida visível sem capturar foco. Navegador continua na aba atual."
                )
        else:
            self.root.after(250, self._restore_external_focus)
            if target_tab_value > 0:
                window_event_message = (
                    f"🪟 Janela principal mantida visível. Instale 'pygetwindow' para direcionar automaticamente a aba {target_tab_value}."
                )
            else:
                window_event_message = (
                    "🪟 Janela principal mantida visível. Instale 'pygetwindow' para redirecionar o foco do navegador automaticamente."
                )
        
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

        # Start bar in indeterminate mode until precise progress becomes available
        progress_bar.config(mode='indeterminate')
        progress_bar.start(120)

        progress_label = ttk.Label(progress_frame, text="Em andamento...")
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
            'finalized': False,
            'progress_mode': 'indeterminate',
            'no_progress_counter': 0,
            'progress_hint_logged': False
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
            if progress and 'percentage' in progress:
                percentage = max(0, min(100, int(progress.get('percentage', 0))))
                if widgets.get('progress_mode') == 'indeterminate':
                    try:
                        widgets['progress_bar'].stop()
                    except Exception:
                        pass
                    widgets['progress_bar'].config(mode='determinate')
                    widgets['progress_mode'] = 'determinate'
                widgets['progress_label'].config(text=f"{percentage}%")
                widgets['progress_bar'].config(value=percentage)
                widgets['no_progress_counter'] = 0
                step = percentage // 10
                last_step = widgets.get('last_progress_step', -1)
                if step > 0 and step != last_step:
                    self._append_log_message(f"📈 Progresso atualizado: {percentage}% concluído.")
                    widgets['last_progress_step'] = step
            else:
                widgets['no_progress_counter'] = widgets.get('no_progress_counter', 0) + 1
                if widgets.get('progress_mode') == 'indeterminate':
                    widgets['progress_label'].config(text="Em andamento...")
                    if widgets['no_progress_counter'] >= 5 and not widgets.get('progress_hint_logged'):
                        self._append_log_message(
                            "ℹ️ Para acompanhar o progresso percentual, utilize o ProgressManager dentro do script (veja o README).",
                            'info'
                        )
                        widgets['progress_hint_logged'] = True
            
            # Se execução terminou
            if not executor.is_running and not widgets.get('finalized'):
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.script_combo.config(state='readonly')

                # Limpar memória
                executor.cleanup()

                # Adicionar ao histórico apenas uma vez por execução
                if executor.status == "completed":
                    try:
                        widgets['progress_bar'].stop()
                    except Exception:
                        pass
                    widgets['progress_bar'].config(mode='determinate')
                    widgets['progress_bar'].config(value=100)
                    widgets['progress_label'].config(text="100%")
                    widgets['last_progress_step'] = 10
                    widgets['progress_mode'] = 'determinate'
                    self._log_to_history(
                        f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Concluído: {executor.script_name} ({executor.get_elapsed_time()})",
                        'success'
                    )
                elif executor.status == "failsafe":
                    try:
                        widgets['progress_bar'].stop()
                    except Exception:
                        pass
                    widgets['progress_label'].config(text="Interrompido")
                    self._log_to_history(
                        f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 FailSafe acionado: {executor.script_name} ({executor.get_elapsed_time()})",
                        'warning'
                    )
                elif executor.status == "error":
                    try:
                        widgets['progress_bar'].stop()
                    except Exception:
                        pass
                    widgets['progress_label'].config(text="Erro")
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
                else:
                    try:
                        widgets['progress_bar'].stop()
                    except Exception:
                        pass
                    widgets['progress_label'].config(text="Parado")
                widgets['progress_mode'] = 'determinate'

                widgets['finalized'] = True
                self.current_execution = None
                state_snapshot = getattr(self, 'execution_window_state', {'was_iconified': False, 'was_topmost': False})

                self._stop_visibility_guard()
                if hasattr(self, 'focus_guardian') and self.focus_guardian:
                    self.focus_guardian.stop()

                if state_snapshot.get('was_iconified'):
                    self.root.iconify()
                else:
                    self.root.deiconify()
                    self.root.lift()

                was_topmost = state_snapshot.get('was_topmost', False)
                self.topmost_var.set(was_topmost)
                if hasattr(self, '_visibility_controller'):
                    self._visibility_controller.set_user_topmost(was_topmost)
                    self._visibility_controller.release()
                else:
                    self.root.attributes('-topmost', was_topmost)

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
        parent = self._dialog_parent()
        was_iconified = self._ensure_dialog_parent_visible()

        try:
            if dialog_type == 'alert':
                self._append_log_message(f"🔔 Alerta do script: {message}", 'info')
                button_text = payload.get('button') or "OK"
                self._show_custom_alert(parent, title, message, button_text)
                executor.send_bridge_response(BRIDGE_ACK)
                return

            if dialog_type == 'prompt':
                self._append_log_message(f"📝 Entrada solicitada: {message}", 'info')
                default = payload.get('default', '')
                response = self._show_custom_prompt(parent, title, message, default)
                if response is None:
                    executor.send_bridge_response(BRIDGE_CANCEL)
                else:
                    executor.send_bridge_response(response)
                return

            if dialog_type == 'confirm':
                self._append_log_message(f"❓ Confirmação solicitada: {message}", 'info')
                buttons = payload.get('buttons') or ['OK', 'Cancel']
                choice = self._show_custom_confirm(title, message, buttons, parent=parent)
                if choice is None:
                    executor.send_bridge_response(BRIDGE_CANCEL)
                else:
                    executor.send_bridge_response(choice)
                return

            # Caso não reconheça, apenas confirma para evitar travar o script
            executor.send_bridge_response(BRIDGE_ACK)
        finally:
            self._restore_dialog_parent_state(was_iconified)

    def _create_overlay_container(self, title):
        self._destroy_overlay()
        overlay = tk.Frame(self.root, bg='#111827', highlightthickness=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()

        container_bg = '#f8fafc'
        container = tk.Frame(
            overlay,
            bg=container_bg,
            bd=1,
            relief='ridge',
            highlightthickness=1,
            highlightbackground='#60a5fa'
        )
        container.place(relx=0.5, rely=0.5, anchor='center')

        title_label = tk.Label(
            container,
            text=title or "Auto MDF InvoISys",
            font=('Segoe UI', 12, 'bold'),
            bg=container_bg,
            fg='#0f172a'
        )
        title_label.pack(padx=24, pady=(18, 6))

        ttk.Separator(container, orient='horizontal').pack(fill=tk.X, padx=24, pady=(0, 12))

        overlay.focus_set()
        self._active_overlay = overlay
        if (
            hasattr(self, '_visibility_controller')
            and self.current_execution
            and self.current_execution.is_running
        ):
            self._visibility_controller.enter_interactive()
        return overlay, container

    def _destroy_overlay(self):
        if self._active_overlay and self._active_overlay.winfo_exists():
            try:
                self._active_overlay.destroy()
            except Exception:
                pass
        self._active_overlay = None
        if (
            hasattr(self, '_visibility_controller')
            and self.current_execution
            and self.current_execution.is_running
        ):
            self._visibility_controller.enter_passive()

    def _show_custom_confirm(self, title, message, buttons, parent=None):
        """Exibe diálogo de confirmação integrado na própria GUI"""
        if not buttons:
            buttons = ['OK']

        result_var = tk.StringVar(value="")
        overlay, container = self._create_overlay_container(title or "Confirmação")

        message_label = tk.Label(
            container,
            text=message,
            justify='left',
            wraplength=440,
            font=('Segoe UI', 10),
            bg=container.cget('bg'),
            fg='#1f2937'
        )
        message_label.pack(padx=24, pady=(12, 18))

        button_frame = tk.Frame(container, bg=container.cget('bg'))
        button_frame.pack(padx=24, pady=(0, 16), fill=tk.X)

        columns = min(3, len(buttons))
        columns = columns if columns > 0 else 1

        def finalize_choice(choice):
            result_var.set(choice)
            self._destroy_overlay()

        for idx, button_text in enumerate(buttons):
            btn = ttk.Button(button_frame, text=button_text, command=lambda val=button_text: finalize_choice(val))
            row = idx // columns
            col = idx % columns
            btn.grid(row=row, column=col, padx=4, pady=4, sticky='ew')
            button_frame.grid_columnconfigure(col, weight=1)
            if idx == 0:
                btn.focus_set()

        def handle_escape(event=None):
            fallback = 'Cancel' if 'Cancel' in buttons else buttons[-1]
            finalize_choice(fallback)

        overlay.bind('<Escape>', handle_escape)

        self.root.wait_variable(result_var)
        choice = result_var.get()
        return choice or None

    def _show_custom_alert(self, parent, title, message, button_text="OK"):
        result_var = tk.StringVar(value="")
        overlay, container = self._create_overlay_container(title or "Alerta")

        message_label = tk.Label(
            container,
            text=message,
            justify='left',
            wraplength=440,
            font=('Segoe UI', 10),
            bg=container.cget('bg'),
            fg='#1f2937'
        )
        message_label.pack(padx=24, pady=(12, 18))

        def confirm(event=None):
            result_var.set(button_text or "OK")
            self._destroy_overlay()

        button = ttk.Button(container, text=button_text or "OK", command=confirm)
        button.pack(pady=(0, 18))
        button.focus_set()

        overlay.bind('<Return>', confirm)
        overlay.bind('<Escape>', confirm)

        self.root.wait_variable(result_var)
        return result_var.get() or (button_text or "OK")

    def _show_custom_prompt(self, parent, title, message, default_value=""):
        cancel_token = "__MDF_PROMPT_CANCEL__"
        result_var = tk.StringVar(value="")
        overlay, container = self._create_overlay_container(title or "Entrada")

        message_label = tk.Label(
            container,
            text=message,
            justify='left',
            wraplength=440,
            font=('Segoe UI', 10),
            bg=container.cget('bg'),
            fg='#1f2937'
        )
        message_label.pack(padx=24, pady=(12, 10))

        entry_var = tk.StringVar(value=default_value or "")
        entry = ttk.Entry(container, textvariable=entry_var, width=48)
        entry.pack(padx=24, pady=(0, 16))

        button_frame = tk.Frame(container, bg=container.cget('bg'))
        button_frame.pack(padx=24, pady=(0, 18))

        def confirm(event=None):
            result_var.set(entry_var.get())
            self._destroy_overlay()

        def cancel(event=None):
            result_var.set(cancel_token)
            self._destroy_overlay()

        ok_btn = ttk.Button(button_frame, text="OK", command=confirm)
        ok_btn.pack(side=tk.LEFT, padx=(0, 6))

        cancel_btn = ttk.Button(button_frame, text="Cancelar", command=cancel)
        cancel_btn.pack(side=tk.LEFT)

        entry.focus_set()
        entry.icursor(tk.END)
        entry.bind('<Return>', confirm)
        overlay.bind('<Escape>', cancel)

        self.root.wait_variable(result_var)

        value = result_var.get()
        if value == cancel_token:
            return None
        return value

    def _is_browser_window(self, window):
        if gw is None or window is None:
            return False
        try:
            title = (window.title or '').lower()
        except Exception:
            return False
        if not title.strip():
            return False
        return any(keyword in title for keyword in BROWSER_WINDOW_KEYWORDS)

    def _activate_external_window(self, window):
        if gw is None or window is None:
            return False
        try:
            if getattr(window, 'isMinimized', False):
                window.restore()
            window.activate()
            self._last_browser_window = window
            if hasattr(self, 'focus_guardian') and self.focus_guardian:
                self.focus_guardian.remember_browser_window(window)
            time.sleep(0.12)
            self._mark_browser_focus_acquired()
            return True
        except Exception:
            return False

    def _focus_browser_window(self, retry=True):
        if self._is_browser_foreground():
            self._mark_browser_focus_acquired()
            self._switch_to_target_tab()
            return True

        if hasattr(self, 'focus_guardian') and self.focus_guardian:
            if self.focus_guardian.force_browser_focus():
                self._mark_browser_focus_acquired()
                self._switch_to_target_tab()
                return True

        if gw is None:
            if self._activate_browser_via_winapi():
                self._switch_to_target_tab()
                return True
            if retry and not self._taskbar_launch_done and self._launch_browser_via_taskbar():
                self.root.after(900, lambda: self._focus_browser_window(retry=False))
                return False
            if retry:
                self.root.after(600, lambda: self._focus_browser_window(retry=False))
            return False

        candidates = []
        try:
            active = gw.getActiveWindow()
            if self._is_browser_window(active):
                candidates.append(active)
        except Exception:
            active = None

        if self._last_browser_window and self._is_browser_window(self._last_browser_window):
            if self._last_browser_window not in candidates:
                candidates.append(self._last_browser_window)

        try:
            for window in gw.getAllWindows():
                if self._is_browser_window(window) and window not in candidates:
                    candidates.append(window)
        except Exception:
            pass

        for window in candidates:
            if self._activate_external_window(window):
                self._switch_to_target_tab()
                return True

        if self._activate_browser_via_winapi():
            self._switch_to_target_tab()
            return True

        if retry and not self._taskbar_launch_done and self._launch_browser_via_taskbar():
            self.root.after(900, lambda: self._focus_browser_window(retry=False))
            return False

        if retry:
            self.root.after(600, lambda: self._focus_browser_window(retry=False))
        return False

    def _restore_external_focus(self):
        return self._focus_browser_window()

    def _dialog_parent(self):
        return self.root

    def _ensure_dialog_parent_visible(self):
        was_iconified = False
        try:
            state = self.root.state()
            if state in ('iconic', 'iconified', 'withdrawn'):
                was_iconified = True
                self.root.deiconify()
                self.root.update_idletasks()
            self.root.lift()
            if (
                hasattr(self, '_visibility_controller')
                and self.current_execution
                and self.current_execution.is_running
            ):
                self._visibility_controller.enter_interactive()
        except Exception:
            pass
        return was_iconified

    def _restore_dialog_parent_state(self, was_iconified):
        try:
            if was_iconified:
                self.root.iconify()
        except Exception:
            pass
        if (
            hasattr(self, '_visibility_controller')
            and self.current_execution
            and self.current_execution.is_running
        ):
            self._visibility_controller.enter_passive()
        if gw is not None:
            self.root.after(250, self._restore_external_focus)

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
        self.dependency_checker.check_dependencies(include_optional=True, use_cache=False)
        missing_required = self.dependency_checker.get_missing_packages()
        missing_optional = self.dependency_checker.get_missing_optional_packages()

        if missing_required:
            initial_message = "⚠️ Dependências obrigatórias pendentes."
        elif missing_optional:
            optional_text = ', '.join(missing_optional)
            initial_message = f"ℹ️ Todos os itens obrigatórios estão ok. Pacotes recomendados ausentes: {optional_text}."
        else:
            initial_message = "✅ Todas as dependências estão instaladas. Você pode reinstalar se desejar."

        install_window = DependencyInstallWindow(
            self.root,
            checker=self.dependency_checker,
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
        
        self.dependency_checker.check_dependencies(include_optional=True)

        missing_required = self.dependency_checker.get_missing_packages()
        missing_optional = self.dependency_checker.get_missing_optional_packages()

        if not missing_required:
            if missing_optional:
                optional_text = ', '.join(missing_optional)
                message = (
                    "Todas as dependências obrigatórias estão instaladas.\n\n"
                    f"Pacotes recomendados ausentes: {optional_text}.\n"
                    "Eles ajudam a manter o navegador em foco durante a automação."
                )
                self._log_to_history(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️ Falta (opcional): {optional_text}",
                    'warning'
                )
            else:
                message = (
                    "Todas as dependências estão instaladas corretamente!\n\n"
                    "Você pode executar os scripts sem problemas."
                )

            messagebox.showinfo("✅ Dependências OK", message)
            self._log_to_history(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Verificação de dependências: OK",
                'success'
            )
        else:
            response = messagebox.showwarning(
                "❌ Dependências Faltando",
                f"As seguintes dependências estão faltando:\n\n"
                f"{', '.join(missing_required)}\n\n"
                f"É obrigatório instalar antes de usar a automação.\n\n"
                f"Deseja instalar agora?",
                type=messagebox.YESNO
            )
            
            if response == messagebox.YES:
                self._install_dependencies_manual()
            
            self._log_to_history(
                f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Verificação de dependências: Faltando {', '.join(missing_required)}",
                'error'
            )
    
    def _check_and_suggest_dependencies(self):
        """Verifica dependências quando erro é detectado e sugere instalação"""
        self.dependency_checker = DependencyChecker()
        
        self.dependency_checker.check_dependencies(include_optional=True, use_cache=False)
        missing_required = self.dependency_checker.get_missing_packages()
        missing_optional = self.dependency_checker.get_missing_optional_packages()

        if missing_required:
            response = messagebox.showwarning(
                "⚠️  Erro de Módulo Detectado",
                f"O script encontrou um erro de módulo não encontrado.\n\n"
                f"Dependências faltando: {', '.join(missing_required)}\n\n"
                f"Deseja instalar as dependências agora?",
                type=messagebox.YESNO
            )

            if response == messagebox.YES:
                self._install_dependencies_manual()

            self._log_to_history(
                f"[{datetime.now().strftime('%H:%M:%S')}] 📥 Faltando: {', '.join(missing_required)}",
                'error'
            )
        else:
            if missing_optional:
                self._log_to_history(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️ Falta instalar (recomendado): {', '.join(missing_optional)}",
                    'warning'
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

            self._stop_visibility_guard()
            if hasattr(self, 'focus_guardian') and self.focus_guardian:
                self.focus_guardian.stop()
            if hasattr(self, '_visibility_controller'):
                self._visibility_controller.release()
            
            self.root.destroy()


def main():
    root = tk.Tk()
    app = MDFAutomationGUIv2(root)
    root.mainloop()


if __name__ == "__main__":
    main()
