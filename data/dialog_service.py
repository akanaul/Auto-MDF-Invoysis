"""Serviço de diálogos Qt ciente do bridge para scripts de automação."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from PySide6.QtWidgets import QDialog, QWidget


class DialogService:
    """Expõe diálogos de alerta/prompt/confirmação integrados ao bridge da GUI."""

    _qt_core_exit_wrapped = False
    _qt_eventloop_exit_wrapped = False

    def __init__(
        self,
        parent_provider: Optional[Callable[[], Optional["QWidget"]]] = None,
        *,
        bridge_enabled: Optional[bool] = None,
    ) -> None:
        self._parent_provider = parent_provider
        self._bridge_override = bridge_enabled
        self._qt_app: Any | None = None
        self._active_modal_count = 0
        self.refresh_environment()

    def refresh_environment(self) -> None:
        env_active = os.environ.get("MDF_BRIDGE_ACTIVE") == "1"
        if self._bridge_override is None:
            self.bridge_active = env_active
        else:
            self.bridge_active = bool(self._bridge_override)
        self.bridge_prefix = os.environ.get("MDF_BRIDGE_PREFIX", "__MDF_GUI_BRIDGE__")
        self.bridge_ack = os.environ.get("MDF_BRIDGE_ACK", "__MDF_GUI_ACK__")
        self.bridge_cancel = os.environ.get("MDF_BRIDGE_CANCEL", "__MDF_GUI_CANCEL__")
        self._log(
            f"Bridge ativo: {self.bridge_active} (override={self._bridge_override}, env={env_active}).",
            level="debug",
        )

    # ------------------------------------------------------------------
    # Auxiliares Qt
    # ------------------------------------------------------------------
    def _ensure_qapp(self) -> Any:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
            with contextlib.suppress(Exception):  # pragma: no cover - best effort
                app.setQuitOnLastWindowClosed(False)
            self._log("QApplication criado para fallback Qt.", level="debug")
        else:
            self._log(
                "Reutilizando QApplication existente para fallback Qt.", level="debug"
            )
        self._install_qt_diagnostics(app)
        self._qt_app = app
        return app

    def _resolve_parent(
        self, explicit_parent: Optional["QWidget"]
    ) -> Optional["QWidget"]:
        if explicit_parent is not None:
            return explicit_parent
        if self._parent_provider is None:
            return None
        try:
            return self._parent_provider()
        except Exception:  # pragma: no cover - defensive
            return None

    @staticmethod
    def _log(message: str, level: str = "debug") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[AutoMDF][DIALOG][{level.upper()}][{timestamp}] {message}", flush=True)

    @staticmethod
    def _activate_dialog(widget: "QWidget") -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        state = widget.windowState()
        if state & Qt.WindowState.WindowMinimized:
            widget.setWindowState(state & ~Qt.WindowState.WindowMinimized)
        if not widget.isVisible():
            widget.show()
        widget.raise_()
        if not widget.isActiveWindow():
            widget.activateWindow()
        widget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        handle = widget.windowHandle()
        if handle is not None:
            handle.requestActivate()
        app = QApplication.instance()
        if app is not None:
            QApplication.setActiveWindow(widget)

    def _exec_modal(self, dialog: "QDialog") -> int:
        from PySide6.QtCore import QTimer

        def _activate() -> None:
            DialogService._log("Acionando ativação para diálogo Qt.")
            DialogService._activate_dialog(dialog)

        QTimer.singleShot(0, _activate)
        self._log("Iniciando loop modal do diálogo Qt.")
        self._active_modal_count += 1
        try:
            return dialog.exec()
        finally:
            self._active_modal_count = max(0, self._active_modal_count - 1)
            self._log("Loop modal do diálogo Qt finalizado.")

    def _install_qt_diagnostics(self, app: Any) -> None:
        """Instala hooks uma única vez para monitorar saídas inesperadas do Qt."""

        if getattr(self, "_qt_hooks_installed", False):
            return

        try:
            from PySide6.QtCore import QCoreApplication, QEventLoop
        except Exception:  # pragma: no cover - PySide6 missing
            return

        if not getattr(DialogService, "_qt_core_exit_wrapped", False):
            original_exit = QCoreApplication.exit

            def logged_exit(code: int = 0) -> None:
                DialogService._log(
                    f"QCoreApplication.exit({code}) chamado.", level="warning"
                )
                return original_exit(code)

            QCoreApplication.exit = staticmethod(logged_exit)  # type: ignore[assignment]
            DialogService._qt_core_exit_wrapped = True

        if not getattr(DialogService, "_qt_eventloop_exit_wrapped", False):
            original_loop_exit = QEventLoop.exit

            def logged_loop_exit(loop_self: Any, return_code: int = 0) -> None:
                DialogService._log(
                    f"QEventLoop.exit({return_code}) chamado.", level="warning"
                )
                return original_loop_exit(loop_self, return_code)

            QEventLoop.exit = logged_loop_exit  # type: ignore[assignment]
            DialogService._qt_eventloop_exit_wrapped = True

        with contextlib.suppress(Exception):
            app.aboutToQuit.connect(
                lambda: DialogService._log(
                    "QApplication.aboutToQuit emitido.", level="warning"
                )
            )

        self._qt_hooks_installed = True

    def is_modal_active(self) -> bool:
        """Retorna True enquanto um diálogo Qt modal estiver aberto."""

        return self._active_modal_count > 0

    def _show_prompt_qt(
        self,
        *,
        text: str,
        title: str,
        default: str,
        require_input: bool,
        allow_cancel: bool,
        cancel_message: str,
        parent: Optional["QWidget"],
    ) -> Optional[str]:
        from PySide6.QtCore import Qt
        from PySide6.QtCore import QEvent, QTimer
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QVBoxLayout,
        )

        parent_widget = self._resolve_parent(parent)

        result: dict[str, Optional[str]] = {"value": None}
        cancel_message = (cancel_message or "").strip()
        service = self

        class _PromptDialog(QDialog):
            def __init__(self) -> None:
                super().__init__(parent_widget)
                service._log(
                    "Instanciando QDialog fallback para prompt.", level="debug"
                )
                self._allow_cancel = allow_cancel
                self._cancel_message = cancel_message
                self._explicit_close = False
                self._reactivation_pending = False
                self._reactivation_block_count = 0
                if not self._allow_cancel:
                    self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
                self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
                self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

            def reject(self) -> None:  # type: ignore[override]
                if not self._allow_cancel:
                    return
                if self._cancel_message:
                    with self._temporary_reactivation_guard("cancel_confirmation"):
                        answer = QMessageBox.question(
                            self,
                            "Cancelar entrada",
                            self._cancel_message,
                            QMessageBox.StandardButton.Yes
                            | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No,
                        )
                    if answer != QMessageBox.StandardButton.Yes:
                        self._schedule_reactivation("cancel_declined")
                        return
                result["value"] = None
                service._log(
                    "Prompt Qt rejeitado pelo usuário/cancelamento.", level="debug"
                )
                self._explicit_close = True
                super().reject()

            def closeEvent(self, event) -> None:  # type: ignore[override]
                service._log("Prompt Qt recebeu closeEvent.", level="debug")
                super().closeEvent(event)

            def showEvent(self, event) -> None:  # type: ignore[override]
                service._log("Prompt Qt showEvent acionado.", level="debug")
                super().showEvent(event)

            def hideEvent(self, event) -> None:  # type: ignore[override]
                service._log("Prompt Qt hideEvent acionado.", level="debug")
                super().hideEvent(event)

            def done(self, result_code: int) -> None:  # type: ignore[override]
                service._log(f"Prompt Qt done({result_code}) acionado.", level="debug")
                self._explicit_close = True
                super().done(result_code)

            def _schedule_reactivation(self, reason: str) -> None:
                if (
                    self._explicit_close
                    or self._reactivation_pending
                    or self._reactivation_block_count > 0
                ):
                    return
                if self.isActiveWindow():
                    return

                def _reactivate() -> None:
                    self._reactivation_pending = False
                    if self._explicit_close:
                        return
                    service._log(
                        f"Reativando prompt Qt após evento: {reason}.",
                        level="debug",
                    )
                    DialogService._activate_dialog(self)

                self._reactivation_pending = True
                QTimer.singleShot(80, _reactivate)

            @contextlib.contextmanager
            def _temporary_reactivation_guard(self, reason: str):
                self._reactivation_block_count += 1
                try:
                    service._log(
                        f"Suspensão temporária da reativação do prompt devido a: {reason}.",
                        level="debug",
                    )
                    yield
                finally:
                    self._reactivation_block_count = max(
                        0, self._reactivation_block_count - 1
                    )

            def event(self, event) -> bool:  # type: ignore[override]
                try:
                    event_type = int(getattr(event, "type")())
                except Exception:
                    event_type = -1
                if (
                    event_type in {QEvent.Type.Hide, QEvent.Type.HideToParent}
                    and not self._explicit_close
                ):
                    service._log(
                        "Prompt Qt bloqueou hide automático; reexibindo diálogo.",
                        level="debug",
                    )
                    event.ignore()
                    self._schedule_reactivation("hide")
                    return True
                if (
                    event_type in {QEvent.Type.WindowDeactivate, QEvent.Type.FocusOut}
                    and not self._explicit_close
                ):
                    self._schedule_reactivation("deactivate")
                return super().event(event)

            def changeEvent(self, event) -> None:  # type: ignore[override]
                try:
                    event_type = int(getattr(event, "type")())
                except Exception:
                    event_type = -1
                service._log(
                    f"Prompt Qt changeEvent recebido: type={event_type}.", level="debug"
                )
                super().changeEvent(event)

        dialog = _PromptDialog()
        dialog.setModal(True)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dialog.raise_()
        dialog.activateWindow()
        dialog.setWindowTitle(title or "Entrada")

        def on_dialog_accepted() -> None:
            self._log("Prompt Qt sinal accepted disparado.", level="debug")

        def on_dialog_rejected() -> None:
            self._log("Prompt Qt sinal rejected disparado.", level="debug")

        def on_dialog_finished(code: int) -> None:
            self._log(
                f"Prompt Qt sinal finished disparado com code={code}.", level="debug"
            )

        dialog.accepted.connect(on_dialog_accepted)
        dialog.rejected.connect(on_dialog_rejected)
        dialog.finished.connect(on_dialog_finished)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 16, 20, 16)

        label = QLabel(text or "Informe o valor:")
        label.setWordWrap(True)
        layout.addWidget(label)

        line_edit = QLineEdit(dialog)
        line_edit.setText(default or "")
        line_edit.selectAll()
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
            service._log("Prompt Qt aceito manualmente pelo usuário.", level="debug")
            dialog.accept()

        if allow_cancel:
            cancel_button = QPushButton("Cancelar", dialog)
            cancel_button.clicked.connect(dialog.reject)
            button_row.addWidget(cancel_button)

        ok_button = QPushButton("OK", dialog)
        ok_button.clicked.connect(accept)
        ok_button.setDefault(True)
        if require_input and not (line_edit.text().strip()):
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
        self._log("Executando dialog.exec() para prompt Qt.", level="debug")
        dialog_result = self._exec_modal(dialog)
        from PySide6.QtCore import Qt as _QtAlias

        visible_after = dialog.isVisible()
        current_result = dialog.result()
        delete_on_close = dialog.testAttribute(
            _QtAlias.WidgetAttribute.WA_DeleteOnClose
        )
        self._log(
            "Prompt Qt finalizou com dialog_result="
            f"{dialog_result} e valor={result['value']!r}. (visible={visible_after}, result_property={current_result},"
            f" delete_on_close={delete_on_close})"
        )

        with contextlib.suppress(RuntimeError):
            dialog.deleteLater()

        return_value = result["value"]
        if return_value is None:
            return None
        trimmed = return_value.strip()
        return trimmed or None

    def _show_alert_qt(
        self,
        *,
        text: str,
        title: str,
        button: str,
        parent: Optional["QWidget"],
    ) -> str:
        from PySide6.QtWidgets import QMessageBox

        parent_widget = self._resolve_parent(parent)
        message_box = QMessageBox(parent_widget)
        message_box.setIcon(QMessageBox.Icon.Information)
        message_box.setWindowTitle(title or "Informação")
        message_box.setText(text or "")
        message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        ok_button = message_box.button(QMessageBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText(button or "OK")
        message_box.setDefaultButton(QMessageBox.StandardButton.Ok)
        self._exec_modal(message_box)
        return button or "OK"

    def _show_confirm_qt(
        self,
        *,
        text: str,
        title: str,
        buttons: list[str],
        parent: Optional["QWidget"],
    ) -> Optional[str]:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QVBoxLayout,
        )

        parent_widget = self._resolve_parent(parent)
        dialog = QDialog(parent_widget)
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
        self._exec_modal(dialog)
        value = choice["value"]
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    # ------------------------------------------------------------------
    # Auxiliares do bridge
    # ------------------------------------------------------------------
    def _send_bridge_payload(self, payload: dict[str, Any]) -> None:
        self._log(f"Enviando payload para bridge: {payload.get('type')}.")
        message = self.bridge_prefix + json.dumps(payload, ensure_ascii=False)
        print(message, flush=True)

    def _parse_bridge_response(self, line: str) -> tuple[Optional[str], bool]:
        if not line:
            return None, True
        response = line.rstrip("\n")
        if response == self.bridge_cancel:
            return None, True
        return ("", True) if response == self.bridge_ack else (response, True)

    def _bridge_request(self, payload: dict[str, Any]) -> tuple[Optional[str], bool]:
        if not self.bridge_active:
            self._log("Bridge desativado; utilizando fallback Qt.", level="info")
            return None, False
        try:
            self._send_bridge_payload(payload)
            response = self._parse_bridge_response(sys.stdin.readline())
            self._log(f"Resposta recebida do bridge: {response}")
            return response
        except Exception:
            self._log(
                "Exceção ao comunicar com a bridge; acionando fallback Qt.",
                level="error",
            )
            return None, False

    # ------------------------------------------------------------------
    # Dialog APIs
    # ------------------------------------------------------------------
    def prompt(
        self,
        *,
        text: str,
        title: str,
        default: str,
        require_input: bool,
        allow_cancel: bool,
        cancel_message: str,
        on_restore_focus: Optional[Callable[[], None]] = None,
        parent: Optional["QWidget"] = None,
    ) -> Optional[str]:  # sourcery skip: low-code-quality
        bridge_payload = {
            "type": "prompt",
            "text": text or "",
            "title": title or "Entrada",
            "default": default or "",
            "require_input": require_input,
            "allow_cancel": allow_cancel,
            "cancel_message": cancel_message or "",
        }

        fallback_default = default or ""
        blank_attempts = 0
        bridge_cancelled = False

        while True:
            response, handled = self._bridge_request(bridge_payload)
            if not handled:
                self._log(
                    "Bridge não lidou com prompt; acionando fallback Qt.", level="info"
                )
                break

            if on_restore_focus:
                on_restore_focus()

            if response is None:
                if require_input and allow_cancel:
                    bridge_cancelled = True
                    self._log(
                        "Usuário cancelou prompt via bridge enquanto entrada obrigatória.",
                        level="warning",
                    )
                    print(
                        "[AutoMDF] Aviso: cancelamento do diálogo principal detectado. Solicitando confirmação ao operador...",
                        flush=True,
                    )
                    break
                return None

            trimmed = response.strip()
            if require_input and not trimmed:
                blank_attempts += 1
                self._log(
                    f"Entrada vazia recebida do bridge (tentativa {blank_attempts}).",
                    level="warning",
                )
                fallback_default = response or ""
                bridge_payload["default"] = fallback_default
                if blank_attempts >= 2:
                    self._log(
                        "Entrada vazia persistente; migrando para fallback Qt.",
                        level="warning",
                    )
                    print(
                        "[AutoMDF] Aviso: entrada vazia recebida do diálogo principal. Alternando para modo de compatibilidade.",
                        flush=True,
                    )
                    break
                continue

            self._log("Entrada recebida do bridge; retornando valor.")
            return trimmed or response or None

        if not bridge_cancelled and require_input:
            print(
                "[AutoMDF] Aviso: entrada vazia persistente no diálogo principal. Alternando para modo de compatibilidade.",
                flush=True,
            )
            self._log(
                "Prompt obrigatório sem resposta; executando fallback Qt.",
                level="warning",
            )

        self._ensure_qapp()
        value = self._show_prompt_qt(
            text=text or "",
            title=title or "Entrada",
            default=fallback_default,
            require_input=require_input,
            allow_cancel=allow_cancel,
            cancel_message=cancel_message or "",
            parent=parent,
        )
        if on_restore_focus:
            on_restore_focus()
        if value is None:
            self._log("Prompt Qt encerrado sem resposta.", level="warning")
        else:
            self._log(f"Prompt Qt retornou valor com comprimento {len(value)}.")
        return value

    def alert(
        self,
        *,
        text: str,
        title: str,
        button: str,
        on_restore_focus: Optional[Callable[[], None]] = None,
        parent: Optional["QWidget"] = None,
    ) -> str:
        response, handled = self._bridge_request(
            {
                "type": "alert",
                "text": text or "",
                "title": title or "Informação",
                "button": button or "OK",
            }
        )
        if handled:
            if on_restore_focus:
                on_restore_focus()
            self._log("Alerta tratado pela bridge.")
            return button or "OK"

        self._ensure_qapp()
        self._show_alert_qt(
            text=text or "",
            title=title or "Informação",
            button=button or "OK",
            parent=parent,
        )
        if on_restore_focus:
            on_restore_focus()
        self._log("Alerta exibido via Qt fallback.", level="info")
        return button or "OK"

    def confirm(
        self,
        *,
        text: str,
        title: str,
        buttons: list[str],
        on_restore_focus: Optional[Callable[[], None]] = None,
        parent: Optional["QWidget"] = None,
    ) -> Optional[str]:
        normalized = buttons or ["OK", "Cancel"]
        normalized = [
            btn for btn in (str(option).strip() for option in normalized) if btn
        ] or ["OK", "Cancel"]

        response, handled = self._bridge_request(
            {
                "type": "confirm",
                "text": text or "",
                "title": title or "Confirmação",
                "buttons": normalized,
            }
        )
        if handled:
            if on_restore_focus:
                on_restore_focus()
            if response is not None:
                trimmed = response.strip()
                self._log(f"Confirmação tratada pela bridge com resposta '{trimmed}'.")
                return trimmed or response or None
            fallback = "Cancel" if "Cancel" in normalized else normalized[-1]
            self._log(
                "Confirmação cancelada pela bridge; retornando fallback.", level="info"
            )
            return fallback

        self._ensure_qapp()
        choice = self._show_confirm_qt(
            text=text or "",
            title=title or "Confirmação",
            buttons=normalized,
            parent=parent,
        )
        if on_restore_focus:
            on_restore_focus()
        if not choice:
            self._log(
                "Confirmação Qt encerrada sem resposta; retornando fallback.",
                level="warning",
            )
            return "Cancel" if "Cancel" in normalized else normalized[-1]
        trimmed = choice.strip()
        self._log(f"Confirmação Qt retornou '{trimmed}'.")
        return trimmed or choice


__all__ = ["DialogService"]
