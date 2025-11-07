"""Lightweight telemetry helpers for automation diagnostics."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

TELEMETRY_FILE = Path("logs/automation_telemetry.jsonl")
_TELEMETRY_DISABLED_VALUES = {"0", "false", "no"}


def _telemetry_enabled() -> bool:
    flag = os.environ.get("MDF_TELEMETRY_DISABLED", "").strip().lower()
    return flag not in _TELEMETRY_DISABLED_VALUES


def _ensure_destination() -> None:
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)


def record_event(event: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Persist a telemetry entry and return the structured payload."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "event": event,
        "details": details or {},
    }
    if not _telemetry_enabled():
        return entry
    try:
        _ensure_destination()
        with TELEMETRY_FILE.open("a", encoding="utf-8") as handle:
            json.dump(entry, handle, ensure_ascii=False)
            handle.write("\n")
    except Exception:
        # Telemetry must never break the main flow.
        return entry
    return entry
