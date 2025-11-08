"""Utilitários de diálogo para lidar com interações de bridge na Qt GUI.

Guia de edição (resumido)
- Modificável pelo usuário:
    - Textos exibidos para o usuário e ajustes leves de layout.
- Requer atenção:
    - Mudanças na lógica de temporização e feedback do bridge podem travar fluxos críticos.
- Apenas para devs:
    - Alterações profundas na integração com `DialogService` ou com controles de foco.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .constants import BRIDGE_ACK, BRIDGE_CANCEL
from data.dialog_service import DialogService

try:  # Import lazily to avoid hard failures when GUI dependencies are missing.
    from data.automation_focus import focus
except ModuleNotFoundError:  # pragma: no cover
    focus = None  # type: ignore[assignment]


def _active_parent() -> Optional[QWidget]:
    """Retorna uma janela Qt ativa para servir como parent, se existir."""

    window = QApplication.activeWindow()
    if window is not None:
        return window
    app = QApplication.instance()
    if app is None:
        return None
    stored = app.property("auto_mdf_main_window")
    return stored if isinstance(stored, QWidget) else None


_GUI_DIALOG_SERVICE = DialogService(
    parent_provider=_active_parent, bridge_enabled=False
)


def _restore_browser_focus(preserve_tab: bool = True) -> None:
    if focus is None:
        return
    focus.prepare_taskbar_retry()
    time.sleep(0.05)
    for _ in range(9):
        with suppress(Exception):  # pragma: no cover - best-effort only
            if preserve_tab:
                success = focus.ensure_browser_focus_preserve_tab(allow_taskbar=True)
                force_tab = False
            else:
                success = focus.ensure_browser_focus(allow_taskbar=True)
                force_tab = True
            if success:
                focus.wait_until_browser_active(force_tab=force_tab)
                return
        time.sleep(0.2)


def _activate_dialog(widget: QWidget) -> None:
    widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    widget.setWindowState(widget.windowState() & ~Qt.WindowState.WindowMinimized)
    widget.show()
    widget.raise_()
    widget.activateWindow()
    widget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
    handle = widget.windowHandle()
    if handle is not None:
        handle.requestActivate()
    if QApplication.instance() is not None:
        QApplication.setActiveWindow(widget)


def _text_or_default(raw: Any, fallback: str) -> str:
    text = fallback if raw is None else str(raw)
    return text or fallback


def _exec_modal(widget: QDialog) -> int:
    widget.setWindowModality(Qt.WindowModality.ApplicationModal)
    QTimer.singleShot(0, lambda: _activate_dialog(widget))
    return widget.exec()


def show_alert(parent: QWidget, *, title: str, text: str, button: str) -> str:
    message_box = QMessageBox(parent)
    message_box.setIcon(QMessageBox.Icon.Information)
    message_box.setWindowTitle(title or "Informação")
    message_box.setText(text or "")
    message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    ok_button = message_box.button(QMessageBox.StandardButton.Ok)
    if ok_button is not None:
        ok_button.setText(button or "OK")
    message_box.setDefaultButton(QMessageBox.StandardButton.Ok)
    _exec_modal(message_box)
    _restore_browser_focus(preserve_tab=True)
    return BRIDGE_ACK


def show_prompt(
    parent: QWidget,
    *,
    title: str,
    text: str,
    default: str,
    require_input: bool = False,
    allow_cancel: bool = True,
    cancel_message: str = "",
) -> Optional[str]:
    cancel_message = (cancel_message or "").strip()

    result: dict[str, Optional[str]] = {"value": None}

    class _PromptDialog(QDialog):
        def __init__(self) -> None:
            super().__init__(parent)
            self._allow_cancel = allow_cancel
            self._cancel_message = cancel_message
            if not self._allow_cancel:
                self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        def reject(self) -> None:  # type: ignore[override]
            if not self._allow_cancel:
                return
            if self._cancel_message:
                answer = QMessageBox.question(
                    self,
                    "Cancelar entrada",
                    self._cancel_message,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            result["value"] = None
            super().reject()

    dialog = _PromptDialog()
    dialog.setWindowTitle(title or "Entrada")

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 16, 20, 16)

    label = QLabel(text or "Informe o valor:")
    label.setWordWrap(True)
    layout.addWidget(label)

    from PySide6.QtWidgets import QLineEdit  # Local import to reduce module weight

    line_edit = QLineEdit(dialog)
    line_edit.setText(default or "")
    line_edit.selectAll()
    line_edit.setAutoFillBackground(True)
    layout.addWidget(line_edit)

    validation_label = QLabel("", dialog)
    validation_label.setStyleSheet("color: #d32f2f;")
    validation_label.setWordWrap(True)
    validation_label.setVisible(False)
    layout.addWidget(validation_label)

    button_row = QHBoxLayout()
    layout.addLayout(button_row)

    def accept() -> None:
        value = line_edit.text()
        trimmed = value.strip()
        if require_input and not trimmed:
            validation_label.setText("Informe um valor antes de continuar.")
            validation_label.setVisible(True)
            line_edit.selectAll()
            line_edit.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            return
        validation_label.clear()
        validation_label.setVisible(False)
        result["value"] = value
        dialog.accept()

    if allow_cancel:
        cancel_button = QPushButton("Cancelar", dialog)
        cancel_button.clicked.connect(dialog.reject)
        button_row.addWidget(cancel_button)

    ok_button = QPushButton("OK", dialog)
    ok_button.clicked.connect(accept)
    ok_button.setDefault(True)
    if require_input and not line_edit.text().strip():
        ok_button.setEnabled(False)
    button_row.addWidget(ok_button)
    line_edit.returnPressed.connect(accept)

    def on_text_changed(value: str) -> None:
        trimmed = value.strip()
        if require_input:
            ok_button.setEnabled(bool(trimmed))
        if validation_label.isVisible() and trimmed:
            validation_label.clear()
            validation_label.setVisible(False)

    line_edit.textChanged.connect(on_text_changed)

    dialog.resize(360, dialog.sizeHint().height())
    line_edit.setFocus(Qt.FocusReason.TabFocusReason)
    _exec_modal(dialog)
    _restore_browser_focus(preserve_tab=True)
    value = result["value"]
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def show_confirm(
    parent: QWidget, *, title: str, text: str, buttons: list[str]
) -> Optional[str]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title or "Confirmação")
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 16, 20, 16)

    label = QLabel(text or "Confirma?")
    label.setWordWrap(True)
    layout.addWidget(label)

    button_row = QHBoxLayout()
    layout.addLayout(button_row)

    choice: dict[str, Optional[str]] = {"value": None}

    def make_handler(value: str):
        def handler() -> None:
            choice["value"] = value
            dialog.accept()

        return handler

    for label_text in buttons:
        button = QPushButton(label_text, dialog)
        button.clicked.connect(make_handler(label_text))
        button_row.addWidget(button)

    dialog.resize(340, dialog.sizeHint().height())
    _exec_modal(dialog)
    _restore_browser_focus(preserve_tab=True)
    value = choice["value"]
    trimmed = value.strip() if value else ""
    return trimmed or None


def handle_bridge_payload(parent: QWidget, payload: dict) -> str:
    dialog_type = _text_or_default(payload.get("type"), "")
    _GUI_DIALOG_SERVICE.refresh_environment()

    if dialog_type == "alert":
        _GUI_DIALOG_SERVICE.alert(
            text=_text_or_default(payload.get("text"), ""),
            title=_text_or_default(payload.get("title"), "Informação"),
            button=_text_or_default(payload.get("button"), "OK"),
            parent=parent,
        )
        return BRIDGE_ACK

    if dialog_type == "prompt":
        require_input = bool(payload.get("require_input", False))
        allow_cancel = bool(payload.get("allow_cancel", True))
        cancel_message = _text_or_default(payload.get("cancel_message"), "")
        result = _GUI_DIALOG_SERVICE.prompt(
            text=_text_or_default(payload.get("text"), "Informe o valor:"),
            title=_text_or_default(payload.get("title"), "Entrada"),
            default=_text_or_default(payload.get("default"), ""),
            require_input=require_input,
            allow_cancel=allow_cancel,
            cancel_message=cancel_message,
            parent=parent,
        )
        return result if result is not None else BRIDGE_CANCEL

    if dialog_type == "confirm":
        buttons = payload.get("buttons") or ["OK", "Cancel"]
        if not isinstance(buttons, list) or not buttons:
            buttons = ["OK", "Cancel"]
        normalized = [_text_or_default(btn, "") for btn in buttons]
        result = _GUI_DIALOG_SERVICE.confirm(
            text=_text_or_default(payload.get("text"), "Confirma?"),
            title=_text_or_default(payload.get("title"), "Confirmação"),
            buttons=normalized,
            parent=parent,
        )
        return result if result is not None else BRIDGE_CANCEL
    return BRIDGE_ACK  # Unknown payload type; acknowledge to avoid blocking the automation.
