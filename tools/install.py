"""Unified dependency installer for Auto MDF InvoISys.

This helper script centralises dependency installation logic for Windows,
Linux, GitHub Codespaces and the in-app installer. It can operate in three
modes:

* venv  - Create (or reuse) a virtual environment and install requirements.
* user  - Install requirements in the current user's site-packages.
* system - Install requirements in the active Python environment.

The script is safe to call multiple times; it will reuse the chosen target
environment when possible and always upgrades pip tooling first.
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

ROOT_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"
DEFAULT_VENV = ROOT_DIR / ".venv"


def is_windows() -> bool:
    return os.name == "nt"


def is_codespaces() -> bool:
    # GitHub Codespaces sets either CODESPACES or CODESPACE_NAME
    return any(os.environ.get(name) for name in ("CODESPACES", "CODESPACE_NAME", "GITHUB_CODESPACES"))


def run_command(command: Sequence[str]) -> None:
    print(f"\n> {' '.join(command)}")
    subprocess.run(command, check=True)


def ensure_virtualenv(python_executable: Path, venv_path: Path) -> Path:
    if not venv_path.exists():
        print(f"Criando ambiente virtual em {venv_path}...")
        run_command([str(python_executable), "-m", "venv", str(venv_path)])
    else:
        print(f"Ambiente virtual encontrado em {venv_path}.")

    if is_windows():
        venv_python = venv_path / "Scripts" / "python.exe"
    else:
        venv_python = venv_path / "bin" / "python"

    if not venv_python.exists():
        raise FileNotFoundError(f"Python do virtualenv nao localizado: {venv_python}")
    return venv_python


def upgrade_tooling(python_executable: Path, *, extra_args: Iterable[str] = ()) -> None:
    run_command([
        str(python_executable),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "setuptools",
        "wheel",
        *extra_args,
    ])


def install_requirements(python_executable: Path, *, extra_args: Iterable[str] = ()) -> None:
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"Arquivo requirements nao encontrado: {REQUIREMENTS_FILE}")
    run_command([
        str(python_executable),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "-r",
        str(REQUIREMENTS_FILE),
        *extra_args,
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Instalador de dependencias do Auto MDF InvoISys")
    parser.add_argument(
        "--mode",
        choices=("venv", "user", "system"),
        default="venv",
        help="Modo de instalacao: venv (padrao), user ou system.",
    )
    parser.add_argument(
        "--venv-path",
        default=str(DEFAULT_VENV),
        help="Caminho do ambiente virtual a ser criado/reutilizado (modo venv).",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python base utilizado para criar o ambiente virtual.",
    )
    parser.add_argument(
        "--pip-extra",
        nargs=argparse.REMAINDER,
        help="Argumentos extras encaminhados ao pip (apos --).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pip_extra = tuple(args.pip_extra or ())

    base_python = Path(args.python)
    if not base_python.exists():
        raise FileNotFoundError(f"Python base nao encontrado: {base_python}")

    print("========================================")
    print(" Instalador de dependencias - Auto MDF ")
    print("========================================\n")
    print(f"Sistema operacional : {platform.system()} {platform.release()}")
    print(f"Python base         : {base_python}")
    print(f"Modo selecionado    : {args.mode}")
    if is_codespaces():
        print("Contexto             : GitHub Codespaces detectado")

    try:
        if args.mode == "venv":
            venv_path = Path(args.venv_path).resolve()
            venv_python = ensure_virtualenv(base_python, venv_path)
            upgrade_tooling(venv_python, extra_args=pip_extra)
            install_requirements(venv_python, extra_args=pip_extra)
            print(f"\nAmbiente virtual pronto em {venv_path}")
            print("Para ativar:")
            if is_windows():
                print(f"    {venv_path / 'Scripts' / 'activate.bat'}")
            else:
                print(f"    source {venv_path / 'bin' / 'activate'}")
        elif args.mode == "user":
            upgrade_tooling(base_python, extra_args=pip_extra)
            install_requirements(base_python, extra_args=("--user", *pip_extra))
            print("\nDependencias instaladas no escopo do usuario.")
        else:  # system
            upgrade_tooling(base_python, extra_args=pip_extra)
            install_requirements(base_python, extra_args=pip_extra)
            print("\nDependencias instaladas no ambiente atual.")
    except subprocess.CalledProcessError as exc:
        print(f"\nFalha ao instalar dependencias (codigo {exc.returncode}).")
        return exc.returncode
    except Exception as exc:  # pragma: no cover - best effort logging
        print(f"\nErro inesperado: {exc}")
        return 1

    print("\nInstalacao concluida com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
