"""Shared browser focus helpers for MDF automation scripts.

This module centralizes the logic required to keep the target browser window
active during automation runs. It consolidates duplicated focus-management
code from the individual automation scripts, making maintenance easier and
reducing the chance of divergence between implementations.
"""

from __future__ import annotations

import contextlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

_pyautogui: Any
_pygetwindow: Any

try:
    import pyautogui as _pyautogui  # type: ignore
except Exception:  # pragma: no cover - pyautogui may be missing in some envs
    _pyautogui = None

try:
    import pygetwindow as _pygetwindow  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _pygetwindow = None

pyautogui: Any = _pyautogui
gw: Any = _pygetwindow

ctypes: Any = None
wintypes: Any = None
_EnumWindowsProc: Any = None
_EnumWindows: Any = None
_IsWindowVisible: Any = None
_GetWindowTextLengthW: Any = None
_GetWindowTextW: Any = None
_SetForegroundWindow: Any = None
_BringWindowToTop: Any = None
_ShowWindow: Any = None
_GetForegroundWindow: Any = None
_SW_RESTORE = 9

if os.name == "nt":
    import ctypes  # type: ignore
    from ctypes import wintypes

    _user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    _EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _EnumWindows = _user32.EnumWindows
    _EnumWindows.argtypes = [_EnumWindowsProc, wintypes.LPARAM]
    _EnumWindows.restype = wintypes.BOOL
    _IsWindowVisible = _user32.IsWindowVisible
    _GetWindowTextLengthW = _user32.GetWindowTextLengthW
    _GetWindowTextW = _user32.GetWindowTextW
    _SetForegroundWindow = _user32.SetForegroundWindow
    _BringWindowToTop = _user32.BringWindowToTop
    _ShowWindow = _user32.ShowWindow
    _GetForegroundWindow = _user32.GetForegroundWindow
    _GetForegroundWindow.restype = wintypes.HWND


GUI_WINDOW_KEYWORDS = ["Auto MDF InvoISys", "Control Center v0.5.0-Alpha-GUI"]
BROWSER_WINDOW_KEYWORDS = ["Google Chrome", "Microsoft Edge", "Mozilla Firefox", "Brave", "Opera"]


