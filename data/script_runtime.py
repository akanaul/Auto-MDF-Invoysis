"""Shared runtime helpers for Auto MDF automation scripts.

Centralises bridge-aware dialog handling, browser focus restoration and
progress/error utilities so that individual scripts stay lightweight and
consistent. Keeping the logic here reduces duplication and makes it easier to
roll out compatibility fixes (for example, timing adjustments) across the
entire catalogue of scripts.
"""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import contextmanager, suppress
from functools import partial
from typing import Any, Iterator, Optional, Sequence

try:
    from .automation_focus import focus
except Exception:  # pragma: no cover - fallback when packages are missing
    focus = None  # type: ignore[assignment]

BRIDGE_ACTIVE = os.environ.get("MDF_BRIDGE_ACTIVE") == "1"
BRIDGE_PREFIX = os.environ.get("MDF_BRIDGE_PREFIX", "__MDF_GUI_BRIDGE__")
BRIDGE_ACK = os.environ.get("MDF_BRIDGE_ACK", "__MDF_GUI_ACK__")
BRIDGE_CANCEL = os.environ.get("MDF_BRIDGE_CANCEL", "__MDF_GUI_CANCEL__")
DEFAULT_TOTAL_STEPS = 100


def configure_stdio() -> None:
    """Force UTF-8 output so Windows consoles behave like the GUI bridge."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def ensure_browser_focus(
    *,
    preserve_tab: bool = False,
    allow_taskbar: bool = True,
    retries: int = 6,
    retry_delay: float = 0.25,
) -> bool:
    """Attempt to bring the browser back to the foreground."""
    if focus is None:
        return False

    focus.prepare_taskbar_retry()
    time.sleep(0.05)

    attempts = max(1, retries)
    pause = max(0.05, retry_delay)
    for attempt in range(attempts):
        with suppress(Exception):
            if focus.ensure_browser_focus(allow_taskbar=allow_taskbar, preserve_tab=preserve_tab) and focus.wait_until_browser_active():
                return True
        if attempt < attempts - 1:
            time.sleep(pause)

    if focus.wait_until_browser_active():
        return True

    print(
        "[AutoMDF] Aviso: não foi possível restabelecer o foco do navegador após o alerta.",
        flush=True,
    )
    return False


def _send_bridge_payload(payload: dict[str, Any]) -> None:
    message = BRIDGE_PREFIX + json.dumps(payload, ensure_ascii=False)
    print(message, flush=True)


def _parse_bridge_response(line: str) -> tuple[Optional[str], bool]:
    if not line:
        return None, True
    response = line.rstrip("\n")
    if response == BRIDGE_CANCEL:
        return None, True
    return ("", True) if response == BRIDGE_ACK else (response, True)


def _bridge_request(payload: dict[str, Any]) -> tuple[Optional[str], bool]:
    if not BRIDGE_ACTIVE:
        return None, False
    try:
        _send_bridge_payload(payload)
        return _parse_bridge_response(sys.stdin.readline())
    except Exception:
        return None, False


@contextmanager
def _tk_root() -> Iterator[Any]:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    root.after(0, root.focus_force)
    root.after(0, root.lift)
    try:
        yield root
    finally:
        try:
            root.destroy()
        finally:
            ensure_browser_focus(preserve_tab=True)


def prompt_topmost(*args, **kwargs) -> Optional[str]:
    """Show a prompt that stays on top, harmonised with the GUI bridge."""
    text, title, default_value = _parse_text_title_defaults(args, kwargs, "Entrada")

    response, handled = _bridge_request(
        {
            "type": "prompt",
            "text": text or "",
            "title": title or "Entrada",
            "default": default_value or "",
        }
    )
    if handled:
        ensure_browser_focus(preserve_tab=True)
        return response

    from tkinter import simpledialog

    with _tk_root() as root:
        return simpledialog.askstring(title or "Entrada", text or "", parent=root, initialvalue=default_value)


def alert_topmost(*args, **kwargs) -> str:
    """Show an alert that stays on top, using the GUI bridge when possible."""
    text, title, button_default = _parse_text_title_defaults(args, kwargs, "Informação")
    button_text = kwargs.get("button", button_default or "OK")

    _, handled = _bridge_request(
        {
            "type": "alert",
            "text": text or "",
            "title": title or "Informação",
            "button": button_text,
        }
    )
    if handled:
        ensure_browser_focus(preserve_tab=True)
        return button_text

    from tkinter import messagebox

    with _tk_root() as root:
        messagebox.showinfo(title or "Informação", text or "", parent=root)
    return button_text


def confirm_topmost(*args, **kwargs) -> Optional[str]:
    """Show a confirmation dialog that stays on top."""
    text, title, _ = _parse_text_title_defaults(args, kwargs, "Confirmação")
    buttons = kwargs.get("buttons") or ["OK", "Cancel"]

    response, handled = _bridge_request(
        {
            "type": "confirm",
            "text": text or "",
            "title": title or "Confirmação",
            "buttons": buttons,
        }
    )
    if handled:
        ensure_browser_focus(preserve_tab=True)
        if response is not None:
            return response
        return "Cancel" if "Cancel" in buttons else buttons[-1]

    import tkinter as tk

    with _tk_root() as root:
        top = tk.Toplevel(root)
        top.title(title or "Confirmação")
        top.transient(root)
        top.attributes("-topmost", True)
        top.resizable(False, False)

        result = {"value": buttons[0]}

        def on_click(value: str) -> None:
            result["value"] = value
            top.destroy()

        def on_close() -> None:
            result["value"] = "Cancel" if "Cancel" in buttons else buttons[-1]
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", on_close)

        label = tk.Label(top, text=text or "", justify="left", wraplength=420)
        label.pack(padx=20, pady=(20, 10))

        button_frame = tk.Frame(top)
        button_frame.pack(padx=20, pady=(0, 20))

        columns = min(3, len(buttons)) or 1
        for idx, btn_text in enumerate(buttons):
            button = tk.Button(button_frame, text=btn_text, width=18, command=partial(on_click, btn_text))
            row = idx // columns
            col = idx % columns
            button.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

        top.update_idletasks()
        top.lift()
        top.focus_force()
        width = top.winfo_width()
        height = top.winfo_height()
        screen_width = top.winfo_screenwidth()
        screen_height = top.winfo_screenheight()
        pos_x = (screen_width // 2) - (width // 2)
        pos_y = (screen_height // 2) - (height // 2)
        top.geometry(f"+{pos_x}+{pos_y}")
        top.grab_set()
        top.focus_force()
        top.lift()

        root.wait_window(top)
        return result["value"]


def register_exception_handler(progress_manager: Any) -> None:
    """Ensure uncaught errors surface in the GUI bridge and log output."""
    original_hook = sys.excepthook

    def _handle(exc_type, exc_value, exc_traceback):
        if exc_type is SystemExit:
            original_hook(exc_type, exc_value, exc_traceback)
            return
        with suppress(Exception):
            progress_manager.error(f"Erro inesperado: {exc_value}")
        try:
            alert_topmost(
                "Ocorreu um erro inesperado. Verifique o log para detalhes.\n\n" f"{exc_value}"
            )
        finally:
            original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _handle


def checkpoint(progress_manager: Any, percent: int, step: str) -> None:
    """Update progress consistently across scripts."""
    progress_manager.update(percent, step)
    progress_manager.add_log(step)


def abort(progress_manager: Any, message: str) -> None:
    """Stop execution after surfacing the reason to the operator."""
    progress_manager.error(message)
    alert_topmost(message)
    raise SystemExit(1)


def apply_pyautogui_bridge(pyautogui_module: Any) -> None:
    """Patch PyAutoGUI dialogs and timing knobs for bridge compatibility."""
    setattr(pyautogui_module, "prompt", prompt_topmost)
    setattr(pyautogui_module, "alert", alert_topmost)
    setattr(pyautogui_module, "confirm", confirm_topmost)
    pyautogui_module.FAILSAFE = True

    pause_env = os.environ.get("MDF_PYAUTOGUI_PAUSE")
    if pause_env := os.environ.get("MDF_PYAUTOGUI_PAUSE"):
        with suppress(ValueError):
            pause_value = float(pause_env)
            if pause_value >= 0:
                pyautogui_module.PAUSE = pause_value

    if min_sleep_env := os.environ.get("MDF_PYAUTOGUI_MIN_SLEEP"):
        with suppress(ValueError):
            min_sleep_value = float(min_sleep_env)
            if min_sleep_value >= 0:
                pyautogui_module.MINIMUM_SLEEP = min_sleep_value


def _parse_text_title_defaults(args: Sequence[Any], kwargs: dict[str, Any], default_title: str) -> tuple[str, str, Optional[str]]:
    text = ""
    title = default_title
    default_value: Optional[str] = None

    if args:
        text = args[0]
    if len(args) > 1:
        title = args[1]
    if len(args) > 2:
        default_value = args[2]

    if "text" in kwargs:
        text = kwargs["text"]
    if "title" in kwargs:
        title = kwargs["title"]
    if "default" in kwargs:
        default_value = kwargs["default"]

    return text, title, default_value


__all__ = [
    "DEFAULT_TOTAL_STEPS",
    "abort",
    "alert_topmost",
    "apply_pyautogui_bridge",
    "checkpoint",
    "confirm_topmost",
    "configure_stdio",
    "ensure_browser_focus",
    "prompt_topmost",
    "register_exception_handler",
]
