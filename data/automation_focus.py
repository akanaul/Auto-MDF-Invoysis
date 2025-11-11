"""Utilitários compartilhados para manter o foco do navegador nos scripts MDF.

Este módulo centraliza a lógica necessária para manter a janela do navegador
ativa durante as execuções de automação. Ele consolida trechos duplicados de
foco presentes em scripts individuais, facilitando a manutenção e reduzindo a
chance de divergências entre implementações.
"""

from __future__ import annotations

import contextlib
import os
import time
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

try:
    from data.automation_settings import load_settings
except ImportError:  # pragma: no cover
    load_settings = None

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
_SW_MAXIMIZE = 3

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
BROWSER_WINDOW_KEYWORDS = ["Microsoft Edge", "Edge", "Worktabs"]
BROWSER_KEYWORDS_LOWER = [keyword.lower() for keyword in BROWSER_WINDOW_KEYWORDS]


class BrowserFocusController:
    """Acompanha e restaura o foco para a janela de navegador configurada."""

    # Seguro ajustar: palavras-chave padrão ou lógica de resolução do slot na barra de tarefas.
    # Requer atenção: constantes de tempo e troca de abas — valide nos sistemas operacionais suportados.
    # Apenas para devs: chamadas à API Win32 e heurísticas de foco; erros podem deixar a automação sem controle.

    def __init__(self) -> None:
        self._target_tab = self._resolve_target_tab()
        self._preferred_title = self._resolve_preferred_title()
        self.last_browser_window: object | None = None
        self.last_taskbar_launch: float = 0.0
        self.taskbar_launched: bool = False
        self.taskbar_launch_attempts: int = 0
        self._force_tab_on_focus = True
        self._taskbar_slot = self._resolve_taskbar_slot()

    @property
    def target_tab(self) -> int:
        return self._target_tab

    @target_tab.setter
    def target_tab(self, value: int) -> None:
        self._target_tab = self._normalize_tab(value)
        self._force_tab_on_focus = True

    def prepare_for_execution(self) -> None:
        """Reinicia o estado antes de executar um script de automação."""
        self._target_tab = self._resolve_target_tab()
        self._preferred_title = self._resolve_preferred_title()
        self.last_browser_window = None
        self.last_taskbar_launch = 0.0
        self.taskbar_launched = False
        self.taskbar_launch_attempts = 0
        self._force_tab_on_focus = True
        self._taskbar_slot = self._resolve_taskbar_slot()

    def prepare_taskbar_retry(self) -> None:
        """Permite uma nova tentativa de Win+1 quando o foco volta para a GUI."""
        title = self._active_window_title().lower()
        if not title:
            return
        if any(keyword.lower() in title for keyword in GUI_WINDOW_KEYWORDS):
            self.taskbar_launched = False
            self.taskbar_launch_attempts = 0
            self.last_taskbar_launch = 0.0

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def ensure_browser_focus(
        self,
        *,
        allow_taskbar: bool = True,
        switch_to_target_tab: Optional[bool] = None,
        preserve_tab: bool = False,
    ) -> bool:
        """Garante que a janela do navegador esteja em foco."""
        explicit_switch = switch_to_target_tab is not None
        if switch_to_target_tab is None:
            switch_to_target_tab = not preserve_tab

        should_switch_tab = bool(switch_to_target_tab)
        if (
            not should_switch_tab
            and not explicit_switch
            and not preserve_tab
            and self._force_tab_on_focus
        ):
            should_switch_tab = True

        if gw:
            try:
                active = self._get_active_window()
            except Exception:
                active = None

            if self._is_browser_window(active):
                self._record_activation(active)
                if should_switch_tab:
                    self._switch_to_target_tab()
                return True

            if self._is_gui_window(active) and self._activate_browser_window(
                should_switch_tab
            ):
                return True

        if self._activate_browser_window(should_switch_tab):
            return True

        if allow_taskbar and self.launch_taskbar_slot():
            return self._activate_browser_window(should_switch_tab)

        return False

    def ensure_browser_focus_if_gui_active(self) -> bool:
        """Restaura o foco do navegador apenas quando a GUI estiver ativa."""
        if not self._is_gui_active():
            return False
        success = self.ensure_browser_focus(
            allow_taskbar=False, switch_to_target_tab=False
        )
        if success:
            self.wait_until_browser_active(force_tab=False)
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
        """Traz o Microsoft Edge para frente usando o slot configurado na barra de tarefas."""
        if self._is_browser_active():
            self.taskbar_launched = True
            return True

        if self._activate_preferred_window(should_switch_tab=True):
            self.taskbar_launched = True
            if wait > 0:
                time.sleep(wait)
            return True

        launched = self._launch_browser_via_taskbar()
        if launched and wait > 0:
            time.sleep(wait)
        return launched

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_tab(value: Any) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return 0
        return min(numeric, 9) if numeric > 0 else 0

    @staticmethod
    def _resolve_target_tab() -> int:
        # Primeiro verifica variável de ambiente específica
        raw = os.environ.get("MDF_BROWSER_TAB", "").strip()
        if raw:
            return BrowserFocusController._normalize_tab(raw)

        # Tenta carregar das configurações
        if load_settings is not None:
            try:
                settings = load_settings()
                return BrowserFocusController._normalize_tab(settings.averbacao_tab)
            except Exception:
                pass

        # Fallback para aba 4 (padrão para averbação)
        return 4

    @staticmethod
    def _resolve_preferred_title() -> str:
        return os.environ.get("MDF_BROWSER_TITLE_HINT", "").strip()

    @staticmethod
    def _normalize_taskbar_slot(value: Any) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return 1
        return min(numeric, 9) if numeric > 0 else 1

    @staticmethod
    def _resolve_taskbar_slot() -> int:
        raw = os.environ.get("MDF_BROWSER_TASKBAR_SLOT", "") or os.environ.get(
            "MDF_EDGE_TASKBAR_SLOT", ""
        )
        return BrowserFocusController._normalize_taskbar_slot(raw or 1)

    def _is_browser_window(self, window) -> bool:
        return self._matches_keywords(window, BROWSER_WINDOW_KEYWORDS)

    def _is_gui_window(self, window) -> bool:
        return self._matches_keywords(window, GUI_WINDOW_KEYWORDS)

    def _is_browser_active(self) -> bool:
        if not (title := self._active_window_title().lower()):
            return False
        return any(keyword in title for keyword in BROWSER_KEYWORDS_LOWER)

    def _active_window_title(self) -> str:
        if gw is not None:
            with contextlib.suppress(Exception):
                window = gw.getActiveWindow()
                if window and getattr(window, "title", None):
                    return str(window.title)
        if (
            _GetForegroundWindow is not None
            and _GetWindowTextLengthW is not None
            and _GetWindowTextW is not None
        ):
            with contextlib.suppress(Exception):
                if hwnd := _GetForegroundWindow():
                    length = _GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        _GetWindowTextW(hwnd, buffer, length + 1)
                        return buffer.value
        return ""

    def _matches_keywords(self, window, keywords: list[str]) -> bool:
        if lowered := self._window_title_lower(window):
            preferred = self._preferred_title.lower()
            if preferred and preferred in lowered:
                return True
            return any(keyword.lower() in lowered for keyword in keywords)
        return False

    def _window_title_lower(self, window) -> str:
        if gw is None or window is None:
            return ""
        with contextlib.suppress(Exception):
            title = getattr(window, "title", "") or ""
            return str(title).lower()
        return ""

    def _switch_to_target_tab(self) -> bool:
        if self._target_tab <= 0 or pyautogui is None:
            self._force_tab_on_focus = False
            return False

        with contextlib.suppress(Exception):
            time.sleep(0.5)  # Delay para garantir que a janela está ativa

            # Verifica se estamos em um workspace do Edge
            is_workspace = self._is_edge_workspace_active()

            if is_workspace:
                # Em workspaces, pode ser necessário usar Ctrl+Tab múltiplas vezes
                # ou ajustar a estratégia de navegação
                self._switch_tab_in_workspace()
            else:
                # Comportamento normal para Edge sem workspaces
                pyautogui.hotkey("ctrl", str(self._target_tab))

            time.sleep(0.15)
            self._force_tab_on_focus = False
            return True
        return False

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
            pyautogui.hotkey("win", str(self._taskbar_slot))
            self.taskbar_launched = True
            return True
        return False

    def _activate_browser_window(self, should_switch_tab: bool) -> bool:
        if self._activate_preferred_window(should_switch_tab):
            return True
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
                if self._activate_candidate_window(window, should_switch_tab):
                    return True

        if self._activate_via_winapi(should_switch_tab):
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

    def wait_until_browser_active(
        self,
        timeout: float = 1.6,
        poll_interval: float = 0.12,
        *,
        force_tab: Optional[bool] = None,
    ) -> bool:
        """Espera o navegador se tornar a janela em primeiro plano."""
        if gw is None:
            return True
        should_switch = (
            self._force_tab_on_focus if force_tab is None else bool(force_tab)
        )
        end_time = time.time() + max(0.0, timeout)
        while time.time() < end_time:
            if self._is_browser_window(self._get_active_window()):
                if should_switch:
                    self._switch_to_target_tab()
                return True
            time.sleep(max(0.01, poll_interval))
        success = self._is_browser_window(self._get_active_window())
        if success and should_switch:
            self._switch_to_target_tab()
        return success

    def switch_to_tab(
        self,
        tab: int,
        *,
        ensure_focus: bool = True,
        allow_taskbar: bool = True,
    ) -> bool:
        """Troca o navegador ativo para a aba informada, restaurando foco se necessário."""

        normalized = self._normalize_tab(tab)
        if normalized <= 0:
            self._force_tab_on_focus = False
            return False

        self._target_tab = normalized

        if ensure_focus:
            success = self.ensure_browser_focus(
                allow_taskbar=allow_taskbar,
                switch_to_target_tab=True,
                preserve_tab=False,
            )
            if success:
                self.wait_until_browser_active(force_tab=False)
            return success

        return self._switch_to_target_tab()

    def _activate_candidate_window(self, window, should_switch_tab: bool) -> bool:
        with contextlib.suppress(Exception):
            if getattr(window, "isMinimized", False):
                window.restore()
            # Garante que a janela esteja maximizada após a ativação
            if hasattr(window, "maximize"):
                window.maximize()
            window.activate()
            self._record_activation(window)
            time.sleep(0.25)
            if should_switch_tab:
                self._switch_to_target_tab()
            return True
        return False

    def _activate_preferred_window(self, should_switch_tab: bool) -> bool:
        if gw is None:
            return False
        hint = self._preferred_title.strip()
        if not hint:
            return False

        seen: set[int] = set()
        matches: list[object] = []
        with contextlib.suppress(Exception):
            matches = list(gw.getWindowsWithTitle(hint))
        if not matches:
            return False
        for window in matches:
            handle = getattr(window, "_hWnd", None)
            if isinstance(handle, int):
                if handle in seen:
                    continue
                seen.add(handle)
            if self._activate_candidate_window(window, should_switch_tab):
                return True
        return False

    # ------------------------------------------------------------------
    # Preferências
    # ------------------------------------------------------------------
    def list_window_titles(self) -> list[str]:
        titles: set[str] = set()
        if gw is None:
            return []
        with contextlib.suppress(Exception):
            for title in gw.getAllTitles():
                cleaned = str(title).strip()
                if not cleaned:
                    continue
                lowered = cleaned.lower()
                if any(keyword in lowered for keyword in BROWSER_KEYWORDS_LOWER):
                    titles.add(cleaned)
        return sorted(titles, key=str.casefold)

    def set_preferred_window_title(self, title: str) -> None:
        cleaned = title.strip()
        self._preferred_title = cleaned
        if cleaned:
            os.environ["MDF_BROWSER_TITLE_HINT"] = cleaned
        else:
            os.environ.pop("MDF_BROWSER_TITLE_HINT", None)

    def set_taskbar_slot(self, slot: int) -> None:
        normalized = self._normalize_taskbar_slot(slot)
        self._taskbar_slot = normalized
        os.environ["MDF_BROWSER_TASKBAR_SLOT"] = str(normalized)
        os.environ["MDF_EDGE_TASKBAR_SLOT"] = str(normalized)

    @property
    def preferred_window_title(self) -> str:
        return self._preferred_title

    def _record_activation(self, window) -> None:
        self.last_browser_window = window
        self.taskbar_launched = True

    def _activate_via_winapi(self, should_switch_tab: bool) -> bool:
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
                    _ShowWindow(hwnd, _SW_MAXIMIZE)
            if _SetForegroundWindow is not None:
                with contextlib.suppress(Exception):
                    if _SetForegroundWindow(hwnd):
                        if should_switch_tab:
                            self._switch_to_target_tab()
                        return True
            if _BringWindowToTop is not None:
                with contextlib.suppress(Exception):
                    _BringWindowToTop(hwnd)
                    if should_switch_tab:
                        self._switch_to_target_tab()
                    return True
        return False


    def _is_edge_workspace_active(self) -> bool:
        """Verifica se o Edge está usando workspaces baseado no título da janela."""
        if gw is None:
            return False

        try:
            active_window = gw.getActiveWindow()
            if active_window is None:
                return False

            title = str(active_window.title).lower()
            # Workspaces do Edge geralmente incluem indicadores como " - Workspaces"
            # ou outros marcadores específicos
            workspace_indicators = [
                "workspaces",
                "workspace",
                " - workspace",
                "workspace - "
            ]
            return any(indicator in title for indicator in workspace_indicators)
        except Exception:
            return False

    def _switch_tab_in_workspace(self) -> None:
        """Alterna para a aba alvo considerando workspaces do Edge."""
        # Em workspaces, a numeração pode ser diferente ou pode haver
        # necessidade de navegação adicional. Por enquanto, usa a mesma
        # lógica mas com verificações adicionais.

        # Primeiro tenta o método normal
        pyautogui.hotkey("ctrl", str(self._target_tab))
        time.sleep(0.2)

        # Verifica se a aba correta foi ativada (pode precisar de ajustes futuros)
        # Por enquanto, assume que funcionou


focus = BrowserFocusController()
__all__ = ["focus", "BrowserFocusController"]
# Exporta instâncias prontas para scripts legados.
