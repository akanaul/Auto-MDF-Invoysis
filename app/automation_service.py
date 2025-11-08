"""High-level automation coordinator bridging GUI and runner."""

from __future__ import annotations

import contextlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from data.automation_settings import (
    AutomationSettings,
    apply_runtime_settings,
    SETTINGS_ENV_VARS,
    load_settings,
    save_settings,
)
from data.automation_telemetry import record_event
from data.progress_manager import ProgressManager

from .runner import ScriptRunner

try:  # pragma: no cover - optional dependency
    from data.automation_focus import focus
except ModuleNotFoundError:  # pragma: no cover
    focus = None  # type: ignore[assignment]


@dataclass
class AutomationRunConfig:
    script_path: Path
    tab_index: int
    window_hint: str
    taskbar_slot: int


class AutomationService(QObject):
    log_message = Signal(str)
    bridge_payload = Signal(dict)
    automation_started = Signal(Path)
    automation_finished = Signal(int)
    telemetry_event = Signal(dict)
    log_pause_request = Signal(bool)

    def __init__(
        self, python_executable: str, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._settings = load_settings()
        apply_runtime_settings(self._settings)
        self._apply_settings_environment()
        self._progress_file = Path(ProgressManager.DEFAULT_FILE_PATH)
        self._runner = ScriptRunner(python_executable, self)
        self._runner.log_message.connect(self.log_message)
        self._runner.bridge_payload.connect(self.bridge_payload)
        self._runner.process_started.connect(self._on_process_started)
        self._runner.process_finished.connect(self._on_process_finished)
        self._pending_config: Optional[AutomationRunConfig] = None

    @property
    def progress_file(self) -> Path:
        return self._progress_file

    @property
    def settings(self) -> AutomationSettings:
        return self._settings

    def update_settings(
        self, settings: AutomationSettings, *, persist: bool = True
    ) -> None:
        self._settings = settings
        apply_runtime_settings(settings)
        self._apply_settings_environment()
        persist_error: Exception | None = None
        if persist:
            try:
                save_settings(settings)
            except Exception as exc:  # pragma: no cover - best-effort persistence
                persist_error = exc
        details = settings.as_dict()
        details["persisted"] = persist_error is None
        entry = record_event("settings_updated", details)
        self.telemetry_event.emit(entry)
        if persist_error is not None:
            failure_entry = record_event(
                "settings_persist_failure",
                {"error": repr(persist_error)},
            )
            self.telemetry_event.emit(failure_entry)

    def start(self, config: AutomationRunConfig) -> bool:
        if self._runner.isRunning():
            return False
        self._pending_config = config
        self._prepare_environment(config)
        ProgressManager.reset(str(self._progress_file))
        started = self._runner.start_script(
            config.script_path, progress_file=self._progress_file
        )
        if not started:
            self._pending_config = None
            return False
        entry = record_event(
            "automation_requested",
            {
                "script": config.script_path.name,
                "tab_index": config.tab_index,
                "window_hint": config.window_hint,
            },
        )
        self.telemetry_event.emit(entry)
        return True

    def stop(self) -> None:
        self._runner.stop_script()

    def is_running(self) -> bool:
        return self._runner.isRunning()

    def wait(self, timeout_ms: Optional[int] = None) -> bool:
        if timeout_ms is None:
            return self._runner.wait()
        return self._runner.wait(timeout_ms)

    def send_bridge_response(self, value: str) -> None:
        self._runner.send_bridge_response(value)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_environment(self, config: AutomationRunConfig) -> None:
        os.environ["MDF_BROWSER_TAB"] = str(config.tab_index)
        if config.window_hint:
            os.environ["MDF_BROWSER_TITLE_HINT"] = config.window_hint
        else:
            os.environ.pop("MDF_BROWSER_TITLE_HINT", None)
        os.environ["MDF_BROWSER_TASKBAR_SLOT"] = str(config.taskbar_slot)
        os.environ["MDF_EDGE_TASKBAR_SLOT"] = str(config.taskbar_slot)
        self._apply_settings_environment()

        if focus is None:
            return
        with contextlib.suppress(Exception):
            focus.set_taskbar_slot(config.taskbar_slot)
            focus.prepare_for_execution()
            focus.target_tab = config.tab_index
            focus.set_preferred_window_title(config.window_hint)
            if not focus.ensure_browser_focus(allow_taskbar=True, preserve_tab=False):
                entry = record_event(
                    "focus_failure",
                    {
                        "script": config.script_path.name,
                        "window_hint": config.window_hint,
                    },
                )
                self.telemetry_event.emit(entry)
            else:
                record_event(
                    "focus_ready",
                    {
                        "script": config.script_path.name,
                        "window_hint": config.window_hint,
                    },
                )

    def _on_process_started(self, script_path: Path) -> None:
        entry = record_event("automation_started", {"script": script_path.name})
        self.telemetry_event.emit(entry)
        cfg = self._pending_config
        if cfg is not None and focus is not None:
            # Pause logging to avoid interference with focus operations
            self.log_pause_request.emit(True)
            try:
                # Give some time for the browser to start before attempting focus
                time.sleep(2.0)
                success = False
                attempts = max(1, int(self._settings.focus_retry_attempts))
                delay = max(0.1, float(self._settings.focus_retry_seconds))
                for _ in range(attempts):
                    with contextlib.suppress(Exception):
                        success = focus.ensure_browser_focus(
                            allow_taskbar=True, preserve_tab=False
                        )
                    if success:
                        break
                    time.sleep(delay)
                if not success:
                    entry = record_event(
                        "focus_retry_failed",
                        {"script": script_path.name, "attempts": attempts},
                    )
                    self.telemetry_event.emit(entry)
            finally:
                # Resume logging after focus attempt
                self.log_pause_request.emit(False)
        self.automation_started.emit(script_path)

    def _on_process_finished(self, exit_code: int) -> None:
        entry = record_event("automation_finished", {"exit_code": exit_code})
        self.telemetry_event.emit(entry)
        self._pending_config = None
        self.automation_finished.emit(exit_code)

    def _apply_settings_environment(self) -> None:
        for key in SETTINGS_ENV_VARS:
            os.environ.pop(key, None)
        for key, value in self._settings.to_environment().items():
            os.environ[key] = value
