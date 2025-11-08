"""Executa compileall nas pastas principais para flagrar erros de sintaxe rapidamente."""

from __future__ import annotations

import compileall
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGETS = [PROJECT_ROOT / "app", PROJECT_ROOT / "data"]


def run() -> None:
    print("== Smoke de compilação ==")
    success = True
    for target in TARGETS:
        print(f"Compilando {target.relative_to(PROJECT_ROOT)}...")
        if not compileall.compile_dir(target, quiet=1, force=True):
            success = False
            print(f"✗ Falha ao compilar {target}")
        else:
            print(f"✓ {target} OK")
    if success:
        print("Todos os módulos foram compilados sem erros.")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
