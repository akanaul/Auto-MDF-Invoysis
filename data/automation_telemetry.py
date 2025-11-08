"""Utilitários leves de telemetria para diagnósticos da automação."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TELEMETRY_FILE = Path("logs/automation_telemetry.jsonl")
_TELEMETRY_DISABLED_VALUES = {"0", "false", "no"}


def _telemetry_enabled() -> bool:
    flag = os.environ.get("MDF_TELEMETRY_DISABLED", "").strip().lower()
    return flag not in _TELEMETRY_DISABLED_VALUES


def _ensure_destination() -> None:
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)


def record_event(event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persiste um registro de telemetria e retorna o payload estruturado."""
    timestamp = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    entry = {
        "timestamp": timestamp,
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
        # Telemetria não deve interromper o fluxo principal.
        return entry
    return entry
