#!/usr/bin/env python3
"""Teste do progresso em tempo real com salvamento."""

import sys
import time
import json
from pathlib import Path

# Adiciona o projeto ao path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.progress_manager import ProgressManager


def _check_progress_file(progress_file: Path, iteration: int) -> None:
    """Check and print progress file status."""
    if progress_file.exists():
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                percentage = data.get("percentage", 0)
                current_step = data.get("current_step", "")
                print(f"[{iteration}] Arquivo JSON: {percentage}% - {current_step}")
        except Exception as e:
            print(f"[{iteration}] Erro lendo JSON: {e}")
    else:
        print(f"[{iteration}] Arquivo JSON não existe: {progress_file}")


def test_realtime_save():
    """Testa se o progresso em tempo real está sendo salvo."""
    print("Testando salvamento de progresso em tempo real...")

    progress = ProgressManager(auto_save=False)
    progress.start(total_steps=100)
    print(f"Arquivo de progresso: {progress.progress_path}")

    # Verifica estado inicial
    print(f"Estado inicial: {progress.progress_data.get('percentage', 0)}%")

    # Simula progresso manual para teste (já que start_realtime_progress não existe)
    print("Simulando progresso manual para teste...")
    for i in range(10):
        progress.update(i * 10, f"Passo {i + 1}")
        time.sleep(0.5)

    print("Aguardando 2 segundos para estabilização...")
    time.sleep(2)

    print("Aguardando atualizações automáticas...")
    print("Verificando arquivo JSON a cada 3 segundos...")

    progress_file = Path(progress.progress_path)

    for i in range(6):
        time.sleep(3)
        _check_progress_file(progress_file, i + 1)

    print("Teste concluído!")


if __name__ == "__main__":
    test_realtime_save()
