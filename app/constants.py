"""Shared constants for the modern Auto MDF GUI."""

from __future__ import annotations

import os
from pathlib import Path

BRIDGE_PREFIX = os.environ.get("MDF_BRIDGE_PREFIX", "__MDF_GUI_BRIDGE__")
BRIDGE_ACK = os.environ.get("MDF_BRIDGE_ACK", "__MDF_GUI_ACK__")
BRIDGE_CANCEL = os.environ.get("MDF_BRIDGE_CANCEL", "__MDF_GUI_CANCEL__")

APP_POLL_INTERVAL_MS = 200
PROGRESS_REFRESH_INTERVAL_MS = 200
LOG_MAX_LINES = 1200

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
LOGS_DIR = ROOT_DIR / "logs"
