"""Launch the PySide6 Auto MDF control center."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = ROOT_DIR / "tools"
LOGS_DIR = ROOT_DIR / "logs"
VENV_DIR = ROOT_DIR / ".venv"
REQUIRED_GUI_MODULES = ("PySide6",)


@dataclass
class DependencyInstallationError(RuntimeError):
    message: str
    log_path: Path
    details: str = ""

    def __str__(self) -> str:  # pragma: no cover - formatting helper
        base = self.message
        if self.details:
            base = f"{base}\n\n{self.details}"
        base += f"\n\nArquivo de log: {self.log_path}"
        return base


def _missing_modules(modules: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for module in modules:
        try:
            importlib.import_module(module)
        except ModuleNotFoundError:
            missing.append(module)
    return missing


def _venv_python_path() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _ensure_virtualenv() -> Path:
    venv_python = _venv_python_path()
    if venv_python.exists():
        return venv_python

    VENV_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "startup-install.log"

    command = [sys.executable, "-m", "venv", str(VENV_DIR)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    log_path.write_text(
        "Comando: " + " ".join(command) + "\n" +
        "Código de saída: " + str(result.returncode) + "\n" +
        "--- STDOUT ---\n" + result.stdout +
        "\n--- STDERR ---\n" + result.stderr,
        encoding="utf-8",
    )

    if result.returncode != 0:
        raise DependencyInstallationError(
            "Não foi possível criar o ambiente virtual .venv.",
            log_path,
        )

    if not venv_python.exists():
        raise DependencyInstallationError(
            "Ambiente virtual criado, mas o interpretador não foi localizado.",
            log_path,
        )

    return venv_python


def _running_inside_venv() -> bool:
    return Path(sys.prefix).resolve() == VENV_DIR.resolve()


def _relaunch_inside_venv(venv_python: Path) -> None:
    args = [str(venv_python), str(ROOT_DIR / "AutoMDF-Start.py"), *sys.argv[1:]]
    os.execv(str(venv_python), args)


def _install_dependencies(python_executable: Path) -> Path:
    install_script = TOOLS_DIR / "install.py"
    if not install_script.exists():
        raise FileNotFoundError(f"Arquivo de instalação não encontrado: {install_script}")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "startup-install.log"

    command = [
        str(python_executable),
        str(install_script),
        "--mode",
        "venv",
        "--venv-path",
        str(VENV_DIR),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    log_path.write_text(
        "Comando: " + " ".join(command) + "\n" +
        "Código de saída: " + str(result.returncode) + "\n" +
        "--- STDOUT ---\n" + result.stdout +
        "\n--- STDERR ---\n" + result.stderr,
        encoding="utf-8",
    )

    if result.returncode != 0:
        details = []
        stderr_lower = result.stderr.lower()
        if "no matching distribution found for pyside6" in stderr_lower:
            details.append(
                "A versão atual do Python não possui builds compatíveis do PySide6. "
                "Instale Python 3.12 (ou 3.11/3.10) e execute novamente o instalador."
            )
        raise DependencyInstallationError(
            "Falha ao instalar dependências automaticamente.",
            log_path,
            "\n".join(details),
        )

    return log_path


def ensure_gui_dependencies(python_executable: Path) -> None:
    missing = _missing_modules(REQUIRED_GUI_MODULES)
    if not missing:
        return

    log_path = _install_dependencies(python_executable)

    if still_missing := _missing_modules(REQUIRED_GUI_MODULES):
        raise DependencyInstallationError(
            "Dependências críticas continuam ausentes após a instalação automática:",
            log_path,
            ", ".join(still_missing),
        )


def _show_startup_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:  # pragma: no cover - no GUI fallback
        print(message, file=sys.stderr)
        return

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Erro ao iniciar Auto MDF", message)
    root.destroy()


def main() -> int:
    """Start the PySide6 control center."""

    try:
        venv_python = _ensure_virtualenv()
    except DependencyInstallationError as exc:
        _show_startup_error(str(exc))
        return 1

    if not _running_inside_venv():
        try:
            _relaunch_inside_venv(venv_python)
        except Exception as exc:  # pragma: no cover - exec failure
            _show_startup_error(f"Não foi possível reiniciar dentro do ambiente virtual: {exc}")
            return 1
        return 0  # os.execv não retorna; este é apenas por segurança

    try:
        ensure_gui_dependencies(Path(sys.executable))
    except DependencyInstallationError as exc:
        _show_startup_error(str(exc))
        return 1
    except Exception as exc:  # pragma: no cover - unexpected failure
        _show_startup_error(f"Erro inesperado ao preparar o ambiente: {exc}")
        return 1

    from app import run

    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
