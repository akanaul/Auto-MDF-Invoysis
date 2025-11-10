"""Valida serialização e restauração de AutomationSettings usando um arquivo temporário."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Iterator

# Ensure the project root is in sys.path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@contextmanager
def _automation_settings_module(tmp_path: Path) -> Iterator[ModuleType]:
    original_env = os.environ.get("MDF_SETTINGS_FILE")
    if original_env is None:
        os.environ.pop("MDF_SETTINGS_FILE", None)
    os.environ["MDF_SETTINGS_FILE"] = str(tmp_path)

    sys.modules.pop("data.automation_settings", None)
    module = importlib.import_module("data.automation_settings")
    try:
        yield module
    finally:
        if original_env is None:
            os.environ.pop("MDF_SETTINGS_FILE", None)
        else:
            os.environ["MDF_SETTINGS_FILE"] = original_env
        sys.modules.pop("data.automation_settings", None)
        importlib.import_module("data.automation_settings")


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "automation_settings.json"
        with _automation_settings_module(tmp_path) as settings_module:
            AutomationSettings = settings_module.AutomationSettings
            save_settings = settings_module.save_settings
            load_settings = settings_module.load_settings

            original = AutomationSettings(
                pyautogui_pause=0.8,
                pyautogui_failsafe=True,
                focus_retry_seconds=5.0,
                focus_retry_attempts=3,
                pyautogui_minimum_sleep=0.05,
                sleep_threshold_short=0.25,
                sleep_threshold_medium=0.9,
                sleep_scale_short=1.2,
                sleep_scale_medium=1.1,
                sleep_scale_long=1.3,
                use_default_timers=False,
            )

            print("Persistindo configurações temporárias...")
            save_settings(original)

            restored = load_settings()

            equal = original.as_dict() == restored.as_dict()
            print(f"Round-trip bem sucedido: {'✓' if equal else '✗'}")
            if not equal:
                print("Diferenças detectadas:")
                for key, value in original.as_dict().items():
                    if value != getattr(restored, key):
                        print(
                            f"  {key}: esperado {value!r}, obtido {getattr(restored, key)!r}"
                        )


if __name__ == "__main__":
    run()
