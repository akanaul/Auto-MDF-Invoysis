"""Mede desempenho do LogManager gerando um grande volume de linhas."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main(batch: int = 20_000) -> None:
    from app.log_manager import LogManager

    manager = LogManager()
    manager.start_session("stress-test")

    start = time.perf_counter()
    latencies: list[float] = []
    for index in range(batch):
        t0 = time.perf_counter()
        manager.append_line(
            f"[AutoMDF][INFO][{time.strftime('%H:%M:%S')}] Stress message {index}"
        )
        latencies.append(time.perf_counter() - t0)
    total = time.perf_counter() - start

    print(
        f"Mensagens: {batch} | Tempo total: {total:.3f}s | Latência média append: {sum(latencies) / len(latencies):.6f}s"
    )
    print("Aguardando 3s para flush assíncrono...")
    time.sleep(3)
    manager.shutdown(timeout=10.0)
    print("Shutdown solicitado e concluído.")

    logs_dir = PROJECT_ROOT / "logs"
    if logs_dir.exists() and (log_files := sorted(logs_dir.glob("*.log"))):
        latest = log_files[-1]
        size = latest.stat().st_size
        print(f"Arquivo gerado: {latest.name} ({size} bytes)")
        return
    print("Nenhum arquivo de log encontrado.")


if __name__ == "__main__":
    main()
