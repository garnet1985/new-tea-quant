"""跨模块契约：scaffold 结果、pipeline 租约异常与常量。

推荐::

    from core.infra.system_actions import SystemActions
    from core.infra.system_actions.contracts import (
        PipelineLeaseBusyError,
        ScaffoldError,
    )

``PipelineLease`` 也可从此模块导入（懒加载实现类）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Kind = Literal["strategy", "tag"]

VALID_KINDS = frozenset(
    {"tag_run", "strategy_scan", "strategy_run", "data_renew"}
)


class ScaffoldError(ValueError):
    """新建 userspace 实体失败。"""


@dataclass(frozen=True)
class ScaffoldResult:
    kind: Kind
    key: str
    dest: Path


class PipelineLeaseBusyError(Exception):
    """``acquire`` 失败：已有任务持有全局 pipeline 租约。"""

    def __init__(self, active: dict):
        self.active = dict(active)
        kind = active.get("kind") or "unknown"
        super().__init__(f"pipeline busy: kind={kind}")


def __getattr__(name: str) -> Any:
    if name == "PipelineLease":
        from core.infra.system_actions.core.cache_cleanup.pipeline_lease import (
            PipelineLease,
        )

        return PipelineLease
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Kind",
    "VALID_KINDS",
    "ScaffoldError",
    "ScaffoldResult",
    "PipelineLeaseBusyError",
    "PipelineLease",
]
