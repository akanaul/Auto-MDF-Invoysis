"""Componentes reutilizáveis de UI para o centro de controle do Auto MDF.

Guia de edição (resumido)
- Modificável pelo usuário:
    - Pequenas adaptações visuais, temas e estilização leve.
- Requer atenção:
    - Mudanças que alterem contratos de sinal/slot ou APIs de componentes podem quebrar consumidores.
- Apenas para devs:
    - Reescrever componentes para suportar novos padrões ou dependências externas.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Optional, Sequence, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from data.automation_settings import AutomationSettings
from .constants import LOG_MAX_LINES

if TYPE_CHECKING:
    from .log_manager import LogEntry, LogManager


class AutomationLogView(QPlainTextEdit):
    """Visualizador de logs somente leitura com formatação por nível."""

    # Seguro ajustar: fontes, cores e comportamento de seguir o final.
    # Requer atenção: ajustar o limite máximo de blocos — considere o impacto em memória.
    # Apenas para devs: alterar a lógica de renderização/append; mantenha alinhado ao LogEntry.

    _LEVEL_COLORS = {
        "DEBUG": QColor("#7f8c8d"),
        "INFO": QColor("#d5d8dc"),
        "WARNING": QColor("#f5b041"),
        "ERROR": QColor("#ec7063"),
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = self.font()
        font.setFamily("Consolas")
        font.setFixedPitch(True)
        self.setFont(font)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setMaximumBlockCount(LOG_MAX_LINES)

    def render_entries(self, entries: Sequence["LogEntry"]) -> None:
        self.setUpdatesEnabled(False)
        try:
            self.clear()
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            for entry in entries:
                self._write_entry(cursor, entry)
            self.setTextCursor(cursor)
        finally:
            self.setUpdatesEnabled(True)

    def append_entry(self, entry: "LogEntry", *, follow: bool = True) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._write_entry(cursor, entry)
        if follow:
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    def _write_entry(self, cursor: QTextCursor, entry: "LogEntry") -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(self._LEVEL_COLORS.get(entry.level, QColor("#d5d8dc")))
        cursor.setCharFormat(fmt)
        cursor.insertText(entry.display + "\n")
        cursor.setCharFormat(QTextCharFormat())


class ProgressPanel(QWidget):
    """Widget composto com rótulo de status e barra de progresso."""

    # Seguro ajustar: texto do rótulo, formato da barra de progresso e espaçamentos.
    # Requer atenção: pressupostos de faixa/valor — a UI espera 0-100.
    # Apenas para devs: substituir a barra por outros widgets (afeta expectativas da MainWindow).

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.status_label = QLabel("Aguardando automação...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.progress_bar.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self.progress_bar.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.progress_bar)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_indeterminate(self) -> None:
        self.progress_bar.setRange(0, 0)

    def set_determinate(self) -> None:
        self.progress_bar.setRange(0, 100)

    def set_value(self, value: int) -> None:
        self.progress_bar.setValue(max(0, min(100, value)))


class LogConsole(QWidget):
    """Console dedicado de logs com filtros e ações contextuais."""

    # Seguro ajustar: layout, rótulos dos botões e textos de placeholder.
    # Requer atenção: lógica de filtragem e emissão de sinais — garanta compatibilidade com o LogManager.
    # Apenas para devs: alterar como as entradas são armazenadas/aplicadas; outros módulos dependem de set_log_manager.

    request_export = Signal()
    request_open = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._manager: Optional["LogManager"] = None
        self._entries: list["LogEntry"] = []
        self._search_term = ""
        self._follow_tail = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        layout.addLayout(controls)

        controls.addWidget(QLabel("Nível:"))
        self.level_combo = QComboBox()
        self.level_combo.addItem("Todos", "ALL")
        self.level_combo.addItem("Informações", "INFO")
        self.level_combo.addItem("Avisos", "WARNING")
        self.level_combo.addItem("Erros", "ERROR")
        self.level_combo.addItem("Depuração", "DEBUG")
        controls.addWidget(self.level_combo)

        controls.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtrar por texto")
        controls.addWidget(self.search_edit, stretch=1)

        self.follow_checkbox = QCheckBox("Acompanhar final")
        self.follow_checkbox.setChecked(True)
        controls.addWidget(self.follow_checkbox)

        self.clear_button = QPushButton("Limpar memória")
        controls.addWidget(self.clear_button)

        self.export_button = QPushButton("Exportar…")
        controls.addWidget(self.export_button)

        self.open_button = QPushButton("Abrir arquivo")
        controls.addWidget(self.open_button)

        layout.addLayout(controls)

        self.status_label = QLabel("Aguardando primeira execução.")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(self.status_label)

        self.log_view = AutomationLogView()
        layout.addWidget(self.log_view, stretch=1)

        self.level_combo.currentIndexChanged.connect(self._apply_filters)
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.follow_checkbox.toggled.connect(self._on_follow_toggled)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.export_button.clicked.connect(lambda: self.request_export.emit())
        self.open_button.clicked.connect(lambda: self.request_open.emit())

    def set_log_manager(self, manager: "LogManager") -> None:
        if manager is self._manager:
            return
        if self._manager is not None:
            self._disconnect_manager()
        self._manager = manager
        self._entries = manager.entries
        manager.entry_added.connect(self._on_entry_added)
        manager.log_cleared.connect(self._on_log_cleared)
        manager.session_started.connect(self._on_session_started)
        manager.session_failed.connect(self._on_session_failed)
        self._apply_filters()
        self._update_status(manager.current_file)

    def _disconnect_manager(self) -> None:
        assert self._manager is not None
        with contextlib.suppress(TypeError):
            self._manager.entry_added.disconnect(self._on_entry_added)
            self._manager.log_cleared.disconnect(self._on_log_cleared)
            self._manager.session_started.disconnect(self._on_session_started)
            self._manager.session_failed.disconnect(self._on_session_failed)

    def _on_entry_added(self, entry: "LogEntry") -> None:
        self._entries.append(entry)
        if self._entry_matches(entry):
            self.log_view.append_entry(entry, follow=self._follow_tail)

    def _on_log_cleared(self) -> None:
        self._entries = []
        self.log_view.clear()

    def _on_session_started(self, path: Path) -> None:
        self._set_status(f"Escrevendo em {path.name}")
        self._apply_filters()

    def _on_session_failed(self, message: str) -> None:
        self._set_status(message, error=True)

    def _on_search_changed(self, text: str) -> None:
        self._search_term = text.strip().lower()
        self._apply_filters()

    def _on_follow_toggled(self, checked: bool) -> None:
        self._follow_tail = checked

    def _on_clear_clicked(self) -> None:
        if self._manager is not None:
            self._manager.clear_memory()
        else:
            self.log_view.clear()
        self._entries = []

    def _apply_filters(self) -> None:
        filtered = [entry for entry in self._entries if self._entry_matches(entry)]
        self.log_view.render_entries(filtered)
        if self._follow_tail:
            self.log_view.moveCursor(QTextCursor.MoveOperation.End)
            self.log_view.ensureCursorVisible()

    def _entry_matches(self, entry: "LogEntry") -> bool:
        selected_level = self.level_combo.currentData()
        level_matches = selected_level == "ALL" or entry.level.upper() == selected_level
        search_matches = (
            not self._search_term or self._search_term in entry.display.lower()
        )
        return level_matches and search_matches

    def _set_status(self, message: str, *, error: bool = False) -> None:
        color = "#ec7063" if error else "#7f8c8d"
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.status_label.setText(message)

    def _update_status(self, path: Optional[Path]) -> None:
        if path is None:
            self._set_status("Aguardando primeira execução.")
        else:
            self._set_status(f"Escrevendo em {path.name}")


class AutomationSettingsPanel(QGroupBox):
    """Exibe ajustes de tempo de execução para a stack de automação."""

    # Seguro ajustar: rótulos, tooltips, faixas das spin boxes e estado padrão do checkbox.
    # Requer atenção: ligações de sinais e a estrutura de `apply_settings/current_settings`.
    # Apenas para devs: adicionar novas abas ou campos de persistência — mantenha alinhado ao AutomationSettings.

    settings_changed = Signal(object)

    def __init__(
        self, settings: AutomationSettings, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__("Configuração de automação", parent)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(8)

        self._tabs = QTabWidget()
        outer_layout.addWidget(self._tabs)

        self._timer_groups: list[QWidget] = []

        self._setup_general_tab()
        self._setup_timers_tab()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._pause_spin.valueChanged.connect(self._notify_change)
        self._retry_spin.valueChanged.connect(self._notify_change)
        self._retry_timeout.valueChanged.connect(self._notify_change)
        self._min_sleep_spin.valueChanged.connect(self._notify_change)
        self._short_scale_spin.valueChanged.connect(self._notify_change)
        self._medium_scale_spin.valueChanged.connect(self._notify_change)
        self._long_scale_spin.valueChanged.connect(self._notify_change)
        self._short_threshold_spin.valueChanged.connect(self._handle_threshold_change)
        self._medium_threshold_spin.valueChanged.connect(self._handle_threshold_change)
        self._use_default_timers_checkbox.toggled.connect(
            self._on_use_default_timers_toggled
        )

        self.apply_settings(settings)
        self._update_timer_hints()

    def apply_settings(self, settings: AutomationSettings) -> None:
        self.blockSignals(True)
        self._pause_spin.setValue(float(settings.pyautogui_pause))
        self._retry_spin.setValue(int(settings.focus_retry_attempts))
        self._retry_timeout.setValue(float(settings.focus_retry_seconds))
        self._min_sleep_spin.setValue(float(settings.pyautogui_minimum_sleep))
        self._short_threshold_spin.setValue(float(settings.sleep_threshold_short))
        self._medium_threshold_spin.setValue(float(settings.sleep_threshold_medium))
        self._short_scale_spin.setValue(float(settings.sleep_scale_short))
        self._medium_scale_spin.setValue(float(settings.sleep_scale_medium))
        self._long_scale_spin.setValue(float(settings.sleep_scale_long))
        self._use_default_timers_checkbox.blockSignals(True)
        self._use_default_timers_checkbox.setChecked(bool(settings.use_default_timers))
        self._use_default_timers_checkbox.blockSignals(False)
        self._apply_timer_override_state(bool(settings.use_default_timers))
        self._enforce_threshold_constraints()
        self._update_timer_hints()
        self.blockSignals(False)

    def current_settings(self) -> AutomationSettings:
        return AutomationSettings(
            pyautogui_pause=float(self._pause_spin.value()),
            pyautogui_failsafe=True,
            focus_retry_seconds=float(self._retry_timeout.value()),
            focus_retry_attempts=int(self._retry_spin.value()),
            pyautogui_minimum_sleep=float(self._min_sleep_spin.value()),
            sleep_threshold_short=float(self._short_threshold_spin.value()),
            sleep_threshold_medium=float(self._medium_threshold_spin.value()),
            sleep_scale_short=float(self._short_scale_spin.value()),
            sleep_scale_medium=float(self._medium_scale_spin.value()),
            sleep_scale_long=float(self._long_scale_spin.value()),
            use_default_timers=self._use_default_timers_checkbox.isChecked(),
        )

    def _notify_change(self, _value: object) -> None:
        self._update_timer_hints()
        self.settings_changed.emit(self.current_settings())

    def _handle_threshold_change(self, _value: float) -> None:
        self._enforce_threshold_constraints()
        self._notify_change(_value)

    def _enforce_threshold_constraints(self) -> None:
        short_value = float(self._short_threshold_spin.value())
        medium_value = float(self._medium_threshold_spin.value())
        min_medium = short_value + 0.01
        self._medium_threshold_spin.blockSignals(True)
        self._medium_threshold_spin.setMinimum(min_medium)
        if medium_value < min_medium:
            self._medium_threshold_spin.setValue(min_medium)
        self._medium_threshold_spin.blockSignals(False)

    def _setup_general_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        header = QLabel(
            "Ajuste como o serviço recupera o foco do Microsoft Edge. "
            "Essas opções afetam toda automação e não exigem reinício."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        self._retry_spin = QSpinBox()
        self._retry_spin.setRange(0, 10)
        self._retry_spin.setSingleStep(1)
        self._retry_spin.setToolTip(
            "Número extra de tentativas caso o Edge não seja trazido para frente na primeira chamada."
        )

        self._retry_timeout = QDoubleSpinBox()
        self._retry_timeout.setDecimals(1)
        self._retry_timeout.setRange(0.5, 30.0)
        self._retry_timeout.setSingleStep(0.5)
        self._retry_timeout.setSuffix(" s")
        self._retry_timeout.setToolTip(
            "Intervalo entre cada tentativa adicional ao recuperar o foco do Edge."
        )

        layout.addLayout(
            self._make_row("Tentativas extras para recuperar o Edge:", self._retry_spin)
        )
        layout.addLayout(
            self._make_row("Intervalo entre tentativas extras:", self._retry_timeout)
        )

        self._failsafe_hint = QLabel(
            "Failsafe do PyAutoGUI sempre ativo: mova o mouse para o canto superior esquerdo para abortar com segurança."
        )
        self._failsafe_hint.setWordWrap(True)
        self._failsafe_hint.setStyleSheet("color: #d35400; font-weight: bold;")
        layout.addWidget(self._failsafe_hint)

        layout.addStretch(1)

        self._tabs.addTab(tab, "Geral")

    def _setup_timers_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(10)

        self._use_default_timers_checkbox = QCheckBox(
            "Usar tempos padrão do script (recomendado)"
        )
        self._use_default_timers_checkbox.setChecked(True)
        self._use_default_timers_checkbox.setToolTip(
            "Mantém os tempos originais definidos pelos scripts. Desmarque apenas se precisar ajustar manualmente."
        )
        inner_layout.addWidget(self._use_default_timers_checkbox)

        self._timer_warning_label = QLabel(
            "ATENÇÃO: Desmarque esta opção apenas se os tempos padrão do script não funcionarem ou se você souber "
            "exatamente o que está fazendo. Ajustes incorretos podem travar a automação."
        )
        self._timer_warning_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self._timer_warning_label.setWordWrap(True)
        self._timer_warning_label.setVisible(False)
        inner_layout.addWidget(self._timer_warning_label)

        description = QLabel(
            "Ajuste quanto tempo o Auto MDF espera entre as ações. Valores menores aceleram a automação; "
            "valores maiores dão mais tempo para as telas responderem."
        )
        description.setWordWrap(True)
        inner_layout.addWidget(description)

        self._pause_spin = QDoubleSpinBox()
        self._pause_spin.setDecimals(2)
        self._pause_spin.setRange(0.0, 5.0)
        self._pause_spin.setSingleStep(0.1)
        self._pause_spin.setSuffix(" s")
        self._pause_spin.setToolTip(
            "Intervalo global aplicado pelo PyAutoGUI após cada clique ou tecla enviada pelos scripts."
        )

        self._min_sleep_spin = QDoubleSpinBox()
        self._min_sleep_spin.setDecimals(3)
        self._min_sleep_spin.setRange(0.0, 0.5)
        self._min_sleep_spin.setSingleStep(0.01)
        self._min_sleep_spin.setSuffix(" s")
        self._min_sleep_spin.setToolTip(
            "Tempo mínimo utilizado internamente pelo PyAutoGUI para pausas embutidas em funções como write()."
        )

        self._short_threshold_spin = QDoubleSpinBox()
        self._short_threshold_spin.setDecimals(2)
        self._short_threshold_spin.setRange(0.05, 2.0)
        self._short_threshold_spin.setSingleStep(0.05)
        self._short_threshold_spin.setSuffix(" s")
        self._short_threshold_spin.setToolTip(
            "Espera de até este tempo usa o ajuste de esperas rápidas. Bom para digitação e cliques simples."
        )

        self._medium_threshold_spin = QDoubleSpinBox()
        self._medium_threshold_spin.setDecimals(2)
        self._medium_threshold_spin.setRange(0.1, 5.0)
        self._medium_threshold_spin.setSingleStep(0.1)
        self._medium_threshold_spin.setSuffix(" s")
        self._medium_threshold_spin.setToolTip(
            "Espera acima do tempo rápido e até aqui usa o ajuste intermediário (mudança de abas, animações curtas)."
        )

        self._short_scale_spin = QDoubleSpinBox()
        self._short_scale_spin.setDecimals(2)
        self._short_scale_spin.setRange(0.1, 5.0)
        self._short_scale_spin.setSingleStep(0.1)
        self._short_scale_spin.setToolTip(
            "Fator aplicado às esperas rápidas. 1.0 mantém o tempo original, 2.0 dobra, 0.5 reduz pela metade."
        )

        self._medium_scale_spin = QDoubleSpinBox()
        self._medium_scale_spin.setDecimals(2)
        self._medium_scale_spin.setRange(0.1, 5.0)
        self._medium_scale_spin.setSingleStep(0.1)
        self._medium_scale_spin.setToolTip(
            "Fator aplicado às esperas intermediárias. Use para ajustar trocas de abas e pequenas animações."
        )

        self._long_scale_spin = QDoubleSpinBox()
        self._long_scale_spin.setDecimals(2)
        self._long_scale_spin.setRange(0.1, 5.0)
        self._long_scale_spin.setSingleStep(0.1)
        self._long_scale_spin.setToolTip(
            "Fator aplicado às esperas longas. Qualquer espera acima do limite intermediário usa este ajuste."
        )

        global_group = QGroupBox("Pausas globais do PyAutoGUI")
        global_layout = QGridLayout(global_group)
        global_layout.setContentsMargins(8, 8, 8, 8)
        global_layout.setHorizontalSpacing(12)
        global_layout.setVerticalSpacing(6)

        global_layout.addWidget(QLabel("Pausa padrão após cada ação:"), 0, 0)
        global_layout.addWidget(self._pause_spin, 0, 1)
        self._pause_hint = QLabel(
            "Aplica-se a cliques, digitações e atalhos enviados pelos scripts."
        )
        self._pause_hint.setStyleSheet("color: #566573; font-size: 11px;")
        self._pause_hint.setWordWrap(True)
        global_layout.addWidget(self._pause_hint, 1, 0, 1, 2)

        global_layout.addWidget(QLabel("Tempo mínimo interno do PyAutoGUI:"), 2, 0)
        global_layout.addWidget(self._min_sleep_spin, 2, 1)
        self._min_sleep_hint = QLabel(
            "Micropausas usadas dentro de funções como `write()` e `hotkey()`. Ajuste apenas se necessário."
        )
        self._min_sleep_hint.setStyleSheet("color: #566573; font-size: 11px;")
        self._min_sleep_hint.setWordWrap(True)
        global_layout.addWidget(self._min_sleep_hint, 3, 0, 1, 2)

        global_layout.setColumnStretch(0, 1)
        global_layout.setColumnStretch(1, 0)
        inner_layout.addWidget(global_group)

        timing_group = QGroupBox("Multiplicadores conforme duração do sleep")
        timing_layout = QGridLayout(timing_group)
        timing_layout.setContentsMargins(8, 8, 8, 8)
        timing_layout.setHorizontalSpacing(12)
        timing_layout.setVerticalSpacing(6)
        timing_layout.setColumnStretch(0, 1)
        timing_layout.setColumnStretch(1, 0)
        timing_layout.setColumnStretch(2, 1)
        timing_layout.setColumnStretch(3, 0)

        timing_layout.addWidget(QLabel("Até (curto):"), 0, 0)
        timing_layout.addWidget(self._short_threshold_spin, 0, 1)
        timing_layout.addWidget(QLabel("Multiplicador curto:"), 0, 2)
        timing_layout.addWidget(self._short_scale_spin, 0, 3)
        self._short_hint = QLabel()
        self._short_hint.setStyleSheet("color: #566573; font-size: 11px;")
        self._short_hint.setWordWrap(True)
        timing_layout.addWidget(self._short_hint, 1, 0, 1, 4)

        timing_layout.addWidget(QLabel("Até (médio):"), 2, 0)
        timing_layout.addWidget(self._medium_threshold_spin, 2, 1)
        timing_layout.addWidget(QLabel("Multiplicador médio:"), 2, 2)
        timing_layout.addWidget(self._medium_scale_spin, 2, 3)
        self._medium_hint = QLabel()
        self._medium_hint.setStyleSheet("color: #566573; font-size: 11px;")
        self._medium_hint.setWordWrap(True)
        timing_layout.addWidget(self._medium_hint, 3, 0, 1, 4)

        long_row = QHBoxLayout()
        long_label = QLabel(
            "Ajuste para esperas longas (acima do limite intermediário):"
        )
        long_label.setWordWrap(True)
        long_row.addWidget(long_label)
        long_row.addWidget(self._long_scale_spin)
        long_row.addStretch(1)
        timing_layout.addLayout(long_row, 4, 0, 1, 4)
        self._long_hint = QLabel()
        self._long_hint.setStyleSheet("color: #566573; font-size: 11px;")
        self._long_hint.setWordWrap(True)
        timing_layout.addWidget(self._long_hint, 5, 0, 1, 4)

        inner_layout.addWidget(timing_group)
        self._timer_groups = [global_group, timing_group]
        inner_layout.addStretch(1)

        self._apply_timer_override_state(True)
        self._tabs.addTab(tab, "Temporizadores")

    def _make_row(self, label_text: str, widget: QWidget) -> QHBoxLayout:
        """Monta uma linha horizontal rotulada para o formulário de ajustes."""
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setWordWrap(True)
        row.addWidget(label)
        row.addWidget(widget)
        row.addStretch(1)
        return row

    def _apply_timer_override_state(self, use_defaults: bool) -> None:
        """Trava os controles de temporizadores quando os padrões de script estão ativos."""
        for widget in self._timer_groups:
            widget.setEnabled(not use_defaults)
        self._timer_warning_label.setVisible(not use_defaults)

    def _on_use_default_timers_toggled(self, checked: bool) -> None:
        """Sincroniza o checkbox com a UI e emite as configurações atualizadas."""
        self._apply_timer_override_state(checked)
        self._update_timer_hints()
        self.settings_changed.emit(self.current_settings())

    def _update_timer_hints(self) -> None:
        """Renova os textos de ajuda para refletir limites e multiplicadores."""
        short_threshold = float(self._short_threshold_spin.value())
        medium_threshold = float(self._medium_threshold_spin.value())
        short_scale = float(self._short_scale_spin.value())
        medium_scale = float(self._medium_scale_spin.value())
        long_scale = float(self._long_scale_spin.value())

        self._short_hint.setText(
            (
                f"Para esperas de até {short_threshold:.2f}s (digitação, cliques rápidos). O tempo original é multiplicado "
                f"por {short_scale:.2f}x."
            )
        )
        self._medium_hint.setText(
            (
                f"Para esperas entre {short_threshold:.2f}s e {medium_threshold:.2f}s (troca de abas, pequenas animações). "
                f"Multiplicador aplicado: {medium_scale:.2f}x."
            )
        )
        self._long_hint.setText(
            (
                f"Para qualquer espera acima de {medium_threshold:.2f}s (carregamentos maiores, downloads). "
                f"Essas esperas usam automaticamente {long_scale:.2f}x."
            )
        )
