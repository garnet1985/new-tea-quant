"""Simple stderr/stdout progress lines for long BE perf steps."""
from __future__ import annotations

import sys
import time
from typing import Optional


def log(msg: str) -> None:
    print(msg, flush=True)


def step(phase: str, msg: str) -> None:
    print(f"[{phase}] {msg}", flush=True)


class Progress:
    """Periodic progress reporter."""

    def __init__(
        self,
        phase: str,
        total: int,
        *,
        unit: str = "items",
        every_n: Optional[int] = None,
        every_sec: float = 2.0,
    ) -> None:
        self.phase = phase
        self.total = max(0, int(total))
        self.unit = unit
        self.every_n = every_n
        if self.every_n is None and self.total > 0:
            # ~20 updates, at least every 1 item
            self.every_n = max(1, self.total // 20)
        elif self.every_n is None:
            self.every_n = 1
        self.every_sec = float(every_sec)
        self.done = 0
        self._t0 = time.perf_counter()
        self._last_t = self._t0
        self._last_done = 0

    def update(self, n: int = 1, *, force: bool = False) -> None:
        self.done += int(n)
        now = time.perf_counter()
        by_count = self.done == self.total or self.done % self.every_n == 0
        by_time = (now - self._last_t) >= self.every_sec
        if not force and not by_count and not by_time:
            return
        elapsed = max(1e-6, now - self._t0)
        rate = self.done / elapsed
        if self.total > 0:
            pct = 100.0 * self.done / self.total
            remain = max(0.0, (self.total - self.done) / rate) if rate > 0 else 0.0
            print(
                f"[{self.phase}] {self.done:,}/{self.total:,} {self.unit} "
                f"({pct:.1f}%)  {rate:,.0f}/s  ETA {remain:.0f}s",
                flush=True,
            )
        else:
            print(
                f"[{self.phase}] {self.done:,} {self.unit}  {rate:,.0f}/s",
                flush=True,
            )
        self._last_t = now
        self._last_done = self.done

    def finish(self, extra: str = "") -> None:
        elapsed = max(1e-6, time.perf_counter() - self._t0)
        rate = self.done / elapsed
        suffix = f"  {extra}" if extra else ""
        print(
            f"[{self.phase}] done {self.done:,} {self.unit} "
            f"in {elapsed:.1f}s ({rate:,.0f}/s){suffix}",
            flush=True,
        )


def spinner_line(phase: str, msg: str) -> None:
    """One-shot heartbeat (no TTY cursor control)."""
    print(f"[{phase}] {msg}…", flush=True)
    sys.stdout.flush()
