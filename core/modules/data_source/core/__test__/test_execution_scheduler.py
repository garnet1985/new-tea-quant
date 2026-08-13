"""DataSourceExecutionScheduler 拓扑排序主线（无网络）。"""
from __future__ import annotations

from typing import List

import pytest

from core.modules.data_source.core.execution_scheduler import DataSourceExecutionScheduler

pytestmark = pytest.mark.force_run


class _StubHandler:
    def __init__(self, key: str, deps: List[str] | None = None) -> None:
        self._key = key
        self._deps = list(deps or [])

    def get_key(self) -> str:
        return self._key

    def get_dependency_data_source_names(self) -> List[str]:
        return list(self._deps)


def test_topological_sort_orders_dependency_first() -> None:
    sched = DataSourceExecutionScheduler()
    a = _StubHandler("a")
    b = _StubHandler("b", deps=["a"])
    ordered = sched._topological_sort_handlers([b, a])
    assert [h.get_key() for h in ordered] == ["a", "b"]


def test_topological_sort_missing_dependency_raises() -> None:
    sched = DataSourceExecutionScheduler()
    with pytest.raises(ValueError, match="不存在或未启用"):
        sched._topological_sort_handlers([_StubHandler("b", deps=["missing"])])


def test_topological_sort_cycle_raises() -> None:
    sched = DataSourceExecutionScheduler()
    a = _StubHandler("a", deps=["b"])
    b = _StubHandler("b", deps=["a"])
    with pytest.raises(ValueError, match="循环依赖"):
        sched._topological_sort_handlers([a, b])
