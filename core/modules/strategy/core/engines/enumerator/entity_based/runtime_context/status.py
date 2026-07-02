"""entity_based 模式 runtime status。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.modules.strategy.core.context.backtest_runtime import RuntimeStatus


@dataclass
class EntityBasedRuntimeStatus(RuntimeStatus):
    """entity_based 模式专用 RuntimeStatus。

    继承RuntimeStatus所有字段：
    - stage: 运行阶段（init/preprocess/execute/postprocess）
    - hook_stage: hooks执行阶段
    - progress: 进度信息
    - monitor: 监控信息（已合并到performance）
    - job_results: job结果列表
    - errors: 错误字典
    - started_at, elapsed_seconds: 时间
    """

    # entity_based特化字段：
    current_entity_id: Optional[str] = None    # 当前处理的entity_id
    entities_completed: int = 0                # 已完成的entity数量
    entities_failed: int = 0                   # 失败的entity数量

    @classmethod
    def init(cls) -> EntityBasedRuntimeStatus:
        """初始化status（preprocess阶段）。"""
        return cls(stage="preprocess")


__all__ = ["EntityBasedRuntimeStatus"]