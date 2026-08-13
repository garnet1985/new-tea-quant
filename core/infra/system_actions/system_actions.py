"""SystemActions 门面 — pipeline。

方法内懒导入，避免包 import 时拉起重链。
"""

from __future__ import annotations

from typing import Any, Optional

from .contracts import (
    VALID_KINDS,
    PipelineLeaseBusyError,
)


class TypesNamespace:
    """与 ``contracts`` 同源的类型 / 常量挂载点。

    ``PipelineLease`` 经 ``__getattr__`` 懒加载（与 contracts 一致）。
    """

    VALID_KINDS = VALID_KINDS
    PipelineLeaseBusyError = PipelineLeaseBusyError

    def __getattr__(self, name: str) -> Any:
        if name == "PipelineLease":
            from core.infra.system_actions.core.pipeline_lease.pipeline_lease import (
                PipelineLease,
            )

            return PipelineLease
        raise AttributeError(f"{type(self).__name__!r} has no attribute {name!r}")


class PipelineNamespace:
    """全局 DuckDB pipeline 租约。"""

    @staticmethod
    def read_status() -> dict:
        from core.infra.system_actions.core.pipeline_lease.pipeline_lease import (
            PipelineLease,
        )

        return PipelineLease.read_status()

    @staticmethod
    def lease(
        *,
        kind: str,
        job_id: str,
        resource_key: str = "",
        label: str = "",
        domains: Optional[list] = None,
    ):
        """构造 ``PipelineLease`` 上下文管理器。"""
        from core.infra.system_actions.core.pipeline_lease.pipeline_lease import (
            PipelineLease,
        )

        return PipelineLease(
            kind=kind,
            job_id=job_id,
            resource_key=resource_key,
            label=label,
            domains=domains,
        )


class SystemActions:
    """系统级操作门面（Facade）。"""

    pipeline = PipelineNamespace()
    types = TypesNamespace()


__all__ = ["SystemActions"]
