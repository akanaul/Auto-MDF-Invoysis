"""Centralized logging utilities for the Auto MDF control center."""

from __future__ import annotations

import re
import unicodedata
from collections import deque
import contextlib
import queue
import threading
import time
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

    def __init__(
        self,
        *,
        max_entries: int = LOG_MAX_LINES,
        parent: Optional[QObject] = None,
        max_queue_size: int = 10000,
        flush_interval: float = 2.0,
        flush_batch: int = 200,
    ) -> None:
        super().__init__(parent)
        self._entries: Deque[LogEntry] = deque(maxlen=max_entries)
        self._raw_lines: Deque[str] = deque(maxlen=max_entries)
        self._current_file: Optional[Path] = None
        self._write_failed = False
        # Queue + worker thread for non-blocking disk writes.
        # We buffer lines in memory and flush to disk periodically or when the
        # buffer reaches a certain size. This reduces frequent small writes
        # which were blocking on slow disks.
        self._max_queue_size = int(max_queue_size) if max_queue_size and int(max_queue_size) > 0 else 10000
        self._write_queue = queue.Queue()
        self._queue_lock = threading.Lock()
        self._queued_items = 0
        self._pause_event = threading.Event()
        self._pause_event.set()  # start unpaused
        self._dropped_lines_count = 0
        self._drop_reported = False
        # flush parameters (configurable)
        self._flush_interval = float(flush_interval)
        self._flush_batch = int(flush_batch)
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()

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
        header = f"### Log de execução - {script_name} ###\n"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - filesystem issues are environmental
            self._write_failed = True
            self.session_failed.emit(f"Não foi possível preparar o diretório de log: {exc}")
            return None

        self._dropped_lines_count = 0
        self._drop_reported = False

        # Notify worker about new session; force enqueue even if backlog exists.
        self._enqueue_message(("start_file", target, header), force=True)

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

        # Enfileira a escrita para o worker. This returns quickly and avoids
        # blocking the caller (often the GUI thread).
        if self._current_file is not None and not self._write_failed:
            enqueued = self._enqueue_message(("write", self._current_file, entry.raw))
            if not enqueued:
                self._dropped_lines_count += 1
                if not self._drop_reported:
                    self._drop_reported = True
                    with contextlib.suppress(Exception):
                        self.session_failed.emit(
                            "Algumas linhas de log foram descartadas devido a alta taxa de geração."
                        )

        self.entry_added.emit(entry)
        return entry

    def abort_session(self, *, delete_file: bool = False) -> None:
        """Cancel the current log session, optionally removing the file."""

        path = self._current_file
        if path is not None:
            self._enqueue_message(("abort", path), force=True)
        self._current_file = None
        self._entries.clear()
        self._raw_lines.clear()
        self._write_failed = False
        self._dropped_lines_count = 0
        self._drop_reported = False
        self.log_cleared.emit()
        if delete_file and path is not None:
            with contextlib.suppress(Exception):
                if path.exists():
                    path.unlink()

    def pause_logging(self) -> None:
        """Pause the background writer thread temporarily."""
        self._pause_event.clear()

    def resume_logging(self) -> None:
        """Resume the background writer thread."""
        self._pause_event.set()

    def _writer_loop(self) -> None:
        """Worker loop that batches writes and flushes periodically.

        Behavior:
        - "start_file": set the current target path and header, do not create
          the file immediately.
        - "write": buffer the line in memory.
        - "stop": force a flush and exit.

        The loop tries to collect multiple messages and flushes when the
        buffer reaches `_flush_batch` or `_flush_interval` seconds pass since
        the last flush.
        """
        current_path: Optional[Path] = None
        header: Optional[str] = None
        buffer: list[str] = []
        last_flush = time.monotonic()
        running = True
        while running:
            try:
                # Wait for a message but with timeout so we can check periodic flush
                msg = self._write_queue.get(timeout=self._flush_interval)
                self._decrement_queue_size()
            except queue.Empty:
                msg = None

            # Check if paused; if so, wait until resumed
            if not self._pause_event.is_set():
                time.sleep(0.1)
                continue

            if msg:
                cmd = msg[0]
                if cmd == "stop":
                    # flush and exit
                    try:
                        if buffer and current_path is not None:
                            self._flush_buffer(current_path, header, buffer)
                    finally:
                        running = False
                        break

                if cmd == "start_file":
                    _, path, hdr = msg
                    # switch session: flush previous buffer first
                    if buffer and current_path is not None:
                        self._flush_buffer(current_path, header, buffer)
                        buffer = []
                    current_path = path
                    header = hdr
                    last_flush = time.monotonic()
                    # Force an immediate flush to create the file with header
                    try:
                        self._flush_buffer(current_path, header, [])
                    except Exception as exc:
                        self._write_failed = True
                        self.session_failed.emit(f"Falha ao preparar arquivo de log: {exc}")
                    continue

                if cmd == "abort":
                    _, path = msg
                    if current_path is not None and path == current_path:
                        buffer = []
                        current_path = None
                        header = None
                    continue

                if cmd == "write":
                    _, path, raw = msg
                    # Only keep if it targets the active session
                    if current_path is None or path != current_path:
                        # drop lines for old sessions
                        continue
                    buffer.append(raw)

            # Determine if we should flush: by size or interval
            now = time.monotonic()
            if buffer and (
                len(buffer) >= self._flush_batch or (now - last_flush) >= self._flush_interval
            ):
                try:
                    if current_path is not None:
                        self._flush_buffer(current_path, header, buffer)
                        buffer = []
                        last_flush = now
                except Exception as exc:
                    self._write_failed = True
                    self.session_failed.emit(f"Falha ao gravar no log: {exc}")
                    # on failure keep running but drop buffer to avoid build-up
                    buffer = []

        # End of loop: ensure nothing is left
        if buffer and current_path is not None:
            try:
                self._flush_buffer(current_path, header, buffer)
            except Exception:
                pass

    def _flush_buffer(self, path: Path, header: Optional[str], lines: list[str]) -> None:
        """Perform the actual disk write of header+lines in a single I/O op.

        This function opens the target file in append or write mode depending
        on whether the file exists. It writes the header only when creating a
        new file.
        """
        try:
            exists = path.exists()
            mode = "a" if exists else "w"
            with open(path, mode, encoding="utf-8") as handle:
                if not exists and header:
                    handle.write(header)
                handle.write("\n".join(lines))
                if lines:
                    handle.write("\n")
                handle.flush()
            # mark write ok
            self._write_failed = False
        except Exception:
            raise

    def shutdown(self, timeout: float = 5.0) -> None:
        """Request the writer thread to stop and wait up to `timeout` seconds.

        This ensures any buffered lines are flushed to disk before the
        application exits. If the thread does not stop within `timeout`, it
        will be left as a daemon thread (process exit will still terminate it).
        """
        try:
            # Enqueue stop request; worker flushes buffer on stop.
            self._enqueue_message(("stop",), force=True)
            if hasattr(self, "_writer_thread") and self._writer_thread.is_alive():
                self._writer_thread.join(timeout)
        except Exception:
            # Best-effort; we don't want shutdown to raise in close handlers
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _enqueue_message(self, message: tuple, *, force: bool = False) -> bool:
        """Attempt to enqueue a message for the writer thread.

        Returns True if the message was enqueued. If the queue backlog exceeds
        `self._max_queue_size` and `force` is False, the message is dropped to
        avoid blocking the producer. Control messages (start/stop/abort) pass
        `force=True` to guarantee delivery.
        """

        with self._queue_lock:
            if not force and self._queued_items >= self._max_queue_size:
                return False
            self._write_queue.put_nowait(message)
            self._queued_items += 1
            return True

    def _decrement_queue_size(self) -> None:
        with self._queue_lock:
            if self._queued_items > 0:
                self._queued_items -= 1

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