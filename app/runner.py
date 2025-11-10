"""Infrastructure for running automation scripts in a background thread.

Guia de edição (resumido)
- Modificável pelo usuário:
    - Scripts a serem executados (ex.: `scripts/`) e parâmetros passados ao runner.
- Requer atenção:
    - Alterações em como processos são spawnados, mensagens via bridge, timeouts e locks podem afetar estabilidade.
    - Teste exaustivamente com scripts reais após qualquer alteração.
- Apenas para devs:
    - Reescrita do modelo de comunicação bridge, uso de pipes e tratamento do subprocesso em diferentes OS.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from .constants import BRIDGE_ACK, BRIDGE_CANCEL, BRIDGE_PREFIX


class ScriptRunner(QThread):
    """Launches automation scripts and streams their output safely to the GUI."""

    log_message = Signal(str)
    bridge_payload = Signal(dict)
    process_started = Signal(Path)
    process_finished = Signal(int)

    def __init__(self, python_executable: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.python_executable = python_executable
        self._script_path: Optional[Path] = None
        self._progress_file: Optional[Path] = None
        self._bridge_responses: queue.Queue[str] = queue.Queue()
        self._stop_requested = threading.Event()
        self._process_lock = threading.Lock()
        self._process: Optional[subprocess.Popen[str]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_script(self, script_path: Path, *, progress_file: Optional[Path] = None) -> bool:
        if self.isRunning():
            return False
        self._script_path = script_path
        self._progress_file = progress_file
        self._stop_requested.clear()
        self._bridge_responses = queue.Queue()
        self.start()
        return True

    def stop_script(self) -> None:
        self._stop_requested.set()
        # Ensure any pending bridge waits are released.
        with contextlib.suppress(queue.Full):
            self._bridge_responses.put(BRIDGE_CANCEL)
        with self._process_lock:
            proc = self._process
        if proc is None:
            return
        with contextlib.suppress(Exception):
            proc.terminate()

    def send_bridge_response(self, value: str) -> None:
        with contextlib.suppress(queue.Full):
            self._bridge_responses.put(value)

    # ------------------------------------------------------------------
    # QThread overrides
    # ------------------------------------------------------------------
    def run(self) -> None:  # type: ignore[override]
        script_path = self._script_path
        if script_path is None:
            return

        env = os.environ.copy()
        # env["MDF_BRIDGE_ACTIVE"] = "1"  # Desabilitado para evitar travamentos
        env["MDF_BRIDGE_PREFIX"] = BRIDGE_PREFIX
        env["MDF_BRIDGE_ACK"] = BRIDGE_ACK
        env["MDF_BRIDGE_CANCEL"] = BRIDGE_CANCEL
        if self._progress_file is not None:
            env["MDF_PROGRESS_FILE"] = str(self._progress_file)

        project_root = Path(__file__).resolve().parent.parent
        pythonpath_components = [str(project_root), str(script_path.parent)]
        if existing_python_path := env.get("PYTHONPATH"):
            pythonpath_components.append(existing_python_path)
        env["PYTHONPATH"] = os.pathsep.join(component for component in pythonpath_components if component)

        try:
            process = subprocess.Popen(
                [self.python_executable, "-u", str(script_path)],
                cwd=str(script_path.parent),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
        except Exception as exc:
            self.log_message.emit(f"Falha ao iniciar {script_path.name}: {exc}")
            self.process_finished.emit(-1)
            return

        with self._process_lock:
            self._process = process
        self.process_started.emit(script_path)

        try:
            assert process.stdout is not None  # for mypy/static hints
            for raw_line in iter(process.stdout.readline, ""):
                if raw_line == "" and process.poll() is not None:
                    break
                line = raw_line.rstrip("\r\n")
                if not line:
                    continue
                if line.startswith(BRIDGE_PREFIX):
                    payload_json = line[len(BRIDGE_PREFIX) :]
                    try:
                        payload = json.loads(payload_json)
                    except json.JSONDecodeError as exc:
                        self.log_message.emit(f"Bridge payload inválido: {exc} :: {payload_json}")
                        self._write_response(BRIDGE_ACK)
                        continue
                    self.bridge_payload.emit(payload)
                    try:
                        response = self._bridge_responses.get()
                    except Exception:
                        response = BRIDGE_CANCEL
                    if not response:
                        response = BRIDGE_CANCEL
                    self._write_response(response)
                    continue
                self.log_message.emit(line)
                if self._stop_requested.is_set():
                    break
        finally:
            # Final termination guard
            if self._stop_requested.is_set() and process.poll() is None:
                with contextlib.suppress(Exception):
                    process.terminate()
                    process.wait(timeout=1.5)
                if process.poll() is None:
                    with contextlib.suppress(Exception):
                        process.kill()
            exit_code = process.wait()
            self.process_finished.emit(exit_code)
            with self._process_lock:
                self._process = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _write_response(self, value: str) -> None:
        with self._process_lock:
            process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            return
        try:
            process.stdin.write(value + "\n")
            process.stdin.flush()
        except Exception as exc:
            self.log_message.emit(f"Erro ao enviar resposta ao script: {exc}")
