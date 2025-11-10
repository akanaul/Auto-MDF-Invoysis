"""Auxiliares para transmitir atualizações de progresso a partir do arquivo JSON."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer, Signal

from data.progress_manager import ProgressManager


class ProgressWatcher(QObject):
    """Observa o arquivo de progresso JSON e emite sinais quando há dados ou ausência deles."""

    # Seguro ajustar: intervalo de polling padrão ou regras de throttling.
    # Requer atenção: comportamento do QFileSystemWatcher — teste ao rodar em shares de rede.
    # Apenas para devs: alterar o payload do snapshot; a MainWindow assume o esquema do ProgressManager.

    progress_updated = Signal(dict)
    progress_missing = Signal()

    def __init__(
        self, progress_file: Path, *, interval_ms: int, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._path = Path(progress_file)
        self._interval_ms = max(200, interval_ms)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._refresh_watch_list)
        self._watcher.directoryChanged.connect(self._refresh_watch_list)
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._emit_snapshot)
        self._refresh_watch_list()

    def start(self) -> None:
        """Inicia o polling e a emissão de atualizações para o arquivo de progresso."""
        if not self._timer.isActive():
            self._emit_snapshot()
            self._timer.start()

    def stop(self) -> None:
        """Interrompe o polling e avisa ouvintes que os dados estão indisponíveis."""
        if self._timer.isActive():
            self._timer.stop()
        self.progress_missing.emit()

    def set_path(self, path: Path) -> None:
        """Aponta o watcher para um outro arquivo de progresso JSON."""
        self._path = Path(path)
        self._refresh_watch_list()

    def _emit_snapshot(self) -> None:
        """Emite os dados atuais de progresso ou sinaliza que estão ausentes."""
        if data := ProgressManager.read_progress(str(self._path)):
            self.progress_updated.emit(data)
        else:
            self.progress_missing.emit()

    def _refresh_watch_list(self) -> None:
        """Mantém o QFileSystemWatcher alinhado com o arquivo monitorado."""
        paths = self._watcher.files()
        for existing in paths:
            self._watcher.removePath(existing)
        directories = self._watcher.directories()
        for existing in directories:
            self._watcher.removePath(existing)
        if self._path.exists():
            with contextlib.suppress(Exception):
                self._watcher.addPath(str(self._path))
        parent_dir = self._path.parent
        if parent_dir.exists():
            with contextlib.suppress(Exception):
                self._watcher.addPath(str(parent_dir))
