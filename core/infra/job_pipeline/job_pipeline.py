"""JobPipeline 门面。只读面已接 TaskGuard；submit / 队列见 docs/DESIGN.md。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .core.task_guard_reader import read_running_job


class JobPipeline:
    """长任务登记 / 排队 / 进度视图的唯一对外入口。

    第一期只读：委托 ``TaskGuard``。排队 / ``filelock`` 换心见 DESIGN。
    """

    @staticmethod
    def get_running_job() -> Optional[Dict[str, Any]]:
        """当前唯一 running 任务；没有则 ``None``（串行期主读面）。"""
        return read_running_job()

    @staticmethod
    def has_running_job() -> bool:
        """``get_running_job() is not None`` 的薄封装。"""
        return JobPipeline.get_running_job() is not None

    @staticmethod
    def list_jobs() -> List[Dict[str, Any]]:
        """管道内任务快照。第一期：0～1 条 running；pending 队列尚未实现。"""
        job = read_running_job()
        return [job] if job else []

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """按 id 取任务；第一期仅能命中当前 running。"""
        needle = str(job_id or "").strip()
        if not needle:
            return None
        job = read_running_job()
        if job is None:
            return None
        return job if str(job.get("job_id") or "") == needle else None

    @staticmethod
    def submit(spec: Dict[str, Any]) -> Dict[str, Any]:
        """提交长任务：空闲则开跑，忙则入队（受队列上限约束）。"""
        raise NotImplementedError(
            "JobPipeline.submit 尚未实现；见 docs/DESIGN.md"
        )
