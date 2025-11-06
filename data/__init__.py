"""Shared automation resources bundled under the data package."""

from typing import Any, cast

from .progress_manager import ProgressManager, track_progress

BrowserFocusController: Any
focus: Any

try:
    from .automation_focus import BrowserFocusController, focus
except ModuleNotFoundError:
    _FOCUS_DEPENDENCY_MESSAGE = (
        "automation_focus dependencies are not available; install GUI requirements to use focus helpers."
    )

    class _BrowserFocusUnavailable:
        """Fallback stub that raises when automation focus helpers are missing."""

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
