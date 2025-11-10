#!/usr/bin/env python3
"""Teste do tracing de linhas com simulação de prompt."""

import sys
import time
from pathlib import Path

# Adiciona o projeto ao path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.progress_manager import (
    ProgressManager,
)  # sourcery skip: module-level-import-not-at-top


def _print_progress(progress: ProgressManager, message: str) -> None:
    """Print current progress with a message."""
    print(message)
    print(
        f"Progress: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}"
    )


def _simulate_lines(progress: ProgressManager, count: int, prefix: str) -> None:
    """Simulate execution of lines with progress updates."""
    for i in range(count):
        time.sleep(0.5)
        print(f"{prefix} {i + 1}")
        _print_progress(
            progress,
            f"Progress: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}",
        )


def simulate_script_execution():
    """Simula a execução de um script com prompt."""
    print("=== TESTE DE TRACING DE LINHAS ===")
    print("Iniciando simulação de script com prompt...")

    progress = ProgressManager(auto_save=True)
    progress.start(total_steps=100)

    # Simula tracing manual (já que start_line_based_progress não existe)
    print("Simulando tracing manual...")

    # Simula execução antes do prompt
    print("Executando código antes do prompt...")
    _simulate_lines(progress, 5, "Linha simulada")

    # Simula prompt (que pode interferir com tracing)
    print("Simulando prompt - pode causar interrupção do tracing...")
    # Simula delay do prompt sem input real
    time.sleep(2)
    user_input = "simulado"
    print(f"Input simulado: {user_input}")
    _print_progress(
        progress,
        f"Progress após prompt: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}",
    )

    # Simula execução após o prompt
    print("Executando código após o prompt...")
    _simulate_lines(progress, 10, "Linha simulada após prompt")

    print("Simulação concluída!")
    _print_progress(
        progress,
        f"Progress final: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}",
    )
    time.sleep(2)  # Tempo para o tracing finalizar


if __name__ == "__main__":
    simulate_script_execution()
