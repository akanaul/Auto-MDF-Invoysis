"""Recursos compartilhados de automação agrupados no pacote data."""

from typing import Any, cast

from .progress_manager import ProgressManager, track_progress

BrowserFocusController: Any
focus: Any

try:
    from .automation_focus import BrowserFocusController, focus
except ModuleNotFoundError:
    _FOCUS_DEPENDENCY_MESSAGE = "Dependências de automation_focus indisponíveis; instale os requisitos da GUI para usar os helpers de foco."

    class _BrowserFocusUnavailable:
        """Stub de fallback que lança exceção quando os helpers de foco não estão acessíveis."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise ModuleNotFoundError(_FOCUS_DEPENDENCY_MESSAGE)

    def _focus_unavailable(*_args: Any, **_kwargs: Any) -> None:
        raise ModuleNotFoundError(_FOCUS_DEPENDENCY_MESSAGE)

    BrowserFocusController = cast(Any, _BrowserFocusUnavailable)
    focus = cast(Any, _focus_unavailable)

__all__ = [
    "BrowserFocusController",
    "focus",
    "ProgressManager",
    "track_progress",
]
# Mantemos __all__ explícito para preservar a compatibilidade dos scripts.
