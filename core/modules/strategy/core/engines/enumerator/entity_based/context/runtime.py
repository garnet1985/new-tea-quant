"""entity_based 运行配置 context。"""
from __future__ import annotations

from core.modules.strategy.core.engines.enumerator.shared.runtime import RuntimeContext


class EntityRuntimeContext:
    """entity_based 模式 runtime 视图。"""

    EXECUTION_MODE = "entity_based"

    @staticmethod
    def stock_ids_from_jobs(jobs: list) -> list[str]:
        ids: list[str] = []
        for job in jobs:
            stock_id = str(job.get("stock_id") or job.get("entity_id") or "").strip()
            if stock_id:
                ids.append(stock_id)
        return ids

    @staticmethod
    def assert_mode(context: RuntimeContext) -> None:
        if context.execution_mode != EntityRuntimeContext.EXECUTION_MODE:
            raise ValueError(
                f"期望 execution_mode={EntityRuntimeContext.EXECUTION_MODE!r}, "
                f"实际 {context.execution_mode!r}"
            )


__all__ = ["EntityRuntimeContext"]
