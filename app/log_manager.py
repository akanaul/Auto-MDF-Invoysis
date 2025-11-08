"""Centralized logging utilities for the Auto MDF control center.

Guia de edição (resumido)
- Modificável pelo usuário:
    - Parâmetros de logs como `LOG_MAX_LINES` e diretório de `LOGS_DIR` (preferencialmente via `app/constants.py`).
- Requer atenção:
    - Mudanças no código de escrita em disco, filas de escrita, threads de I/O e flush podem causar perda de logs ou bloqueio da UI.
    - Teste localmente em cenários de alta carga antes de commitar.
- Apenas para devs:
    - Reescrever a arquitetura de buffering, threads e gerenciamento de sessão de logs.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from __future__ import annotations

import contextlib
import re
import unicodedata
from collections import deque
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from .constants import LOG_MAX_LINES, LOGS_DIR

_LOG_PATTERN = re.compile(
    r"^\[AutoMDF\]\[(?P<level>[A-Z]+)\]\[(?P<time>\d{2}:\d{2}:\d{2})\]\s*(?P<body>.*)$"
)


QueueMessage = Tuple[Any, ...]


@dataclass(slots=True)
class LogEntry:
    """Representação estruturada de uma linha de log da automação."""

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
    """Gerencia entradas de log em memória e a persistência em disco."""

    # Seguro ajustar: limites de retenção ou formato de exportação.
    # Requer atenção: padrão de nome dos arquivos e regex de `_parse_line` — mantenha compatibilidade com os scripts.
    # Apenas para devs: ciclo de vida da sessão, sinais ou uso da deque; demais componentes esperam o comportamento atual.

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
        # Fila + thread trabalhadora para escrita em disco sem bloquear a UI.
        # As linhas ficam em memória e são descarregadas periodicamente ou quando
        # o buffer atinge um determinado tamanho. Isso reduz escritas pequenas
        # frequentes que travavam discos mais lentos.
        self._max_queue_size = max_queue_size if max_queue_size > 0 else 10000
        self._write_queue: queue.Queue[QueueMessage] = queue.Queue()
        self._queue_lock = threading.Lock()
        self._queued_items = 0
        self._pause_event = threading.Event()
        self._pause_event.set()  # inicia sem pausa
        self._dropped_lines_count = 0
        self._drop_reported = False
        # parâmetros de flush (configuráveis)
        self._flush_interval = flush_interval if flush_interval > 0 else 2.0
        self._flush_batch = flush_batch if flush_batch > 0 else 200
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
        """Prepara um novo arquivo de log e limpa os buffers em memória."""

        sanitized = _sanitize_script_name(script_name)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = LOGS_DIR / f"{timestamp}-{sanitized}.log"
        header = f"### Log de execução - {script_name} ###\n"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except (
            Exception
        ) as exc:  # pragma: no cover - filesystem issues are environmental
            self._write_failed = True
            self.session_failed.emit(
                f"Não foi possível preparar o diretório de log: {exc}"
            )
            return None

        self._dropped_lines_count = 0
        self._drop_reported = False

        # Notify worker about new session; force enqueue even if backlog exists.
        self._enqueue_message(("start_file", target, header), force=True)

        self._current_file = target
        self.clear_memory()
        self._write_failed = False
        self.session_started.emit(target)
        return target

    def clear_memory(self) -> None:
        """Limpa entradas em memória sem alterar o arquivo de log em disco."""

        self._entries.clear()
        self._raw_lines.clear()
        self.log_cleared.emit()

    def append_line(self, raw_line: str) -> LogEntry:
        """Registra uma nova linha de log proveniente da automação."""

        entry = self._parse_line(raw_line)
        self._entries.append(entry)
        self._raw_lines.append(entry.raw)

        # Enfileira a escrita para o worker; retorna rápido e evita
        # bloquear quem chamou (geralmente a thread da GUI).
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
        """Cancela a sessão de log atual, opcionalmente removendo o arquivo."""

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
        """Pausa temporariamente a thread de escrita em segundo plano."""
        self._pause_event.clear()

    def resume_logging(self) -> None:
        """Retoma a thread de escrita em segundo plano."""
        self._pause_event.set()

    def _writer_loop(self) -> None:  # sourcery skip: low-code-quality
        """Loop do worker que agrupa escritas e realiza flush periódico.

        Comportamento:
        - "start_file": define o caminho/arquivo atual e o cabeçalho, sem criar o arquivo imediatamente.
        - "write": coloca a linha no buffer em memória.
        - "stop": força um flush e encerra a thread.

        O loop tenta juntar múltiplas mensagens e faz flush quando o buffer atinge `_flush_batch`
        ou quando `_flush_interval` segundos passam desde o último flush.
        """
        current_path: Optional[Path] = None
        header: Optional[str] = None
        buffer: list[str] = []
        last_flush = time.monotonic()
        running = True
        while running:
            try:
                # Aguarda uma mensagem com timeout para permitir o flush periódico
                msg = self._write_queue.get(timeout=self._flush_interval)
                self._decrement_queue_size()
            except queue.Empty:
                msg = None

            # Verifica se está pausado; caso positivo, espera até retomar
            if not self._pause_event.is_set():
                time.sleep(0.1)
                continue

            if msg:
                cmd = msg[0]
                if cmd == "stop":
                    # faz o flush e encerra
                    try:
                        if buffer and current_path is not None:
                            self._flush_buffer(current_path, header, buffer)
                    finally:
                        running = False
                    break

                if cmd == "start_file":
                    _, path, hdr = msg
                    # troca de sessão: descarrega o buffer anterior antes
                    if buffer and current_path is not None:
                        self._flush_buffer(current_path, header, buffer)
                        buffer = []
                    current_path = path
                    header = hdr
                    last_flush = time.monotonic()
                    # Força um flush imediato para criar o arquivo com o cabeçalho
                    if current_path is not None:
                        try:
                            self._flush_buffer(current_path, header, [])
                        except Exception as exc:
                            self._write_failed = True
                            self.session_failed.emit(
                                f"Falha ao preparar arquivo de log: {exc}"
                            )
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
                    # Só mantém se apontar para a sessão ativa
                    if current_path is None or path != current_path:
                        # descarta linhas de sessões antigas
                        continue
                    buffer.append(raw)

            # Decide se precisa fazer flush: por tamanho ou intervalo
            now = time.monotonic()
            if buffer and (
                len(buffer) >= self._flush_batch
                or (now - last_flush) >= self._flush_interval
            ):
                try:
                    if current_path is not None:
                        self._flush_buffer(current_path, header, buffer)
                        buffer = []
                        last_flush = now
                except Exception as exc:
                    self._write_failed = True
                    self.session_failed.emit(f"Falha ao gravar no log: {exc}")
                    # em caso de erro continua rodando, mas descarta o buffer para evitar acúmulo
                    buffer = []

        # Final do loop: garante que nada ficou pendente
        if buffer and current_path is not None:
            with contextlib.suppress(Exception):
                self._flush_buffer(current_path, header, buffer)

    def _flush_buffer(
        self, path: Path, header: Optional[str], lines: list[str]
    ) -> None:
        """Realiza a escrita em disco do cabeçalho e linhas em uma única operação.

        Esta função abre o arquivo alvo em modo append ou write conforme a sua
        existência. O cabeçalho é gravado apenas na criação de um novo arquivo.
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
            # marca a escrita como bem-sucedida
            self._write_failed = False
        except Exception:
            raise

    def shutdown(self, timeout: float = 5.0) -> None:
        """Solicita a parada da thread de escrita e aguarda até `timeout` segundos.

        Isso garante que as linhas em buffer sejam gravadas em disco antes do
        encerramento da aplicação. Se a thread não parar dentro do `timeout`,
        ela permanece como daemon (o fim do processo ainda a encerrará).
        """
        with contextlib.suppress(Exception):
            # Enfileira a requisição de stop; o worker faz flush ao encerrar.
            self._enqueue_message(("stop",), force=True)
            if hasattr(self, "_writer_thread") and self._writer_thread.is_alive():
                self._writer_thread.join(timeout)

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------
    def _enqueue_message(
        self, message: Tuple[Any, ...], *, force: bool = False
    ) -> bool:
        """Tenta enfileirar uma mensagem para a thread de escrita.

        Retorna True quando a mensagem foi aceita. Se o backlog ultrapassar
        `self._max_queue_size` e `force` for False, a mensagem é descartada para
        não bloquear quem produz. Mensagens de controle (start/stop/abort) usam
        `force=True` para garantir a entrega.
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
        """Exporta o log em memória para um local escolhido pelo usuário."""

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
        if match := _LOG_PATTERN.match(raw_line):
            level = match.group("level").upper()
            time_fragment = match.group("time")
            message = match.group("body").strip()
            today = datetime.now().date()
            timestamp = datetime.strptime(
                f"{today} {time_fragment}", "%Y-%m-%d %H:%M:%S"
            )
            display = f"[{time_fragment}] [{level}] {message}"
        else:
            level = "INFO"
            timestamp = datetime.now()
            message = raw_line.strip()
            display = f"[{timestamp.strftime('%H:%M:%S')}] [INFO] {message}"
        normalized_raw = raw_line
        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            raw=normalized_raw,
            display=display,
        )
