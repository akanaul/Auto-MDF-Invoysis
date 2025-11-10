"""Launch the PySide6 Auto MDF control center."""

from __future__ import annotations

import contextlib
import importlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

ROOT_DIR = Path(__file__).resolve().parent
INSTALL_DIR = ROOT_DIR / "install"
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
        pythonw = VENV_DIR / "Scripts" / "pythonw.exe"
        if pythonw.exists():
            return pythonw
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
        "Comando: "
        + " ".join(command)
        + "\n"
        + "Código de saída: "
        + str(result.returncode)
        + "\n"
        + "--- STDOUT ---\n"
        + result.stdout
        + "\n--- STDERR ---\n"
        + result.stderr,
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


MANUAL_INSTALL_HINT = (
    "Para tentar novamente manualmente:\n"
    "  1. Abra a pasta 'install' na raiz do projeto.\n"
    "  2. No Windows, execute 'install\\install.bat' (ambiente .venv) ou 'install\\install_user.bat'.\n"
    "  3. Após concluir, execute novamente o AutoMDF-Start."
)


def _build_install_error_details(stdout_combined: str) -> list[str]:
    details = []
    if "no matching distribution found for pyside6" in stdout_combined:
        details.append(
            "A versão atual do Python não possui builds compatíveis do PySide6. "
            "Instale Python 3.12 (ou 3.11/3.10) e execute novamente o instalador."
        )
    return details


def _build_missing_modules_details(missing_modules: list[str]) -> str:
    return ", ".join(missing_modules) + "\n\n" + MANUAL_INSTALL_HINT


def _install_dependencies(python_executable: Path) -> Path:
    install_script = INSTALL_DIR / "install.py"
    if not install_script.exists():
        raise FileNotFoundError(
            f"Arquivo de instalação não encontrado: {install_script}"
        )

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "startup-install.log"

    command = [
        str(python_executable),
        "-u",
        str(install_script),
        "--mode",
        "venv",
        "--venv-path",
        str(VENV_DIR),
    ]

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    print("Iniciando instalação automática das dependências...", flush=True)

    log_lines: list[str] = []

    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    ) as process:
        assert process.stdout is not None
        for raw_line in process.stdout:
            sys.stdout.write(raw_line)
            sys.stdout.flush()
            log_lines.append(raw_line)
        returncode = process.wait()

    _write_install_log(log_path, command, log_lines, returncode)

    if returncode != 0:
        stdout_combined = "".join(log_lines).lower()
        details = _build_install_error_details(stdout_combined)
        print(
            "\nA instalação automática falhou. Consulte o log e siga as instruções abaixo:",
            flush=True,
        )
        print(f"  - Log: {log_path}", flush=True)
        print(MANUAL_INSTALL_HINT, flush=True)
        details.append(MANUAL_INSTALL_HINT)
        raise DependencyInstallationError(
            "Falha ao instalar dependências automaticamente.",
            log_path,
            "\n".join(details),
        )

    print("Instalação automática concluída com sucesso.\n", flush=True)
    return log_path


def _write_install_log(
    log_path: Path, command: list[str], lines: list[str], returncode: Optional[int]
) -> None:
    quoted_command = " ".join(
        f'"{part}"' if " " in str(part) else str(part) for part in command
    )
    header = [
        f"Comando: {quoted_command}",
        f"Código de saída: {'' if returncode is None else returncode}",
        "--- STDOUT/STDERR ---",
    ]
    log_payload = "\n".join(header) + "\n" + "".join(lines)

    with contextlib.suppress(Exception):
        log_path.write_text(log_payload, encoding="utf-8")


def ensure_gui_dependencies(python_executable: Path) -> None:
    missing = _missing_modules(REQUIRED_GUI_MODULES)
    if not missing:
        return

    print("Dependências críticas ausentes: " + ", ".join(missing), flush=True)
    print("Executando instalação automática via pip...", flush=True)

    log_path = _install_dependencies(python_executable)

    print(f"Logs da instalação gravados em: {log_path}", flush=True)

    if still_missing := _missing_modules(REQUIRED_GUI_MODULES):
        print(
            "Instalação automática concluída, mas ainda faltam dependências críticas.",
            flush=True,
        )
        print(MANUAL_INSTALL_HINT, flush=True)
        details = _build_missing_modules_details(still_missing)
        raise DependencyInstallationError(
            "Dependências críticas continuam ausentes após a instalação automática:",
            log_path,
            details,
        )


def _show_startup_error(message: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except Exception:  # pragma: no cover - no GUI fallback
        print(message, file=sys.stderr)
        return

    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication([])
        owns_app = True

    box = QMessageBox()
    box.setWindowTitle("Erro ao iniciar Auto MDF")
    box.setIcon(QMessageBox.Icon.Critical)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()

    if owns_app:
        app.quit()


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
            _show_startup_error(
                f"Não foi possível reiniciar dentro do ambiente virtual: {exc}"
            )
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
