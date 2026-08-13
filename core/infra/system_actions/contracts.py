"""跨模块契约：pipeline 租约异常与常量。

推荐::

    from core.infra.system_actions import SystemActions
    from core.infra.system_actions.contracts import PipelineLeaseBusyError

``PipelineLease`` 也可从此模块导入（懒加载实现类）。
"""

from __future__ import annotations

from typing import Any

VALID_KINDS = frozenset(
    {"tag_run", "strategy_scan", "strategy_run", "data_renew"}
)


class PipelineLeaseBusyError(Exception):
    """``acquire`` 失败：已有任务持有全局 pipeline 租约。"""

    def __init__(self, active: dict):
        self.active = dict(active)
        kind = active.get("kind") or "unknown"
        super().__init__(f"pipeline busy: kind={kind}")


def __getattr__(name: str) -> Any:
    if name == "PipelineLease":
        from core.infra.system_actions.core.pipeline_lease.pipeline_lease import (
            PipelineLease,
        )

        return PipelineLease
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VALID_KINDS",
    "PipelineLeaseBusyError",
    "PipelineLease",
]
