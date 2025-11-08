"""Gera um arquivo de progresso temporário para inspecionar o JSON produzido pelo ProgressManager."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def _progress_env() -> Iterator[Path]:
    original_env = os.environ.get("MDF_PROGRESS_FILE")
    with tempfile.TemporaryDirectory() as tmp:
        progress_path = Path(tmp) / "progress.json"
        os.environ["MDF_PROGRESS_FILE"] = str(progress_path)
        try:
            yield progress_path
        finally:
            if original_env is None:
                os.environ.pop("MDF_PROGRESS_FILE", None)
            else:
                os.environ["MDF_PROGRESS_FILE"] = original_env


def run() -> None:
    from data.progress_manager import ProgressManager

    with _progress_env() as progress_path:
        manager = ProgressManager()
        manager.start(total_steps=5)
        manager.update(20, "Preparando ambiente", step_number=1)
        manager.add_log("Ambiente preparado")
        manager.update(60, "Executando automação", step_number=3)
        manager.add_warning("Processo um pouco lento, monitorando...")
        manager.update(100, "Concluído", step_number=5)
        manager.complete("Execução concluída com sucesso")

        print(f"Arquivo de progresso gerado em: {progress_path}")
        print(progress_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    run()
