"""Main window for the modern Auto MDF automation control center."""
# sourcery skip: all

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from data.progress_manager import ProgressManager

from . import dialogs
from .progress_overlay import ProgressOverlay
from .constants import (
    LOGS_DIR,
    LOG_MAX_LINES,
    PROGRESS_REFRESH_INTERVAL_MS,
    SCRIPTS_DIR,
)
from .runner import ScriptRunner

try:  # pragma: no cover - optional dependency runtime guard
    from data.automation_focus import focus
except ModuleNotFoundError:  # pragma: no cover
    focus = None  # type: ignore[assignment]


_AUTOMDF_LOG_RE = re.compile(r"^\[AutoMDF\]\[(?P<level>[A-Z]+)\]\[(?P<time>\d{2}:\d{2}:\d{2})\]\s*(?P<body>.*)$")
_LEVEL_LABELS = {
    "DEBUG": "Detalhe",
    "INFO": "Informação",
    "WARNING": "Aviso",
    "ERROR": "Erro",
}




class MainWindow(QMainWindow):
    def __init__(self, python_executable: str) -> None:
        super().__init__()
        self.python_executable = python_executable
        self.setWindowTitle("Auto MDF InvoISys")
        self.resize(1040, 680)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

        self._default_browser_tab = self._normalize_browser_tab(os.environ.get("MDF_BROWSER_TAB", "1"))
        os.environ["MDF_BROWSER_TAB"] = str(self._default_browser_tab)
        self._default_browser_window_hint = os.environ.get("MDF_BROWSER_TITLE_HINT", "").strip()
        raw_slot = (
            os.environ.get("MDF_BROWSER_TASKBAR_SLOT")
            or os.environ.get("MDF_EDGE_TASKBAR_SLOT")
            or "1"
        )
        self._default_taskbar_slot = self._normalize_taskbar_slot(raw_slot)
        os.environ["MDF_BROWSER_TASKBAR_SLOT"] = str(self._default_taskbar_slot)
        os.environ["MDF_EDGE_TASKBAR_SLOT"] = str(self._default_taskbar_slot)

        self._current_script: Optional[Path] = None
        self._current_script_label: str = ""
        self._current_log_path: Optional[Path] = None
        self._log_buffer: list[str] = []
        self._raw_log_buffer: list[str] = []
        self._log_write_failed = False
        self._automation_active = False
        self._user_requested_stop = False
        self.progress_file = Path(ProgressManager.DEFAULT_FILE_PATH)
        self._progress_overlay = ProgressOverlay()

        self.runner = ScriptRunner(python_executable, self)

        self._build_ui()
        self._connect_signals()

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(PROGRESS_REFRESH_INTERVAL_MS)
        self._progress_timer.timeout.connect(self._refresh_progress)
        self._progress_timer.start()

        self._refresh_script_list()
        self._refresh_browser_windows()
        self._update_log_buttons(False)
        self._apply_idle_progress_state()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _create_row(self, parent_layout: QVBoxLayout, spacing: int = 8) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(spacing)
        parent_layout.addLayout(row)
        return row

    def _new_row(self, parent_layout: QVBoxLayout, label_text: str) -> tuple[QHBoxLayout, QLabel]:
        row = self._create_row(parent_layout)
        label = QLabel(label_text)
        row.addWidget(label)
        return row, label

    # sourcery skip: extract-method
    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        script_row, _ = self._new_row(layout, "Script de automação:")

        self.script_combo = QComboBox()
        self.script_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        script_row.addWidget(self.script_combo)

        self.refresh_scripts_button = QPushButton("Atualizar lista")
        script_row.addWidget(self.refresh_scripts_button)

        self.run_button = QPushButton("Iniciar")
        self.stop_button = QPushButton("Parar")
        self.stop_button.setEnabled(False)
        script_row.addWidget(self.run_button)
        script_row.addWidget(self.stop_button)

        browser_row, _ = self._new_row(layout, "Aba inicial do Microsoft Edge:")

        self.browser_tab_combo = QComboBox()
        self.browser_tab_combo.setToolTip("Escolha a aba que deve receber o foco antes da automação (0 mantém a atual).")
        for tab in range(10):
            text = "0 - manter aba atual" if tab == 0 else f"{tab}"
            self.browser_tab_combo.addItem(text, tab)
        default_index = self.browser_tab_combo.findData(self._default_browser_tab)
        if default_index >= 0:
            self.browser_tab_combo.setCurrentIndex(default_index)
        browser_row.addWidget(self.browser_tab_combo)
        browser_row.addStretch(1)

        taskbar_row, _ = self._new_row(layout, "Posição do Edge na barra de tarefas:")

        self.taskbar_slot_spin = QSpinBox()
        self.taskbar_slot_spin.setRange(1, 9)
        self.taskbar_slot_spin.setValue(self._default_taskbar_slot)
        self.taskbar_slot_spin.setToolTip("Informe a posição do Microsoft Edge fixado na barra de tarefas do Windows (Win+Número).")
        taskbar_row.addWidget(self.taskbar_slot_spin)
        taskbar_row.addStretch(1)

        window_row, _ = self._new_row(layout, "Janela do Microsoft Edge:")

        self.browser_window_combo = QComboBox()
        self.browser_window_combo.setEditable(True)
        self.browser_window_combo.setPlaceholderText("Detectar Microsoft Edge automaticamente")
        window_row.addWidget(self.browser_window_combo)

        self.refresh_windows_button = QPushButton("Atualizar janelas")
        window_row.addWidget(self.refresh_windows_button)
        window_row.addStretch(1)

        status_row, self.status_label = self._new_row(layout, "Status:")
        self.status_label.setText("Aguardando automação...")
        self.status_label.setWordWrap(True)
        status_row.addStretch(1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.progress_bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        status_row.addWidget(self.progress_bar)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_view, stretch=1)

        log_actions = self._create_row(layout)

        self.verify_deps_button = QPushButton("Verificar dependências")
        self.export_log_button = QPushButton("Exportar log")
        self.open_log_button = QPushButton("Abrir log")
        log_actions.addWidget(self.verify_deps_button)
        log_actions.addWidget(self.export_log_button)
        log_actions.addWidget(self.open_log_button)
        log_actions.addStretch(1)

        self.setCentralWidget(central)
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

    def _connect_signals(self) -> None:
        self.run_button.clicked.connect(self._on_run_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.refresh_scripts_button.clicked.connect(self._refresh_script_list)
        self.verify_deps_button.clicked.connect(self._on_verify_dependencies)
        self.export_log_button.clicked.connect(self._on_export_log)
        self.open_log_button.clicked.connect(self._on_open_log)
        self.refresh_windows_button.clicked.connect(self._refresh_browser_windows)

        self.runner.log_message.connect(self._on_log_message)
        self.runner.bridge_payload.connect(self._on_bridge_payload)
        self.runner.process_started.connect(self._on_process_started)
        self.runner.process_finished.connect(self._on_process_finished)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_run_clicked(self) -> None:
        script_name = self.script_combo.currentText().strip()
        if not script_name:
            QMessageBox.information(self, "Nenhum script", "Selecione um script na lista.")
            return

        script_path = (SCRIPTS_DIR / script_name).resolve()
        if not script_path.exists():
            QMessageBox.warning(
                self,
                "Arquivo não encontrado",
                f"O script '{script_name}' não foi localizado em {SCRIPTS_DIR}.",
            )
            self._refresh_script_list()
            return

        tab_choice = self._selected_browser_tab()
        os.environ["MDF_BROWSER_TAB"] = str(tab_choice)

        window_hint = self._selected_browser_window_hint()
        if window_hint:
            os.environ["MDF_BROWSER_TITLE_HINT"] = window_hint
        else:
            os.environ.pop("MDF_BROWSER_TITLE_HINT", None)
        self._default_browser_window_hint = window_hint

        slot_choice = self._selected_taskbar_slot()
        os.environ["MDF_BROWSER_TASKBAR_SLOT"] = str(slot_choice)
        os.environ["MDF_EDGE_TASKBAR_SLOT"] = str(slot_choice)

        self._user_requested_stop = False
        self._start_new_log_session(script_name)

        if focus is not None:
            with contextlib.suppress(Exception):
                focus.set_taskbar_slot(slot_choice)
                focus.prepare_for_execution()
                focus.target_tab = tab_choice
                focus.set_preferred_window_title(window_hint)
                focus.ensure_browser_focus(allow_taskbar=True, preserve_tab=False)

        ProgressManager.reset(str(self.progress_file))

        if not self.runner.start_script(script_path, progress_file=self.progress_file):
            QMessageBox.warning(
                self,
                "Execução em andamento",
                "Já existe uma automação em execução no momento.",
            )
            return

        self._current_script = script_path
        self._current_script_label = self._friendly_script_label(script_path)
        self._set_running_state(True)
        self.status_label.setText(f"Executando {script_path.name}...")

    def _on_stop_clicked(self) -> None:
        if not self.runner.isRunning():
            QMessageBox.information(self, "Nenhuma execução", "Nenhum script está em execução.")
            return
        self._user_requested_stop = True
        self.runner.stop_script()
        self.status_label.setText("Encerrando script...")
        self._progress_overlay.show_indeterminate("Encerrando automação...")

    def _on_export_log(self) -> None:
        if not self._raw_log_buffer:
            QMessageBox.information(self, "Log vazio", "Não há conteúdo para exportar.")
            return
        default_name = "execucao.log"
        if self._current_script is not None:
            default_name = f"{self._current_script.stem}.log"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar log",
            str(LOGS_DIR / default_name),
            "Arquivo de log (*.log);;Todos os arquivos (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(self._raw_log_buffer) + "\n")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao exportar", f"Falha ao salvar o log:\n{exc}")
            return
        self.statusBar().showMessage(f"Log exportado para {path}", 5000)

    def _on_open_log(self) -> None:
        if not self._current_log_path or not self._current_log_path.exists():
            QMessageBox.information(self, "Log indisponível", "Nenhum arquivo de log disponível.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self._current_log_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self._current_log_path)])
            else:
                subprocess.Popen(["xdg-open", str(self._current_log_path)])
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao abrir log", f"Não foi possível abrir o log:\n{exc}")

    def _on_verify_dependencies(self) -> None:
        missing = []
        for module_name in ("PySide6", "pyautogui", "pyperclip"):
            try:
                __import__(module_name)
            except ModuleNotFoundError:
                missing.append(module_name)

        if not missing:
            QMessageBox.information(
                self,
                "Dependências",
                "Todas as dependências obrigatórias estão disponíveis.",
            )
            return

        details = "\n".join(f"- {name}" for name in missing)
        QMessageBox.warning(
            self,
            "Dependências ausentes",
            "Não foi possível carregar os módulos a seguir:\n" + details,
        )

    def _on_log_message(self, line: str) -> None:
        self._append_log(line)

    def _on_bridge_payload(self, payload: dict) -> None:
        response = dialogs.handle_bridge_payload(self, payload)
        self.runner.send_bridge_response(response)

    def _on_process_started(self, script_path: Path) -> None:
        self._automation_active = True
        self.status_label.setText(f"Executando {script_path.name}...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        overlay_label = self._current_script_label or script_path.stem
        self._progress_overlay.show_indeterminate(f"Executando {overlay_label}...")
        self._update_log_buttons(True)

    def _on_process_finished(self, exit_code: int) -> None:
        self._automation_active = False
        self._set_running_state(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if exit_code == 0 else 0)
        summary = "Execução concluída com sucesso." if exit_code == 0 else f"Execução encerrada (código {exit_code})."
        if self._user_requested_stop and exit_code != 0:
            summary = "Execução interrompida pelo usuário."
        self.status_label.setText(summary)
        if self._user_requested_stop:
            self._progress_overlay.show_result(True, "Automação interrompida pelo usuário.", auto_hide_ms=3500)
        elif exit_code == 0:
            self._progress_overlay.show_result(True, "Automação concluída com sucesso.", auto_hide_ms=3500)
        else:
            self._progress_overlay.show_result(False, f"Falha na automação (código {exit_code}).", auto_hide_ms=6000)
        if exit_code != 0 and not self._user_requested_stop:
            QMessageBox.warning(
                self,
                "Execução finalizada",
                f"O script terminou com código {exit_code}. Consulte o log para detalhes.",
            )
        self._user_requested_stop = False
        self._update_log_buttons(bool(self._current_log_path and self._current_log_path.exists()))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _refresh_script_list(self) -> None:
        scripts = sorted(script.name for script in SCRIPTS_DIR.glob("*.py") if script.is_file())
        current_selection = self.script_combo.currentText()
        self.script_combo.blockSignals(True)
        self.script_combo.clear()
        self.script_combo.addItems(scripts)
        self.script_combo.blockSignals(False)
        if current_selection and current_selection in scripts:
            index = self.script_combo.findText(current_selection)
            if index >= 0:
                self.script_combo.setCurrentIndex(index)
        if scripts:
            self.statusBar().showMessage(f"{len(scripts)} script(s) disponíveis", 3000)
        else:
            self.statusBar().showMessage("Nenhum script encontrado na pasta 'scripts'.", 5000)

    # sourcery skip: extract-method
    def _refresh_browser_windows(self) -> None:
        if not hasattr(self, "browser_window_combo"):
            return

        combo = self.browser_window_combo
        button = getattr(self, "refresh_windows_button", None)

        if focus is None or not hasattr(focus, "list_window_titles"):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Detecção automática indisponível", "")
            self._finalize_combo_state(combo, False)
            if button is not None:
                button.setEnabled(False)
            return

        try:
            titles = focus.list_window_titles()
        except Exception:
            titles = []

        previous_data = combo.currentData()
        previous_text = combo.currentText().strip()
        combo.blockSignals(True)
        combo.clear()
        default_label = "Detectar Microsoft Edge automaticamente"
        combo.addItem(default_label, "")
        for title in titles:
            combo.addItem(title, title)

        preferred = ""
        if isinstance(previous_data, str) and previous_data.strip():
            preferred = previous_data.strip()
        elif previous_text and previous_text != default_label:
            preferred = previous_text
        elif self._default_browser_window_hint:
            preferred = self._default_browser_window_hint

        if preferred:
            index = combo.findData(preferred)
            if index < 0 and preferred:
                combo.addItem(preferred, preferred)
                index = combo.findData(preferred)
            if index >= 0:
                combo.setCurrentIndex(index)
            else:
                combo.setCurrentText(preferred)
        else:
            combo.setCurrentIndex(0)
        self._finalize_combo_state(combo, True)
        if button is not None:
            button.setEnabled(True)

    def _set_running_state(self, running: bool) -> None:
        self.run_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.script_combo.setEnabled(not running)
        self.refresh_scripts_button.setEnabled(not running)
        if hasattr(self, "verify_deps_button"):
            self.verify_deps_button.setEnabled(not running)
        if hasattr(self, "browser_tab_combo"):
            self.browser_tab_combo.setEnabled(not running)
        if hasattr(self, "taskbar_slot_spin"):
            self.taskbar_slot_spin.setEnabled(not running)
        if hasattr(self, "browser_window_combo"):
            allowed = not running and focus is not None and hasattr(focus, "list_window_titles")
            self.browser_window_combo.setEnabled(allowed)
        if hasattr(self, "refresh_windows_button"):
            allowed_btn = not running and focus is not None and hasattr(focus, "list_window_titles")
            self.refresh_windows_button.setEnabled(allowed_btn)

    def _start_new_log_session(self, script_name: str) -> None:
        self._log_buffer.clear()
        self._raw_log_buffer.clear()
        self.log_view.clear()
        self._log_write_failed = False
        sanitized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in script_name).strip("-") or "automacao"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._current_log_path = LOGS_DIR / f"{timestamp}-{sanitized}.log"
        try:
            with open(self._current_log_path, "w", encoding="utf-8") as handle:
                handle.write(f"### Log de execução - {script_name} ###\n")
                handle.write(f"Iniciado em {datetime.now().isoformat()}\n\n")
        except Exception:
            self._log_write_failed = True
            self.statusBar().showMessage("Não foi possível criar o arquivo de log.", 6000)
        self._update_log_buttons(True)

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        raw_entry = f"[{timestamp}] {message}"
        display_entry = self._simplify_log_message(timestamp, message)

        self._raw_log_buffer.append(raw_entry)
        if len(self._raw_log_buffer) > LOG_MAX_LINES:
            self._raw_log_buffer = self._raw_log_buffer[-LOG_MAX_LINES:]

        self._log_buffer.append(display_entry)
        if len(self._log_buffer) > LOG_MAX_LINES:
            self._log_buffer = self._log_buffer[-LOG_MAX_LINES:]

        self.log_view.setPlainText("\n".join(self._log_buffer))
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)
        self.log_view.ensureCursorVisible()

        if not self._current_log_path or self._log_write_failed:
            return
        try:
            with open(self._current_log_path, "a", encoding="utf-8") as handle:
                handle.write(raw_entry + "\n")
        except Exception:
            self._log_write_failed = True
            self.statusBar().showMessage("Falha ao gravar no arquivo de log.", 6000)

    def _simplify_log_message(self, timestamp: str, message: str) -> str:
        text = message.strip()
        if not text:
            return f"{timestamp} •"

        if match := _AUTOMDF_LOG_RE.match(text):
            return self._format_automdf_entry(match)

        if text.startswith("[AutoMDF]"):
            _, _, remainder = text.partition("]")
            if remainder:
                text = remainder.strip()

        return f"{timestamp} • {text}"

    @staticmethod
    def _format_automdf_entry(match: re.Match[str]) -> str:
        level = match.group("level").upper()
        body = match.group("body").strip() or "(sem detalhes)"
        friendly_level = _LEVEL_LABELS.get(level, level.title())
        log_time = match.group("time")
        return f"{log_time} • {friendly_level}: {body}"

    def _update_log_buttons(self, enabled: bool) -> None:
        self.export_log_button.setEnabled(enabled)
        self.open_log_button.setEnabled(enabled)

    @staticmethod
    def _finalize_combo_state(combo: QComboBox, enabled: bool) -> None:
        combo.blockSignals(False)
        combo.setEnabled(enabled)

    def _apply_idle_progress_state(self) -> None:
        self.status_label.setText("Aguardando automação...")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self._automation_active = False
        self._current_script = None
        self._current_log_path = None
        self._log_buffer.clear()
        self._raw_log_buffer.clear()
        self._log_write_failed = False
        self.log_view.clear()
        self._update_log_buttons(False)
        self._current_script_label = ""
        self._progress_overlay.hide_immediately()

    def _refresh_progress(self) -> None:
        data = ProgressManager.read_progress(str(self.progress_file))
        if not data:
            if self._automation_active:
                if self.progress_bar.maximum() != 0:
                    self.progress_bar.setRange(0, 0)
                overlay_label = self._current_script_label or "Automação"
                self._progress_overlay.show_indeterminate(f"{overlay_label} em preparação...")
            else:
                if self.progress_bar.maximum() == 0:
                    self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(0)
                self._progress_overlay.hide_immediately()
            return

        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)

        try:
            percentage = int(data.get("percentage", 0))
        except (TypeError, ValueError):
            percentage = 0
        self.progress_bar.setValue(max(0, min(100, percentage)))

        if self._automation_active:
            overlay_message = (
                str(data.get("current_step", "")).strip()
                or str(data.get("status", "")).strip().title()
                or "Automação em andamento"
            )
            self._progress_overlay.update_progress(percentage, overlay_message)

        status = str(data.get("status", "")).strip().lower()
        step = str(data.get("current_step", "")).strip()
        if status in {"running", "paused"} and step:
            self.status_label.setText(step)
        elif status == "completed":
            self.status_label.setText(step or "Automação concluída.")
            if self._automation_active:
                self._progress_overlay.show_result(True, step or "Automação concluída.")
        elif status == "error":
            self.status_label.setText(step or "Erro na automação.")
            if self._automation_active:
                self._progress_overlay.show_result(False, step or "Erro na automação.")

    @staticmethod
    def _normalize_browser_tab(value: Optional[str]) -> int:
        try:
            tab = int(value) if value is not None else 1
        except (TypeError, ValueError):
            tab = 1
        tab = max(0, tab)
        return min(tab, 9)

    def _selected_browser_tab(self) -> int:
        data = self.browser_tab_combo.currentData() if hasattr(self, "browser_tab_combo") else None
        try:
            if data is None:
                raise TypeError
            return int(data)
        except (TypeError, ValueError):
            return self._default_browser_tab

    def _selected_browser_window_hint(self) -> str:
        if not hasattr(self, "browser_window_combo"):
            return ""
        combo = self.browser_window_combo
        data = combo.currentData()
        if isinstance(data, str) and data.strip():
            return data.strip()
        if combo.isEditable() and (text := combo.currentText().strip()):
            return text
        return ""

    @staticmethod
    def _normalize_taskbar_slot(value: str | int) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return 1
        return max(1, min(9, numeric))

    def _selected_taskbar_slot(self) -> int:
        if hasattr(self, "taskbar_slot_spin"):
            return self.taskbar_slot_spin.value()
        return self._default_taskbar_slot

    @staticmethod
    def _friendly_script_label(script: Path) -> str:
        label = re.sub(r"[_-]+", " ", script.stem).strip()
        return label or script.stem or script.name

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        if self.runner.isRunning():
            answer = QMessageBox.question(
                self,
                "Automação em execução",
                "Há um script em execução. Deseja interromper e sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._on_stop_clicked()
            self.runner.wait(1500)
        ProgressManager.reset(str(self.progress_file))
        self._apply_idle_progress_state()
        self._progress_overlay.close()
        super().closeEvent(event)
