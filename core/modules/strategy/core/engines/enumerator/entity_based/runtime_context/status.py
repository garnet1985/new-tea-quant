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

    def update_progress(
        self,
        total_jobs: int,
        finished: int,
        completed_jobs: int,
        failed_jobs: int,
        last_job_id: str,
        last_job_status: str,
    ) -> None:
        """更新进度信息（封装方法）。"""
        self.progress = {
            "total_jobs": total_jobs,
            "finished": finished,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "last_job_id": last_job_id,
            "last_job_status": last_job_status,
        }
        self.entities_completed = completed_jobs
        self.entities_failed = failed_jobs


__all__ = ["EntityBasedRuntimeStatus"]