#!/usr/bin/env python3
"""Teste simples da função start_realtime_progress."""

import sys
import time
from pathlib import Path

# Adiciona o projeto ao path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.progress_manager import ProgressManager
from data.script_runtime import start_realtime_progress

def test_realtime_progress():
    """Testa a função de progresso em tempo real."""
    print("Iniciando teste de progresso em tempo real...")

    progress = ProgressManager(auto_save=False)
    progress.start(total_steps=100)

    # Inicia progresso em tempo real (10 segundos para teste)
    start_realtime_progress(progress, estimated_duration=10)

    print("Aguardando progresso automático...")
    time.sleep(3)

    # Simula um checkpoint manual
    progress.update(30, "Checkpoint manual", force_save=True)
    print("Checkpoint manual definido")

    time.sleep(3)

    # Simula outro checkpoint
    progress.update(60, "Segundo checkpoint", force_save=True)
    print("Segundo checkpoint definido")

    time.sleep(4)

    print("Teste concluído!")
    print(f"Progresso final: {progress.progress_data.get('percentage', 0)}%")

if __name__ == "__main__":
    test_realtime_progress()