"""Main window for the modern Auto MDF automation control center.

Guia de edição (resumido)
- Modificável pelo usuário:
    - Textos da interface, atalhos e preferências exibidas no painel de configurações.
- Requer atenção:
    - Mudanças em handlers de eventos, threads de UI e manipulação de widgets podem causar travamentos ou perda de estado.
- Apenas para devs:
    - Alterações profundas na arquitetura da janela principal, ciclo de vida do aplicativo e integrações com backend.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from data.automation_settings import AutomationSettings
from data.progress_manager import ProgressManager

from . import dialogs
from .automation_service import AutomationRunConfig, AutomationService
from .progress_overlay import ProgressOverlay
from .progress_watcher import ProgressWatcher
from .ui_components import AutomationSettingsPanel, LogConsole, ProgressPanel
from .log_manager import LogEntry, LogManager
from .constants import (
    LOGS_DIR,
    PROGRESS_REFRESH_INTERVAL_MS,
    SCRIPTS_DIR,
)

try:  # pragma: no cover - optional dependency runtime guard
    from data.automation_focus import focus
except ModuleNotFoundError:  # pragma: no cover
    focus = None  # type: ignore[assignment]


class MainWindow(QMainWindow):
    def __init__(self, python_executable: str) -> None:
        super().__init__()
        self.python_executable = python_executable
        self.setWindowTitle("Auto MDF InvoISys")
        self.resize(900, 580)
        self.setMinimumSize(820, 540)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

        self._default_browser_tab = self._normalize_browser_tab(
            os.environ.get("MDF_BROWSER_TAB", "1")
        )
        os.environ["MDF_BROWSER_TAB"] = str(self._default_browser_tab)
        self._default_browser_window_hint = os.environ.get(
            "MDF_BROWSER_TITLE_HINT", ""
        ).strip()
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
        self._automation_active = False
        self._user_requested_stop = False
        self._current_log_path: Optional[Path] = None
        self._log_actions_enabled = False
        self._log_manager = LogManager(parent=self)
        self._automation_service = AutomationService(python_executable, self)
        self.progress_file = self._automation_service.progress_file
        self._progress_overlay = ProgressOverlay()

        self._progress_watcher = ProgressWatcher(
            self.progress_file,
            interval_ms=PROGRESS_REFRESH_INTERVAL_MS,
            parent=self,
        )
        self._settings_apply_timer = QTimer(self)
        self._settings_apply_timer.setSingleShot(True)
        self._settings_apply_timer.setInterval(350)
        self._settings_apply_timer.timeout.connect(self._commit_pending_settings)
        self._pending_settings: Optional[AutomationSettings] = None

        self._process_check_timer = QTimer(self)
        self._process_check_timer.setInterval(1000)  # Check every second
        self._process_check_timer.timeout.connect(self._check_process_status)

        self._build_ui()
        self._connect_signals()

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

    def _new_row(
        self, parent_layout: QVBoxLayout, label_text: str
    ) -> tuple[QHBoxLayout, QLabel]:
        row = self._create_row(parent_layout)
        label = QLabel(label_text)
        row.addWidget(label)
        return row, label

    @staticmethod
    def _configure_vbox(
        parent: QWidget, *, spacing: int, margins: tuple[int, int, int, int]
    ) -> QVBoxLayout:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)
        return layout

    def _build_ui(self) -> None:
        central = QWidget(self)
        outer_layout = self._configure_vbox(
            central, spacing=12, margins=(18, 18, 18, 18)
        )

        self._tabs = QTabWidget()
        outer_layout.addWidget(self._tabs, stretch=1)

        control_tab = QWidget()
        control_layout = self._configure_vbox(
            control_tab, spacing=12, margins=(0, 0, 0, 0)
        )

        script_row, _ = self._new_row(control_layout, "Script de automação:")

        self.script_combo = QComboBox()
        self.script_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        script_row.addWidget(self.script_combo)

        self.refresh_scripts_button = QPushButton("Atualizar lista")
        script_row.addWidget(self.refresh_scripts_button)

        self.run_button = QPushButton("Iniciar")
        self.stop_button = QPushButton("Parar")
        self.stop_button.setEnabled(False)
        script_row.addWidget(self.run_button)
        script_row.addWidget(self.stop_button)

        self.use_default_tab_checkbox = QCheckBox("Usar aba específica (experimental)")
        self.use_default_tab_checkbox.setChecked(False)
        self.use_default_tab_checkbox.setToolTip(
            "Marque para escolher uma aba específica para iniciar a automação (funcionalidade experimental)."
        )
        control_layout.addWidget(self.use_default_tab_checkbox)

        self.tab_warning_label = QLabel(
            "ATENÇÃO: A seleção manual de aba é experimental e pode causar comportamentos inesperados. Use apenas se souber exatamente o que está fazendo."
        )
        self.tab_warning_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.tab_warning_label.setWordWrap(True)
        self.tab_warning_label.setVisible(False)
        control_layout.addWidget(self.tab_warning_label)

        browser_row, _ = self._new_row(control_layout, "Aba inicial do Microsoft Edge:")

        self.browser_tab_combo = QComboBox()
        self.browser_tab_combo.setToolTip(
            "Escolha a aba que deve receber o foco antes da automação (0 mantém a atual)."
        )
        for tab in range(10):
            text = "0 - manter aba atual" if tab == 0 else f"{tab}"
            self.browser_tab_combo.addItem(text, tab)
        default_index = self.browser_tab_combo.findData(self._default_browser_tab)
        if default_index >= 0:
            self.browser_tab_combo.setCurrentIndex(default_index)
        browser_row.addWidget(self.browser_tab_combo)
        browser_row.addStretch(1)

        self.browser_tab_combo.setEnabled(self.use_default_tab_checkbox.isChecked())

        taskbar_row, _ = self._new_row(
            control_layout, "Posição do Edge na barra de tarefas:"
        )

        self.taskbar_slot_spin = QSpinBox()
        self.taskbar_slot_spin.setRange(1, 9)
        self.taskbar_slot_spin.setValue(self._default_taskbar_slot)
        self.taskbar_slot_spin.setToolTip(
            "Informe a posição do Microsoft Edge fixado na barra de tarefas do Windows (Win+Número)."
        )
        taskbar_row.addWidget(self.taskbar_slot_spin)
        taskbar_row.addStretch(1)

        window_row, _ = self._new_row(control_layout, "Janela do Microsoft Edge:")

        self.browser_window_combo = QComboBox()
        self.browser_window_combo.setEditable(True)
        self.browser_window_combo.setPlaceholderText(
            "Detectar Microsoft Edge automaticamente"
        )
        window_row.addWidget(self.browser_window_combo)

        self.refresh_windows_button = QPushButton("Atualizar janelas")
        window_row.addWidget(self.refresh_windows_button)
        window_row.addStretch(1)

        self.progress_panel = ProgressPanel()
        control_layout.addWidget(self.progress_panel)
        self.status_label = self.progress_panel.status_label
        self.progress_bar = self.progress_panel.progress_bar

        actions_row = self._create_row(control_layout)
        self.verify_deps_button = QPushButton("Verificar dependências")
        actions_row.addWidget(self.verify_deps_button)
        actions_row.addStretch(1)

        control_layout.addStretch(1)
        self._tabs.addTab(control_tab, "Controle")

        self.settings_panel = AutomationSettingsPanel(self._automation_service.settings)
        settings_tab = QWidget()
        settings_layout = self._configure_vbox(
            settings_tab, spacing=12, margins=(0, 0, 0, 0)
        )
        settings_layout.addWidget(self.settings_panel)
        settings_layout.addStretch(1)
        self._tabs.addTab(settings_tab, "Configurações")

        logs_tab = QWidget()
        logs_layout = self._configure_vbox(logs_tab, spacing=0, margins=(0, 0, 0, 0))

        self.log_console = LogConsole()
        self.log_console.set_log_manager(self._log_manager)
        logs_layout.addWidget(self.log_console)
        self._tabs.addTab(logs_tab, "Logs")

        self.setCentralWidget(central)
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

    def _connect_signals(self) -> None:
        self.run_button.clicked.connect(self._on_run_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.refresh_scripts_button.clicked.connect(self._refresh_script_list)
        self.verify_deps_button.clicked.connect(self._on_verify_dependencies)
        self.refresh_windows_button.clicked.connect(self._refresh_browser_windows)
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.log_console.request_export.connect(self._on_export_log)
        self.log_console.request_open.connect(self._on_open_log)

        self._automation_service.log_message.connect(self._on_log_message)
        self._automation_service.bridge_payload.connect(self._on_bridge_payload)
        self._automation_service.automation_started.connect(self._on_process_started)
        self._automation_service.automation_finished.connect(self._on_process_finished)
        self._automation_service.telemetry_event.connect(self._on_telemetry_event)
        self._automation_service.log_pause_request.connect(self._on_log_pause_request)

        self._log_manager.entry_added.connect(self._on_log_entry_added)
        self._log_manager.log_cleared.connect(self._on_log_cleared)
        self._log_manager.session_started.connect(self._on_log_session_started)
        self._log_manager.session_failed.connect(self._on_log_session_failed)

        self._progress_watcher.progress_updated.connect(self._on_progress_snapshot)
        self._progress_watcher.progress_missing.connect(self._on_progress_missing)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_run_clicked(self) -> None:
        script_name = self.script_combo.currentText().strip()
        if not script_name:
            QMessageBox.information(
                self, "Nenhum script", "Selecione um script na lista."
            )
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
        self._default_browser_window_hint = window_hint

        slot_choice = self._selected_taskbar_slot()
        self._default_taskbar_slot = slot_choice

        self._user_requested_stop = False
        if not self._start_new_log_session(script_name):
            return
        config = AutomationRunConfig(
            script_path=script_path,
            tab_index=tab_choice,
            window_hint=window_hint,
            taskbar_slot=slot_choice,
        )

        if not self._automation_service.start(config):
            QMessageBox.warning(
                self,
                "Execução em andamento",
                "Já existe uma automação em execução no momento.",
            )
            self._log_manager.abort_session(delete_file=True)
            self._current_log_path = None
            self._update_log_buttons(False)
            return

        self._current_script = script_path
        self._current_script_label = self._friendly_script_label(script_path)
        self._set_running_state(True)
        self.status_label.setText(f"Executando {script_path.name}...")

    def _on_stop_clicked(self) -> None:
        if not self._automation_service.is_running():
            QMessageBox.information(
                self, "Nenhuma execução", "Nenhum script está em execução."
            )
            return
        self._user_requested_stop = True
        self._automation_service.stop()
        self.status_label.setText("Encerrando script...")
        self._progress_overlay.show_indeterminate("Encerrando automação...")

    def _on_use_default_tab_toggled(self, checked: bool) -> None:
        self.browser_tab_combo.setEnabled(checked)
        self.tab_warning_label.setVisible(checked)

    def _on_export_log(self) -> None:
        raw_lines = self._log_manager.raw_lines
        if not raw_lines:
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
            destination = Path(path)
            if not self._log_manager.export_to(destination):
                QMessageBox.critical(
                    self, "Erro ao exportar", "Falha ao salvar o log selecionado."
                )
                return
        except Exception as exc:
            QMessageBox.critical(
                self, "Erro ao exportar", f"Falha ao salvar o log:\n{exc}"
            )
            return
        self.statusBar().showMessage(f"Log exportado para {path}", 5000)

    def _on_open_log(self) -> None:
        target = self._log_manager.current_file
        if not target or not target.exists():
            QMessageBox.information(
                self, "Log indisponível", "Nenhum arquivo de log disponível."
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            QMessageBox.critical(
                self, "Erro ao abrir log", f"Não foi possível abrir o log:\n{exc}"
            )

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
        self._automation_service.send_bridge_response(response)

    def _on_settings_changed(self, settings: AutomationSettings) -> None:
        self._pending_settings = settings
        self._settings_apply_timer.start()

    def _commit_pending_settings(self) -> None:
        if self._pending_settings is None:
            return
        settings = self._pending_settings
        self._pending_settings = None
        self._automation_service.update_settings(settings)

    def _on_telemetry_event(self, entry: dict) -> None:
        event = str(entry.get("event", "")).lower()
        if event == "focus_failure":
            self.statusBar().showMessage(
                "Falha ao ativar automaticamente o Microsoft Edge. Verifique se a janela está acessível.",
                6000,
            )
        elif event == "focus_retry_failed":
            self.statusBar().showMessage(
                "Não foi possível recuperar o foco do Microsoft Edge após tentativas extras.",
                6000,
            )
        elif event == "settings_updated":
            self.statusBar().showMessage("Configurações de automação aplicadas.", 4000)
        elif event == "settings_persist_failure":
            self.statusBar().showMessage(
                "Não foi possível salvar as configurações (acesso negado). Os ajustes valem apenas para esta sessão.",
                8000,
            )

    def _on_process_started(self, script_path: Path) -> None:
        self._automation_active = True
        self.status_label.setText(f"Executando {script_path.name}...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        overlay_label = self._current_script_label or script_path.stem
        self._progress_overlay.show_indeterminate(f"Executando {overlay_label}...")
        self._update_log_buttons(True)
        self._progress_watcher.start()
        self._process_check_timer.start()

    def _on_process_finished(self, exit_code: int) -> None:
        self._progress_watcher.stop()
        self._process_check_timer.stop()
        self._automation_active = False
        self._set_running_state(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if exit_code == 0 else 0)
        summary = (
            "Execução concluída com sucesso."
            if exit_code == 0
            else f"Execução encerrada (código {exit_code})."
        )
        if self._user_requested_stop and exit_code != 0:
            summary = "Execução interrompida pelo usuário."
        self.status_label.setText(summary)
        if self._user_requested_stop:
            self._progress_overlay.show_result(
                True, "Automação interrompida pelo usuário.", auto_hide_ms=3500
            )
        elif exit_code == 0:
            self._progress_overlay.show_result(
                True, "Automação concluída com sucesso.", auto_hide_ms=3500
            )
        else:
            self._progress_overlay.show_result(
                False, f"Falha na automação (código {exit_code}).", auto_hide_ms=6000
            )
        if exit_code != 0 and not self._user_requested_stop:
            QMessageBox.warning(
                self,
                "Execução finalizada",
                f"O script terminou com código {exit_code}. Consulte o log para detalhes.",
            )
        self._user_requested_stop = False
        self._update_log_buttons(
            bool(self._current_log_path and self._current_log_path.exists())
        )

    def _on_log_pause_request(self, pause: bool) -> None:
        if pause:
            self._log_manager.pause_logging()
        else:
            self._log_manager.resume_logging()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _refresh_script_list(self) -> None:
        scripts = sorted(
            script.name for script in SCRIPTS_DIR.glob("*.py") if script.is_file()
        )
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
            self.statusBar().showMessage(
                "Nenhum script encontrado na pasta 'scripts'.", 5000
            )

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
            allowed = (
                not running
                and focus is not None
                and hasattr(focus, "list_window_titles")
            )
            self.browser_window_combo.setEnabled(allowed)
        if hasattr(self, "refresh_windows_button"):
            allowed_btn = (
                not running
                and focus is not None
                and hasattr(focus, "list_window_titles")
            )
            self.refresh_windows_button.setEnabled(allowed_btn)
        if hasattr(self, "settings_panel"):
            self.settings_panel.setEnabled(not running)

    def _start_new_log_session(self, script_name: str) -> bool:
        path = self._log_manager.start_session(script_name)
        self._current_log_path = path
        self._update_log_buttons(path is not None)
        return path is not None

    def _append_log(self, message: str) -> None:
        self._log_manager.append_line(message)

    def _update_log_buttons(self, enabled: bool | None = None) -> None:
        if not hasattr(self, "log_console"):
            return
        if enabled is not None:
            self._log_actions_enabled = enabled
        allow = self._log_actions_enabled
        has_lines = bool(self._log_manager.raw_lines)
        current_file = self._log_manager.current_file
        has_file = bool(current_file and current_file.exists())
        self.log_console.export_button.setEnabled(allow and has_lines)
        self.log_console.open_button.setEnabled(allow and has_file)

    def _on_log_entry_added(self, _entry: LogEntry) -> None:
        self._update_log_buttons()

    def _on_log_cleared(self) -> None:
        self._update_log_buttons()

    def _on_log_session_started(self, path: Path) -> None:
        self._current_log_path = path
        self._log_actions_enabled = True
        self._update_log_buttons()
        self.statusBar().showMessage(f"Escrevendo log em {path.name}", 4000)

    def _on_log_session_failed(self, message: str) -> None:
        self.statusBar().showMessage(message, 6000)
        current_file = self._log_manager.current_file
        if current_file is None or not current_file.exists():
            self._current_log_path = None
            self._update_log_buttons(False)
        else:
            self._update_log_buttons()

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
        self._log_actions_enabled = False
        self._log_manager.clear_memory()
        self._update_log_buttons(False)
        self._current_script_label = ""
        self._progress_overlay.hide_immediately()
        self._progress_watcher.stop()

    def _on_progress_missing(self) -> None:
        if self._automation_active:
            if self.progress_bar.maximum() != 0:
                self.progress_bar.setRange(0, 0)
            overlay_label = self._current_script_label or "Automação"
            self._progress_overlay.show_indeterminate(
                f"{overlay_label} em preparação..."
            )
        else:
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self._progress_overlay.hide_immediately()

    def _on_progress_snapshot(self, data: dict) -> None:
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)

        try:
            percentage = int(data.get("percentage", 0))
        except (TypeError, ValueError):
            percentage = 0
        self.progress_bar.setValue(max(0, min(100, percentage)))

        status = str(data.get("status", "")).strip().lower()
        step = str(data.get("current_step", "")).strip()

        if self._automation_active or status == "running":
            overlay_message = (
                str(data.get("current_step", "")).strip()
                or str(data.get("status", "")).strip().title()
                or "Automação em andamento"
            )
            estimated_time = data.get("estimated_time_remaining")
            if estimated_time and estimated_time > 0:
                minutes = estimated_time // 60
                seconds = estimated_time % 60
                time_str = f"{minutes}:{seconds:02d}" if minutes > 0 else f"{seconds}s"
                overlay_message += f"\nTempo restante: ~{time_str}"
            self._progress_overlay.update_progress(percentage, overlay_message)

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

        # Verificar se o processo terminou sem emitir sinal de finalização
        if self._automation_active and not self._automation_service.is_running():
            exit_code = 1 if status == "error" else 0
            self._on_process_finished(exit_code)

    def _check_process_status(self) -> None:
        """Verifica periodicamente se o processo de automação ainda está rodando."""
        if self._automation_active and not self._automation_service.is_running():
            self._on_process_finished(1)  # Assume erro se não detectado de outra forma

    @staticmethod
    def _normalize_browser_tab(value: Optional[str]) -> int:
        try:
            tab = int(value) if value is not None else 1
        except (TypeError, ValueError):
            tab = 1
        tab = max(0, tab)
        return min(tab, 9)

    def _selected_browser_tab(self) -> int:
        if not self.use_default_tab_checkbox.isChecked():
            return 1
        data = (
            self.browser_tab_combo.currentData()
            if hasattr(self, "browser_tab_combo")
            else None
        )
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
        if self._automation_service.is_running():
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
            self._automation_service.wait(1500)
        ProgressManager.reset(str(self.progress_file))
        self._apply_idle_progress_state()
        self._progress_overlay.close()
        # Ensure log manager flushes buffers and stops writer thread cleanly
        try:
            if hasattr(self, "_log_manager") and self._log_manager is not None:
                self._log_manager.shutdown()
        except Exception:
            pass
        super().closeEvent(event)
