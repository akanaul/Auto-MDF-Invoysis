"""
progress_manager.py - Gerenciador de progresso em tempo real para automação MDF-e
Permite que scripts de automação comuniquem seu progresso via arquivo JSON compartilhado.
"""

import json
import threading
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class ProgressManager:
    """Gerencia o progresso da automação em tempo real"""

    DEFAULT_FILE_NAME = "automation_progress.json"
    PROGRESS_FILE = os.environ.get('MDF_PROGRESS_FILE', DEFAULT_FILE_NAME)

    def __init__(self, progress_file: Optional[str] = None):
        self.progress_path = self._resolve_progress_path(progress_file)
        # Manter compatibilidade para consumidores que ainda consultam o atributo de classe
        ProgressManager.PROGRESS_FILE = str(self.progress_path)

        self.progress_data: Dict[str, Any] = {
            "status": "idle",  # idle, running, paused, completed, error
            "percentage": 0,
            "current_step": "Aguardando início...",
            "total_steps": 0,
            "current_step_number": 0,
            "start_time": None,
            "elapsed_seconds": 0,
            "messages": [],
            "errors": [],
            "estimated_time_remaining": None,
        }
        self.lock = threading.Lock()
        self._save_progress()

    @classmethod
    def _resolve_progress_path(cls, custom_path: Optional[str] = None) -> Path:
        """Resolve o caminho do arquivo de progresso considerando overrides e variáveis de ambiente."""
        if custom_path:
            return Path(custom_path)

        env_path = os.environ.get('MDF_PROGRESS_FILE')
        if env_path:
            return Path(env_path)

        return Path(cls.DEFAULT_FILE_NAME)
    
    def start(self, total_steps: int = 100):
        """Inicia o monitoramento de progresso"""
        with self.lock:
            self.progress_data["status"] = "running"
            self.progress_data["percentage"] = 0
            self.progress_data["total_steps"] = total_steps
            self.progress_data["current_step_number"] = 0
            self.progress_data["start_time"] = datetime.now().isoformat()
            self.progress_data["messages"] = []
            self.progress_data["errors"] = []
            self._save_progress()
    
    def update(self, percentage: int, step: str, step_number: int = None):
        """Atualiza o progresso"""
        with self.lock:
            self.progress_data["percentage"] = max(0, min(100, percentage))
            self.progress_data["current_step"] = step
            
            if step_number is not None:
                self.progress_data["current_step_number"] = step_number
            
            # Calcular tempo estimado restante
            if self.progress_data["start_time"] and percentage > 0 and percentage < 100:
                start = datetime.fromisoformat(self.progress_data["start_time"])
                elapsed = (datetime.now() - start).total_seconds()
                rate = elapsed / percentage
                remaining = rate * (100 - percentage)
                self.progress_data["estimated_time_remaining"] = int(remaining)
            
            self._save_progress()
    
    def add_log(self, message: str):
        """Adiciona mensagem de log"""
        with self.lock:
            timestamp = datetime.now().isoformat()
            self.progress_data["messages"].append({
                "timestamp": timestamp,
                "message": message,
                "type": "info"
            })
            self._save_progress()
    
    def add_warning(self, message: str):
        """Adiciona aviso"""
        with self.lock:
            timestamp = datetime.now().isoformat()
            self.progress_data["messages"].append({
                "timestamp": timestamp,
                "message": message,
                "type": "warning"
            })
            self._save_progress()
    
    def add_error(self, message: str):
        """Adiciona erro"""
        with self.lock:
            timestamp = datetime.now().isoformat()
            self.progress_data["errors"].append({
                "timestamp": timestamp,
                "message": message
            })
            self.progress_data["messages"].append({
                "timestamp": timestamp,
                "message": message,
                "type": "error"
            })
            self._save_progress()
    
    def pause(self):
        """Pausa o progresso"""
        with self.lock:
            self.progress_data["status"] = "paused"
            self._save_progress()
    
    def resume(self):
        """Retoma o progresso"""
        with self.lock:
            self.progress_data["status"] = "running"
            self._save_progress()
    
    def complete(self, message: str = "Automação concluída com sucesso!"):
        """Marca como concluído"""
        with self.lock:
            self.progress_data["status"] = "completed"
            self.progress_data["percentage"] = 100
            self.progress_data["current_step"] = message
            self.progress_data["messages"].append({
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "type": "success"
            })
            self._save_progress()
    
    def error(self, error_message: str):
        """Marca como erro"""
        timestamp = datetime.now().isoformat()
        with self.lock:
            self.progress_data["status"] = "error"
            self.progress_data["current_step"] = f"Erro: {error_message}"
            self.progress_data["errors"].append({
                "timestamp": timestamp,
                "message": error_message
            })
            self.progress_data["messages"].append({
                "timestamp": timestamp,
                "message": error_message,
                "type": "error"
            })
            self._save_progress()

    def _save_progress(self):
        """Salva dados de progresso em arquivo JSON"""
        try:
            path = self.progress_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar progresso: {e}")

    @classmethod
    def read_progress(cls, progress_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Lê dados de progresso do arquivo JSON"""
        progress_path = cls._resolve_progress_path(progress_file)

        if not progress_path.exists():
            return None

        try:
            with open(progress_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler progresso: {e}")
            return None

    @classmethod
    def reset(cls, progress_file: Optional[str] = None):
        """Reseta o arquivo de progresso"""
        progress_path = cls._resolve_progress_path(progress_file)
        if progress_path.exists():
            progress_path.unlink()


# Decorator para facilitar rastreamento de funções
def track_progress(step_name: str, step_number: int = None):
    """Decorator que rastreia execução de funções"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            progress = ProgressManager()
            progress.add_log(f"Iniciando: {step_name}")
            try:
                result = func(*args, **kwargs)
                progress.add_log(f"Concluído: {step_name}")
                return result
            except Exception as e:
                progress.add_error(f"Erro em {step_name}: {str(e)}")
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # Exemplo de uso
    pm = ProgressManager()
    pm.start(total_steps=10)
    
    steps = [
        (10, "Abrindo formulário"),
        (20, "Preenchendo dados de MDF"),
        (30, "Preenchendo dados de MDF"),
        (50, "Preenchendo dados de MDF"),
        (70, "Preenchendo dados de MDF"),
        (85, "Preenchsendo dados de MDF"),
        (100, "Finalizando..."),
    ]
    
    for percent, step in steps:
        pm.update(percent, step)
        pm.add_log(f"[{percent}%] {step}")
        print(f"[{percent}%] {step}")
        time.sleep(1)
    
    pm.complete()
    print("✅ Progresso concluído!")
