"""Dialog helpers for handling bridge interactions in the Qt GUI."""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .constants import BRIDGE_ACK, BRIDGE_CANCEL

try:  # Import lazily to avoid hard failures when GUI dependencies are missing.
    from data.automation_focus import focus
except ModuleNotFoundError:  # pragma: no cover
    focus = None  # type: ignore[assignment]


def _restore_browser_focus(preserve_tab: bool = True) -> None:
    if focus is None:
        return
    focus.prepare_taskbar_retry()
    time.sleep(0.05)
    for _ in range(9):
        with suppress(Exception):  # pragma: no cover - best-effort only
            if preserve_tab:
                success = focus.ensure_browser_focus_preserve_tab(allow_taskbar=True)
            else:
                success = focus.ensure_browser_focus(allow_taskbar=True)
            if success:
                focus.wait_until_browser_active()
                return
        time.sleep(0.2)


def _activate_dialog(widget: QWidget) -> None:
    widget.raise_()
    widget.activateWindow()
    widget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)


def _exec_modal(widget: QDialog) -> int:
    widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
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
    ok_button.setText(button or "OK")
    message_box.setDefaultButton(QMessageBox.StandardButton.Ok)
    _exec_modal(message_box)
    _restore_browser_focus(preserve_tab=True)
    return BRIDGE_ACK


def show_prompt(parent: QWidget, *, title: str, text: str, default: str) -> Optional[str]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title or "Entrada")
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 16, 20, 16)

    label = QLabel(text or "Informe o valor:")
    label.setWordWrap(True)
    layout.addWidget(label)

    from PySide6.QtWidgets import QLineEdit  # Local import to reduce module weight

    line_edit = QLineEdit(dialog)
    line_edit.setText(default or "")
    line_edit.selectAll()
    layout.addWidget(line_edit)

    button_row = QHBoxLayout()
    layout.addLayout(button_row)

    result: dict[str, Optional[str]] = {"value": None}

    def accept() -> None:
        result["value"] = line_edit.text()
        dialog.accept()

    def reject() -> None:
        result["value"] = None
        dialog.reject()

    cancel_button = QPushButton("Cancelar", dialog)
    cancel_button.clicked.connect(reject)
    button_row.addWidget(cancel_button)

    ok_button = QPushButton("OK", dialog)
    ok_button.clicked.connect(accept)
    ok_button.setDefault(True)
    button_row.addWidget(ok_button)

    dialog.resize(360, dialog.sizeHint().height())
    line_edit.setFocus(Qt.FocusReason.TabFocusReason)
    _exec_modal(dialog)
    _restore_browser_focus(preserve_tab=True)
    return result["value"]


def show_confirm(parent: QWidget, *, title: str, text: str, buttons: list[str]) -> Optional[str]:
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
    dialog_type = str(payload.get("type", ""))
    if dialog_type == "alert":
        button_text = str(payload.get("button") or "OK")
        return show_alert(parent, title=str(payload.get("title") or "Informação"), text=str(payload.get("text") or ""), button=button_text)
    if dialog_type == "prompt":
        result = show_prompt(
            parent,
            title=str(payload.get("title") or "Entrada"),
            text=str(payload.get("text") or "Informe o valor:"),
            default=str(payload.get("default") or ""),
        )
        return result if result is not None else BRIDGE_CANCEL
    if dialog_type == "confirm":
        buttons = payload.get("buttons") or ["OK", "Cancel"]
        if not isinstance(buttons, list) or not buttons:
            buttons = ["OK", "Cancel"]
        result = show_confirm(
            parent,
            title=str(payload.get("title") or "Confirmação"),
            text=str(payload.get("text") or "Confirma?"),
            buttons=[str(btn) for btn in buttons],
        )
        return result if result is not None else BRIDGE_CANCEL
    # Unknown payload type, acknowledge to avoid blocking the automation.
    return BRIDGE_ACK

