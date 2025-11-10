#!/usr/bin/env python3
"""Teste do tracing de linhas com simulação de prompt."""

import sys
import time
from pathlib import Path

# Adiciona o projeto ao path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.progress_manager import ProgressManager
from data.script_runtime import start_line_based_progress

def simulate_script_execution():
    """Simula a execução de um script com prompt."""
    print("=== TESTE DE TRACING DE LINHAS ===")
    print("Iniciando simulação de script com prompt...")

    progress = ProgressManager(auto_save=True)
    progress.start(total_steps=100)

    # Inicia tracing
    print("Ativando tracing de linhas...")
    start_line_based_progress(progress, __file__)

    # Simula execução antes do prompt
    print("Executando código antes do prompt...")
    for i in range(5):
        time.sleep(0.5)
        print(f"Linha simulada {i+1}")
        print(f"Progress: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}")

    # Simula prompt (que pode interferir com tracing)
    print("Simulando prompt - pode causar interrupção do tracing...")
    # Simula delay do prompt sem input real
    time.sleep(2)
    user_input = "simulado"
    print(f"Input simulado: {user_input}")
    print(f"Progress após prompt: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}")

    # Simula execução após o prompt
    print("Executando código após o prompt...")
    for i in range(10):
        time.sleep(0.5)
        print(f"Linha simulada após prompt {i+1}")
        print(f"Progress: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}")

    print("Simulação concluída!")
    print(f"Progress final: {progress.progress_data['percentage']}% - {progress.progress_data['current_step']}")
    time.sleep(2)  # Tempo para o tracing finalizar

if __name__ == "__main__":
    simulate_script_execution()