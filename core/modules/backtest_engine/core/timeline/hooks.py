"""Timeline progression hooks (calendar day drive; not \"advanced\" hooks)."""
from __future__ import annotations

from typing import Any, Dict, Protocol, Sequence, runtime_checkable


@runtime_checkable
class TimelineHooks(Protocol):
    """回测推进中的钩子（日历路径）。

    边界:
    - 负责: 单日业务、run 汇总 dict
    - 不负责: open_dates 迭代（TimelineDriver）
    - 调用方: TimelineDriver；实现方: enumerator / tag 等
    """

    def on_run_begin(self, open_dates: Sequence[str]) -> None:
        ...

    def on_day(self, day: str, index: int, *, is_last: bool) -> None:
        ...

    def on_run_end(self, open_dates: Sequence[str]) -> Dict[str, Any]:
        ...


__all__ = ["TimelineHooks"]