@dataclass
class BrowserFocusController:
    """Tracks and restores focus to the configured browser window."""

    target_tab: int = field(default_factory=lambda: BrowserFocusController._resolve_target_tab())
    last_browser_window: object | None = None
    last_taskbar_launch: float = 0.0
    taskbar_launched: bool = False
    taskbar_launch_attempts: int = 0

    def prepare_for_execution(self) -> None:
        """Reset state prior to running an automation script."""
        self.target_tab = self._resolve_target_tab()
        self.last_browser_window = None
        self.last_taskbar_launch = 0.0
        self.taskbar_launched = False
        self.taskbar_launch_attempts = 0

    def prepare_taskbar_retry(self) -> None:
        """Allow a new Win+1 attempt when focus returns to the GUI."""
        title = self._active_window_title().lower()
        if not title:
            return
        if any(keyword.lower() in title for keyword in GUI_WINDOW_KEYWORDS):
            self.taskbar_launched = False
            self.taskbar_launch_attempts = 0
            self.last_taskbar_launch = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ensure_browser_focus(
        self,
        *,
        allow_taskbar: bool = True,
        switch_to_target_tab: Optional[bool] = None,
        preserve_tab: bool = False,
    ) -> bool:
        """Guarantee the browser window is focused."""
        if switch_to_target_tab is None:
            switch_to_target_tab = not preserve_tab
        if gw:
            try:
                active = self._get_active_window()
            except Exception:
                active = None

            if self._is_browser_window(active):
                self._record_activation(active)
                if switch_to_target_tab:
                    self._switch_to_target_tab()
                return True

            if self._is_gui_window(active) and self._activate_browser_window(switch_to_target_tab):
                return True

        if self._activate_browser_window(switch_to_target_tab):
            return True

        if allow_taskbar and self.launch_taskbar_slot():
            return self._activate_browser_window(switch_to_target_tab)

        return False

    def ensure_browser_focus_if_gui_active(self) -> bool:
        """Restore browser focus only when the GUI currently owns the focus."""
        if not self._is_gui_active():
            return False
        success = self.ensure_browser_focus(allow_taskbar=False, switch_to_target_tab=False)
        if success:
            self.wait_until_browser_active()
        return success

    def _is_gui_active(self) -> bool:
        if gw is None:
            return False
        try:
            active = gw.getActiveWindow()
        except Exception:
            return False
        return self._is_gui_window(active)

    def launch_taskbar_slot(self, wait: float = 0.6) -> bool:
        """Attempt to bring the pinned browser to the foreground via Win+1."""
        if self._is_browser_active():
            self.taskbar_launched = True
            return True

        launched = self._launch_browser_via_taskbar()
        if launched and wait > 0:
            time.sleep(wait)
        return launched

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_target_tab() -> int:
        raw = os.environ.get("MDF_BROWSER_TAB", "").strip()
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return 0
        return 0 if value <= 0 else min(value, 9)

    def _is_browser_window(self, window) -> bool:
        return self._matches_keywords(window, BROWSER_WINDOW_KEYWORDS)

    def _is_gui_window(self, window) -> bool:
        return self._matches_keywords(window, GUI_WINDOW_KEYWORDS)

    def _is_browser_active(self) -> bool:
        title = self._active_window_title().lower()
        if not title:
            return False
        return any(keyword.lower() in title for keyword in BROWSER_WINDOW_KEYWORDS)

    def _active_window_title(self) -> str:
        if gw is not None:
            with contextlib.suppress(Exception):
                window = gw.getActiveWindow()
                if window and getattr(window, "title", None):
                    return str(window.title)
        if _GetForegroundWindow is not None and _GetWindowTextLengthW is not None and _GetWindowTextW is not None:
            with contextlib.suppress(Exception):
                hwnd = _GetForegroundWindow()
                if hwnd:
                    length = _GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        _GetWindowTextW(hwnd, buffer, length + 1)
                        return buffer.value
        return ""

    def _matches_keywords(self, window, keywords: list[str]) -> bool:
        if lowered := self._window_title_lower(window):
            return any(keyword.lower() in lowered for keyword in keywords)
        return False

    def _window_title_lower(self, window) -> str:
        if gw is None or window is None:
            return ""
        with contextlib.suppress(Exception):
            title = getattr(window, "title", "") or ""
            return str(title).lower()
        return ""

    def _switch_to_target_tab(self) -> None:
        if self.target_tab <= 0 or pyautogui is None:
            return
        with contextlib.suppress(Exception):
            pyautogui.hotkey("ctrl", str(self.target_tab))
            time.sleep(0.15)

    def _launch_browser_via_taskbar(self) -> bool:
        if pyautogui is None:
            return False
        if self.taskbar_launched:
            return False
        if self.taskbar_launch_attempts >= 3:
            return False
        now = time.time()
        if now - self.last_taskbar_launch < 1.5:
            return False

        self.last_taskbar_launch = now
        self.taskbar_launch_attempts += 1
        with contextlib.suppress(Exception):
            pyautogui.hotkey("win", "1")
            self.taskbar_launched = True
            return True
        return False

    def _activate_browser_window(self, switch_to_target_tab: bool) -> bool:
        if gw:
            candidates: list[object] = []
            active = self._get_active_window()

            if self._is_browser_window(active):
                candidates.append(active)

            if (
                self.last_browser_window
                and self._is_browser_window(self.last_browser_window)
                and self.last_browser_window not in candidates
            ):
                candidates.append(self.last_browser_window)

            with contextlib.suppress(Exception):
                for keyword in BROWSER_WINDOW_KEYWORDS:
                    for window in gw.getWindowsWithTitle(keyword):
                        if self._is_browser_window(window) and window not in candidates:
                            candidates.append(window)

            for window in candidates:
                if self._activate_candidate_window(window, switch_to_target_tab):
                    return True

        if self._activate_via_winapi(switch_to_target_tab):
            self.taskbar_launched = True
            return True

        return False

    def _get_active_window(self):
        if gw is None:
            return None
        with contextlib.suppress(Exception):
            return gw.getActiveWindow()
        return None

    def ensure_browser_focus_preserve_tab(self, *, allow_taskbar: bool = True) -> bool:
        return self.ensure_browser_focus(allow_taskbar=allow_taskbar, preserve_tab=True)

    def wait_until_browser_active(self, timeout: float = 1.6, poll_interval: float = 0.12) -> bool:
        """Wait until the browser window becomes the foreground window."""
        if gw is None:
            return True
        end_time = time.time() + max(0.0, timeout)
        while time.time() < end_time:
            if self._is_browser_window(self._get_active_window()):
                return True
            time.sleep(max(0.01, poll_interval))
        return self._is_browser_window(self._get_active_window())

    def _activate_candidate_window(self, window, switch_to_target_tab: bool) -> bool:
        with contextlib.suppress(Exception):
            if getattr(window, "isMinimized", False):
                window.restore()
            window.activate()
            self._record_activation(window)
            time.sleep(0.25)
            if switch_to_target_tab:
                self._switch_to_target_tab()
            return True
        return False

    def _record_activation(self, window) -> None:
        self.last_browser_window = window
        self.taskbar_launched = True

    def _activate_via_winapi(self, switch_to_target_tab: bool) -> bool:
        if (
            ctypes is None
            or _EnumWindows is None
            or _EnumWindowsProc is None
            or _IsWindowVisible is None
            or _GetWindowTextLengthW is None
            or _GetWindowTextW is None
        ):
            return False

        handles: list[int] = []
        gui_keywords = [kw.lower() for kw in GUI_WINDOW_KEYWORDS]
        browser_keywords = [kw.lower() for kw in BROWSER_WINDOW_KEYWORDS]

        def enum_proc(hwnd, _lparam):
            try:
                if not _IsWindowVisible(hwnd):
                    return True
                length = _GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                _GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value.lower()
            except Exception:
                return True

            if not title:
                return True
            for keyword in gui_keywords:
                if keyword in title:
                    return True
            for keyword in browser_keywords:
                if keyword in title:
                    handles.append(hwnd)
                    break
            return True

        try:
            callback = _EnumWindowsProc(enum_proc)
            _EnumWindows(callback, 0)
        except Exception:
            return False

        for hwnd in handles:
            if _ShowWindow is not None:
                with contextlib.suppress(Exception):
                    _ShowWindow(hwnd, _SW_RESTORE)
            if _SetForegroundWindow is not None:
                with contextlib.suppress(Exception):
                    if _SetForegroundWindow(hwnd):
                        if switch_to_target_tab:
                            self._switch_to_target_tab()
                        return True
            if _BringWindowToTop is not None:
                with contextlib.suppress(Exception):
                    _BringWindowToTop(hwnd)
                    if switch_to_target_tab:
                        self._switch_to_target_tab()
                    return True
        return False


focus = BrowserFocusController()
__all__ = ["focus", "BrowserFocusController"]