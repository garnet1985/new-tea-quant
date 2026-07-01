"""entity_based 模式 runtime context。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, List

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.strategy.core.engines.enumerator.shared.runtime import RuntimeContext


@dataclass
class EntityBasedRuntimeContext(RuntimeContext):
    """entity_based 模式专用 RuntimeContext。"""

    EXECUTION_MODE: ClassVar[BacktestMode] = BacktestMode.ENTITY_BASED

    @staticmethod
    def entity_ids_from_jobs(jobs: list) -> List[str]:
        ids: List[str] = []
        for index, job in enumerate(jobs):
            if not isinstance(job, dict):
                raise ValueError(f"entity_based jobs[{index}] 须为 dict")
            if "entity_id" not in job:
                raise ValueError(f"entity_based jobs[{index}] 缺少 entity_id")
            entity_id = str(job["entity_id"]).strip()
            if not entity_id:
                raise ValueError(f"entity_based jobs[{index}].entity_id 不能为空")
            ids.append(entity_id)
        return ids

    @classmethod
    def assert_mode(cls, context: RuntimeContext) -> None:
        mode = BacktestMode.normalize(context.execution_mode)
        if mode != cls.EXECUTION_MODE.value:
            raise ValueError(
                f"期望 execution_mode={cls.EXECUTION_MODE.value!r}, "
                f"实际 {mode!r}"
            )


__all__ = ["EntityBasedRuntimeContext"]
