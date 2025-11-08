#!/usr/bin/env python3
"""Verifica manualmente o controle de foco do navegador."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run() -> bool:
    from data.automation_focus import BrowserFocusController

    focus = BrowserFocusController()

    print("== Diagnóstico do foco do navegador ==")
    print(f"Aba alvo configurada: {focus._target_tab}")  # noqa: SLF001
    print(f"Título preferido: {focus._preferred_title!r}")  # noqa: SLF001

    print("\nForçando foco...")
    success = focus.ensure_browser_focus(allow_taskbar=True, preserve_tab=False)
    print(f"Resultado: {'✓' if success else '✗'}")

    if success:
        print("Foco restaurado com sucesso.")
    else:
        print(
            "Não foi possível focar o navegador. Verifique as palavras-chave configuradas."
        )
    return success


if __name__ == "__main__":
    os.environ.setdefault("MDF_BROWSER_TITLE_HINT", "Microsoft Edge")
    run()
