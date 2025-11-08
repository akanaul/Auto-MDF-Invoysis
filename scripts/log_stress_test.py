"""Stress test for LogManager.

Run this script from the repository root. It will create a LogManager,
start a session, and enqueue N log lines quickly to measure append latency
and total throughput. At the end it will call shutdown() to flush to disk.

Usage (PowerShell):
    python ./scripts/log_stress_test.py
"""
from __future__ import annotations

import time
from pathlib import Path

# ensure project root is on sys.path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.log_manager import LogManager


def main() -> None:
    mgr = LogManager()
    mgr.start_session("stress-test")
    N = 20000
    start = time.perf_counter()
    latencies = []
    for i in range(N):
        t0 = time.perf_counter()
        mgr.append_line(f"[AutoMDF][INFO][{time.strftime('%H:%M:%S')}] Stress message {i}")
        latencies.append(time.perf_counter() - t0)
    total = time.perf_counter() - start
    print(f"Enqueued {N} messages in {total:.3f}s — avg append latency {sum(latencies)/len(latencies):.6f}s")

    # Give some time for background writer to flush, then request shutdown
    print("Waiting 3s for background flush...")
    time.sleep(3)
    mgr.shutdown(timeout=10.0)
    print("Shutdown requested and writer joined (if possible).")
    logs_dir = Path('logs')
    latest = None
    if logs_dir.exists():
        files = sorted(logs_dir.glob('*.log'))
        if files:
            latest = files[-1]
    if latest:
        print(f"Wrote log file: {latest} ({latest.stat().st_size} bytes)")
    else:
        print("No log file found.")


if __name__ == '__main__':
    main()
