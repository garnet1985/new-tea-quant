#!/usr/bin/env python3
"""Sequential renew for large tables; log to /tmp/ntq_large_renew*.log."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLES = ["stock_klines", "stock_indicators", "stock_moneyflow"]
LOG = Path("/tmp/ntq_large_renew.log")
SUMMARY = Path("/tmp/ntq_large_renew_summary.log")


def main() -> int:
    SUMMARY.write_text("")
    with LOG.open("w") as log:
        log.write(f"started {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.flush()
        for table in TABLES:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"===== START {table} {stamp} =====", flush=True)
            log.write(f"===== START {table} {stamp} =====\n")
            log.flush()
            t0 = time.time()
            proc = subprocess.run(
                [str(ROOT / "venv" / "bin" / "python"), "cli.py", "r", table],
                cwd=str(ROOT),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            dt = time.time() - t0
            status = "OK" if proc.returncode == 0 else f"FAIL({proc.returncode})"
            line = f"{status}\t{dt:.1f}s\t{table}\t{time.strftime('%Y-%m-%d %H:%M:%S')}"
            print(f"===== END {line} =====", flush=True)
            log.write(f"===== END {line} =====\n")
            log.flush()
            with SUMMARY.open("a") as s:
                s.write(line + "\n")
        print("ALL DONE", flush=True)
        log.write("ALL DONE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
