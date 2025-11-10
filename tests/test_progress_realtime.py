#!/usr/bin/env python3
"""Test script for real-time progress updates."""

import time
from data.progress_manager import ProgressManager
from data.script_runtime import update_progress_realtime

def _run_progress_test(pm: ProgressManager) -> None:
    """Run the progress test loop."""
    for i in range(101):  # 0 to 100
        update_progress_realtime(pm, i, f"Step {i}")  # Atualização em tempo real
        print(f"Progress: {i}%")
        time.sleep(0.02)  # Simular trabalho rápido para teste

        if i % 10 == 0:  # Salvar checkpoint a cada 10%
            pm.save_checkpoint()
            print(f"Checkpoint saved at {i}%")

def test_realtime_progress():
    """Test real-time progress updates with 1% increments."""
    pm = ProgressManager(auto_save=False)  # Não salvar automaticamente
    pm.start(total_steps=100)

    print("Starting real-time progress test...")

    _run_progress_test(pm)

    pm.complete("Test completed successfully")

if __name__ == "__main__":
    test_realtime_progress()