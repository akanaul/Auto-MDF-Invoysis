"""Centralized logging utilities for the Auto MDF control center."""

from __future__ import annotations

import re
import unicodedata
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Deque, Optional

from PySide6.QtCore import QObject, Signal

from .constants import LOG_MAX_LINES, LOGS_DIR

_LOG_PATTERN = re.compile(
    r"^\[AutoMDF\]\[(?P<level>[A-Z]+)\]\[(?P<time>\d{2}:\d{2}:\d{2})\]\s*(?P<body>.*)$"
)


@dataclass(slots=True)
class LogEntry:
    """Structured representation of an automation log line."""

    timestamp: datetime
    level: str
    message: str
    raw: str
    display: str


def _sanitize_script_name(raw_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw_name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_only).strip("-._")
    return cleaned or "execucao"


class LogManager(QObject):
    """Manages buffered log entries and persistence to disk."""

    entry_added = Signal(object)
    session_started = Signal(Path)
    session_failed = Signal(str)
    log_cleared = Signal()

    def __init__(self, *, max_entries: int = LOG_MAX_LINES, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._entries: Deque[LogEntry] = deque(maxlen=max_entries)
        self._raw_lines: Deque[str] = deque(maxlen=max_entries)
        self._current_file: Optional[Path] = None
        self._write_failed = False

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    @property
    def raw_lines(self) -> list[str]:
        return list(self._raw_lines)

    @property
    def current_file(self) -> Optional[Path]:
        return self._current_file

    @property
    def write_failed(self) -> bool:
        return self._write_failed

    def start_session(self, script_name: str) -> Optional[Path]:
        """Prepare a new log file and clear in-memory buffers."""

        sanitized = _sanitize_script_name(script_name)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = LOGS_DIR / f"{timestamp}-{sanitized}.log"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(f"### Log de execução - {script_name} ###\n")
        except Exception as exc:  # pragma: no cover - filesystem issues are environmental
            self._write_failed = True
            self.session_failed.emit(f"Não foi possível preparar o arquivo de log: {exc}")
            return None

        self._current_file = target
        self._entries.clear()
        self._raw_lines.clear()
        self._write_failed = False
        self.log_cleared.emit()
        self.session_started.emit(target)
        return target

    def clear_memory(self) -> None:
        """Clear buffered entries without touching the on-disk log."""

        self._entries.clear()
        self._raw_lines.clear()
        self.log_cleared.emit()

    def append_line(self, raw_line: str) -> LogEntry:
        """Register a new log line coming from the automation output."""

        entry = self._parse_line(raw_line)
        self._entries.append(entry)
        self._raw_lines.append(entry.raw)

        if self._current_file is not None and not self._write_failed:
            try:
                with open(self._current_file, "a", encoding="utf-8") as handle:
                    handle.write(entry.raw + "\n")
            except Exception as exc:  # pragma: no cover - disk write failure
                self._write_failed = True
                self.session_failed.emit(f"Falha ao gravar no log: {exc}")

        self.entry_added.emit(entry)
        return entry

    def export_to(self, destination: Path) -> bool:
        """Export the current buffered log to a user-selected location."""

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, "w", encoding="utf-8") as handle:
                handle.write("\n".join(self._raw_lines))
                if self._raw_lines:
                    handle.write("\n")
        except Exception as exc:  # pragma: no cover - propagate failure
            self.session_failed.emit(f"Falha ao exportar log: {exc}")
            return False
        return True

    def _parse_line(self, raw_line: str) -> LogEntry:
        match = _LOG_PATTERN.match(raw_line)
        if match:
            level = match.group("level").upper()
            time_fragment = match.group("time")
            message = match.group("body").strip()
            today = datetime.now().date()
            timestamp = datetime.strptime(f"{today} {time_fragment}", "%Y-%m-%d %H:%M:%S")
            display = f"[{time_fragment}] [{level}] {message}"
            normalized_raw = raw_line
        else:
            level = "INFO"
            timestamp = datetime.now()
            message = raw_line.strip()
            display = f"[{timestamp.strftime('%H:%M:%S')}] [INFO] {message}"
            normalized_raw = raw_line
        return LogEntry(timestamp=timestamp, level=level, message=message, raw=normalized_raw, display=display)