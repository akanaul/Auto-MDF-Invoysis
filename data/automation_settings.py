"""Persistence helpers for automation runtime settings."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


_SETTINGS_ENV_VAR = "MDF_SETTINGS_FILE"
_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_SETTINGS_PATH = _MODULE_DIR / "automation_settings.json"


SETTINGS_ENV_VARS: tuple[str, ...] = (
    "MDF_PYAUTOGUI_PAUSE",
    "MDF_PYAUTOGUI_MIN_SLEEP",
    "MDF_SLEEP_THRESHOLD_SHORT",
    "MDF_SLEEP_THRESHOLD_MEDIUM",
    "MDF_SLEEP_SCALE_SHORT",
    "MDF_SLEEP_SCALE_MEDIUM",
    "MDF_SLEEP_SCALE_LONG",
)


def _candidate_paths() -> list[Path]:
    """Return ordered candidate paths for persisting settings."""

    candidates: list[Path] = []

    if env_value := os.environ.get(_SETTINGS_ENV_VAR):
        candidates.append(Path(env_value).expanduser())

    candidates.append(_DEFAULT_SETTINGS_PATH)

    if appdata := os.environ.get("APPDATA"):
        candidates.append(Path(appdata) / "AutoMDF" / "automation_settings.json")

    candidates.append(Path.home() / ".auto_mdf" / "automation_settings.json")

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen or not key:
            continue
        seen.add(key)
        unique.append(path)
    return unique


_CANDIDATE_PATHS = _candidate_paths()


def _initial_settings_path() -> Path:
    for path in _CANDIDATE_PATHS:
        try:
            if path.exists():
                return path
        except OSError:
            continue
    return _CANDIDATE_PATHS[0]


_settings_path: Path = _initial_settings_path()


@dataclass
class AutomationSettings:
    pyautogui_pause: float = 0.5
    pyautogui_failsafe: bool = True
    focus_retry_seconds: float = 8.0
    focus_retry_attempts: int = 2
    pyautogui_minimum_sleep: float = 0.02
    sleep_threshold_short: float = 0.35
    sleep_threshold_medium: float = 1.2
    sleep_scale_short: float = 1.0
    sleep_scale_medium: float = 1.0
    sleep_scale_long: float = 1.0
    use_default_timers: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutomationSettings":
        if not isinstance(data, dict):
            return cls()
        allowed = {field.name for field in fields(cls)}
        values = {key: data[key] for key in allowed if key in data}
        values["pyautogui_failsafe"] = True
        return cls(**values)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_environment(self) -> Dict[str, str]:
        if self.use_default_timers:
            return {}
        short_threshold = max(0.0, float(self.sleep_threshold_short))
        medium_threshold = max(
            short_threshold + 0.01, float(self.sleep_threshold_medium)
        )

        return {
            "MDF_PYAUTOGUI_PAUSE": f"{max(0.0, float(self.pyautogui_pause)):.4f}",
            "MDF_PYAUTOGUI_MIN_SLEEP": f"{max(0.0, float(self.pyautogui_minimum_sleep)):.4f}",
            "MDF_SLEEP_THRESHOLD_SHORT": f"{short_threshold:.4f}",
            "MDF_SLEEP_THRESHOLD_MEDIUM": f"{medium_threshold:.4f}",
            "MDF_SLEEP_SCALE_SHORT": f"{max(0.0, float(self.sleep_scale_short)):.4f}",
            "MDF_SLEEP_SCALE_MEDIUM": f"{max(0.0, float(self.sleep_scale_medium)):.4f}",
            "MDF_SLEEP_SCALE_LONG": f"{max(0.0, float(self.sleep_scale_long)):.4f}",
        }


def _paths_in_priority_order() -> Iterable[Path]:
    yielded: set[str] = set()
    for path in (_settings_path, *_CANDIDATE_PATHS):
        key = str(path)
        if not key or key in yielded:
            continue
        yielded.add(key)
        yield path


def load_settings() -> AutomationSettings:
    global _settings_path

    for path in _paths_in_priority_order():
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError):
            continue
        _settings_path = path
        settings = AutomationSettings.from_dict(raw)
        settings.sleep_threshold_medium = max(
            settings.sleep_threshold_medium,
            settings.sleep_threshold_short + 0.01,
        )
        return settings

    _settings_path = _CANDIDATE_PATHS[0]
    settings = AutomationSettings()
    settings.sleep_threshold_medium = max(
        settings.sleep_threshold_medium,
        settings.sleep_threshold_short + 0.01,
    )
    return settings


def save_settings(settings: AutomationSettings) -> None:
    global _settings_path

    payload = settings.as_dict()
    last_error: Exception | None = None

    for path in _paths_in_priority_order():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            last_error = exc
            continue
        _settings_path = path
        return

    if last_error is not None:
        raise last_error


_ORIGINAL_PYAUTOGUI_PAUSE: Optional[float] = None
_ORIGINAL_PYAUTOGUI_MIN_SLEEP: Optional[float] = None


def apply_runtime_settings(settings: AutomationSettings) -> None:
    try:
        import pyautogui  # type: ignore
    except Exception:
        return
    global _ORIGINAL_PYAUTOGUI_PAUSE, _ORIGINAL_PYAUTOGUI_MIN_SLEEP
    if _ORIGINAL_PYAUTOGUI_PAUSE is None:
        try:
            _ORIGINAL_PYAUTOGUI_PAUSE = float(pyautogui.PAUSE)
        except (AttributeError, TypeError, ValueError):
            _ORIGINAL_PYAUTOGUI_PAUSE = None
    if _ORIGINAL_PYAUTOGUI_MIN_SLEEP is None and hasattr(pyautogui, "MINIMUM_SLEEP"):
        try:
            _ORIGINAL_PYAUTOGUI_MIN_SLEEP = float(getattr(pyautogui, "MINIMUM_SLEEP"))
        except (AttributeError, TypeError, ValueError):
            _ORIGINAL_PYAUTOGUI_MIN_SLEEP = None
    pause = max(0.0, float(settings.pyautogui_pause))
    fail_safe = bool(settings.pyautogui_failsafe)
    pyautogui.FAILSAFE = fail_safe
    if settings.use_default_timers:
        if _ORIGINAL_PYAUTOGUI_PAUSE is not None:
            pyautogui.PAUSE = _ORIGINAL_PYAUTOGUI_PAUSE
        if _ORIGINAL_PYAUTOGUI_MIN_SLEEP is not None and hasattr(
            pyautogui, "MINIMUM_SLEEP"
        ):
            setattr(
                pyautogui,
                "MINIMUM_SLEEP",
                max(0.0, float(_ORIGINAL_PYAUTOGUI_MIN_SLEEP)),
            )
    else:
        pyautogui.PAUSE = pause
        if hasattr(pyautogui, "MINIMUM_SLEEP"):
            setattr(
                pyautogui,
                "MINIMUM_SLEEP",
                max(0.0, float(settings.pyautogui_minimum_sleep)),
            )
