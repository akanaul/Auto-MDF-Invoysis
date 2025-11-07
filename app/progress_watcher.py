"""Helpers to broadcast progress updates from the JSON snapshot."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer, Signal

from data.progress_manager import ProgressManager


class ProgressWatcher(QObject):
    progress_updated = Signal(dict)
    progress_missing = Signal()

    def __init__(self, progress_file: Path, *, interval_ms: int, parent: Optional[QObject] = None) -> None:
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
        if not self._timer.isActive():
            self._emit_snapshot()
            self._timer.start()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self.progress_missing.emit()

    def set_path(self, path: Path) -> None:
        self._path = Path(path)
        self._refresh_watch_list()

    def _emit_snapshot(self) -> None:
        if data := ProgressManager.read_progress(str(self._path)):
            self.progress_updated.emit(data)
        else:
            self.progress_missing.emit()

    def _refresh_watch_list(self) -> None:
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
