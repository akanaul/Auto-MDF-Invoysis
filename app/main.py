"""Application entry point for the PySide6 Auto MDF control center.

Guia de edição (resumido)
- Modificável pelo usuário:
    - Parâmetros de execução (ex.: caminho do interpretador passado a `run`).
- Requer atenção:
    - Alterações no fluxo de inicialização do QApplication ou variáveis de ambiente podem afetar toda a UI.
- Apenas para devs:
    - Mudanças em inicialização profunda do Qt, gerenciamento de eventos e integração com o loop principal.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def _configure_qt_environment() -> None:
    """Aplica ajustes básicos de ambiente Qt antes de criar a aplicação."""
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


def run(python_executable: Optional[str] = None) -> int:
    """Inicia a janela do centro de controle Auto MDF.

    Parâmetros
    ----------
    python_executable:
        Caminho do interpretador usado ao iniciar os scripts de automação. Por
        padrão usa o interpretador atual.
    """

    app = QApplication.instance()
    owns_app = app is None

    if owns_app:
        _configure_qt_environment()
        app = QApplication(sys.argv)

    assert app is not None  # For type checkers
    interpreter = python_executable or sys.executable
    window = MainWindow(interpreter)
    app.setProperty("auto_mdf_main_window", window)
    window.show()
    window.raise_()

    return app.exec() if owns_app else 0


def main() -> int:
    """Ponto de entrada quando executado via console."""

    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
