"""Main window for the modern Auto MDF automation control center."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
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
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from data.progress_manager import ProgressManager

from . import dialogs
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

        self._current_script: Optional[Path] = None
        self._current_log_path: Optional[Path] = None
        self._log_buffer: list[str] = []
        self._log_write_failed = False
        self._automation_active = False
        self._user_requested_stop = False
        self.progress_file = Path(ProgressManager.DEFAULT_FILE_PATH)

        self.runner = ScriptRunner(python_executable, self)

        self._build_ui()
        self._connect_signals()

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(PROGRESS_REFRESH_INTERVAL_MS)
        self._progress_timer.timeout.connect(self._refresh_progress)
        self._progress_timer.start()

        self._refresh_script_list()
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

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        script_row = self._create_row(layout)

        script_label = QLabel("Script de automação:")
        script_row.addWidget(script_label)

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

        browser_row = self._create_row(layout)

        browser_label = QLabel("Aba inicial do navegador:")
        browser_row.addWidget(browser_label)

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

        status_row = self._create_row(layout)

        self.status_label = QLabel("Aguardando automação...")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_label, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
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

        self._user_requested_stop = False
        self._start_new_log_session(script_name)

        if focus is not None:
            with contextlib.suppress(Exception):
                focus.target_tab = tab_choice

        ProgressManager.reset(str(self.progress_file))

        if not self.runner.start_script(script_path, progress_file=self.progress_file):
            QMessageBox.warning(
                self,
                "Execução em andamento",
                "Já existe uma automação em execução no momento.",
            )
            return

        self._current_script = script_path
        self._apply_idle_progress_state()
        self._set_running_state(True)
        self.status_label.setText(f"Executando {script_path.name}...")

    def _on_stop_clicked(self) -> None:
        if not self.runner.isRunning():
            QMessageBox.information(self, "Nenhuma execução", "Nenhum script está em execução.")
            return
        self._user_requested_stop = True
        self.runner.stop_script()
        self.status_label.setText("Encerrando script...")

    def _on_export_log(self) -> None:
        if not self._log_buffer:
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
                handle.write("\n".join(self._log_buffer) + "\n")
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
        self.progress_bar.setValue(0)
        self._update_log_buttons(True)

    def _on_process_finished(self, exit_code: int) -> None:
        self._automation_active = False
        self._set_running_state(False)
        summary = "Execução concluída com sucesso." if exit_code == 0 else f"Execução encerrada (código {exit_code})."
        if self._user_requested_stop and exit_code != 0:
            summary = "Execução interrompida pelo usuário."
        self.status_label.setText(summary)
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

    def _set_running_state(self, running: bool) -> None:
        self.run_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.script_combo.setEnabled(not running)
        self.refresh_scripts_button.setEnabled(not running)
        if hasattr(self, "verify_deps_button"):
            self.verify_deps_button.setEnabled(not running)
        if hasattr(self, "browser_tab_combo"):
            self.browser_tab_combo.setEnabled(not running)

    def _start_new_log_session(self, script_name: str) -> None:
        self._log_buffer.clear()
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
        entry = f"[{timestamp}] {message}"
        self._log_buffer.append(entry)
        if len(self._log_buffer) > LOG_MAX_LINES:
            self._log_buffer = self._log_buffer[-LOG_MAX_LINES:]
        self.log_view.setPlainText("\n".join(self._log_buffer))
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)
        self.log_view.ensureCursorVisible()

        if not self._current_log_path or self._log_write_failed:
            return
        try:
            with open(self._current_log_path, "a", encoding="utf-8") as handle:
                handle.write(entry + "\n")
        except Exception:
            self._log_write_failed = True
            self.statusBar().showMessage("Falha ao gravar no arquivo de log.", 6000)

    def _update_log_buttons(self, enabled: bool) -> None:
        self.export_log_button.setEnabled(enabled)
        self.open_log_button.setEnabled(enabled)

    def _apply_idle_progress_state(self) -> None:
        if not self._automation_active and not self.runner.isRunning():
            self.status_label.setText("Aguardando automação...")
            self.progress_bar.setValue(0)

    def _refresh_progress(self) -> None:
        data = ProgressManager.read_progress(str(self.progress_file))
        if not data:
            if not self._automation_active:
                self.progress_bar.setValue(0)
            return

        try:
            percentage = int(data.get("percentage", 0))
        except (TypeError, ValueError):
            percentage = 0
        self.progress_bar.setValue(max(0, min(100, percentage)))

        status = str(data.get("status", "")).strip().lower()
        step = str(data.get("current_step", "")).strip()
        if status in {"running", "paused"} and step:
            self.status_label.setText(step)
        elif status == "completed":
            self.status_label.setText(step or "Automação concluída.")
        elif status == "error":
            self.status_label.setText(step or "Erro na automação.")

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

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------
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
        super().closeEvent(event)