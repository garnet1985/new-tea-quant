# WorkerProbe 单元测试
from __future__ import annotations

import multiprocessing as mp

from core.infra.job_dispatcher.probe import WorkerProbe


def test_resolve_auto_logical_minus_reserve():
    cpu = mp.cpu_count() or 1
    assert WorkerProbe.resolve("auto", reserve_cores=1) == max(1, cpu - 1)
    assert WorkerProbe.resolve("auto", reserve_cores=0) == cpu


def test_resolve_auto_positive():
    n = WorkerProbe.resolve("auto", reserve_cores=0)
    assert isinstance(n, int)
    assert n >= 1


def test_resolve_int_clamped():
    n = WorkerProbe.resolve(9999)
    assert n <= (mp.cpu_count() or 1) * 2


def test_resolve_with_cap():
    n = WorkerProbe.resolve("auto", reserve_cores=0, cap=2)
    assert n <= 2
