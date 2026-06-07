"""NTQ UI / workbench 进程清理：进程组与 multiprocessing 子进程。"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import signal
import time
from typing import Iterable

logger = logging.getLogger(__name__)


def kill_process_group(pid: int, *, grace_sec: float = 5.0) -> None:
    """向 ``pid`` 所在进程组发 SIGTERM，超时后 SIGKILL。"""
    if pid <= 0:
        return
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    try:
        own_pgid = os.getpgid(os.getpid())
    except ProcessLookupError:
        own_pgid = None
    if own_pgid is not None and pgid == own_pgid:
        _signal_pid(pid, signal.SIGTERM)
        _wait_pid(pid, grace_sec)
        _signal_pid(pid, signal.SIGKILL)
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            _signal_pid(pid, sig)
        if sig == signal.SIGTERM:
            if _wait_pid(pid, grace_sec):
                return
            time.sleep(0.2)


def _signal_pid(pid: int, sig: signal.Signals) -> None:
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass


def _wait_pid(pid: int, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    return False


def terminate_multiprocessing_children(*, grace_sec: float = 3.0) -> None:
    """终止当前 Python 进程下的 ``multiprocessing`` 活跃子进程（ProcessPool worker 等）。"""
    children = [p for p in mp.active_children() if p.is_alive()]
    if not children:
        return
    for proc in children:
        try:
            proc.terminate()
        except Exception as exc:
            logger.debug("terminate child %s: %s", proc.name, exc)
    deadline = time.monotonic() + grace_sec
    while time.monotonic() < deadline:
        if not any(p.is_alive() for p in children):
            return
        time.sleep(0.05)
    for proc in children:
        if not proc.is_alive():
            continue
        try:
            proc.kill()
        except Exception as exc:
            logger.debug("kill child %s: %s", proc.name, exc)


def kill_pids_with_process_groups(pids: Iterable[int], *, grace_sec: float = 5.0) -> int:
    killed = 0
    seen: set[int] = set()
    for pid in pids:
        if pid in seen:
            continue
        seen.add(pid)
        kill_process_group(pid, grace_sec=grace_sec)
        killed += 1
    return killed
