"""
Backtest Engine - Timeline-based Executor

时间线模式的执行器：接受plan，切割jobs并执行。

职责：
- TimelineExecutor.execute()：接受plan并执行jobs
- _build_jobs_from_plan()：根据plan切割jobs（entity-based）
- _run_jobs()：执行jobs（使用ProcessPoolExecutor）
- _monitor_progress()：监控执行进度

特点：
- entity-based切割（每个job包含多个entity）
- 使用ProcessPoolExecutor并行执行
- 监控进度并回调on_result
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ProcessPoolExecutor, Future, wait, FIRST_COMPLETED
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable

from core.modules.backtest_engine.core.shared.types import (
    Job,
    JobContext,
    JobReport,
    DispatchResult,
    JobFailure,
    JobFailurePhase,
    RunProgress,
)
from core.modules.backtest_engine.core.timeline_based.planner import (
    DispatchPlan,
    JobBatch,
)
from core.modules.backtest_engine.core.shared.context import ExecutionContext

logger = logging.getLogger(__name__)


# ===== Hooks协议 =====

class OnResultHook(Callable):
    """结果回调：接收JobReport和RunProgress。"""
    
    def __call__(self, report: JobReport, progress: RunProgress) -> None:
        ...


class OnReleaseHook(Callable):
    """释放回调：接收JobContext。"""
    
    def __call__(self, context: JobContext) -> None:
        ...


# ===== 执行结果 =====

@dataclass
class ExecutionResult:
    """timeline执行结果。"""
    
    success: bool
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    failures: List[JobFailure]
    elapsed_seconds: float
    job_results: List[JobReport]


class TimelineExecutor:
    """时间线模式执行器（面向对象方式）。"""
    
    @staticmethod
    def execute(
        plan: DispatchPlan,
        batches: List[JobBatch],
        context: ExecutionContext,
        on_result: Optional[OnResultHook] = None,
        on_release: Optional[OnReleaseHook] = None,
        log_label: str = "执行",
    ) -> ExecutionResult:
        """接受plan并执行jobs。
        
        Args:
            plan: 调度规划
            batches: 切割后的job批次
            context: 执行上下文（pickle传递到子进程）
            on_result: 结果回调
            on_release: 释放回调
            log_label: 日志标签
            
        Returns:
            ExecutionResult: 执行结果
        """
        if not batches:
            logger.info("%s无jobs需要执行", log_label)
            return ExecutionResult(
                success=True,
                total_jobs=0,
                completed_jobs=0,
                failed_jobs=0,
                failures=[],
                elapsed_seconds=0.0,
                job_results=[],
            )
        
        # 初始化执行状态
        total_jobs = len(batches)
        completed_jobs = 0
        failed_jobs = 0
        failures: List[JobFailure] = []
        job_results: List[JobReport] = []
        
        # 构建Job列表（从batches）
        jobs = TimelineExecutor._build_jobs_from_batches(batches)
        
        # 执行jobs
        logger.info(
            "%s启动: run=%s, jobs=%s, workers=%s, epj=%s",
            log_label,
            context.run_name,
            total_jobs,
            plan.max_workers,
            plan.entities_per_job,
        )
        
        start_time = time.monotonic()
        
        try:
            # 使用ProcessPoolExecutor执行
            with ProcessPoolExecutor(max_workers=plan.max_workers) as pool:
                futures: Dict[Future, Job] = {}
                
                # 提交所有jobs
                for job in jobs:
                    job_context = TimelineExecutor._build_job_context(job, context)
                    future = pool.submit(_job_worker, job_context, context)
                    futures[future] = job
                
                # 等待完成并监控进度
                while futures:
                    done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                    
                    for future in done:
                        job = futures.pop(future)
                        try:
                            raw_result = future.result()
                            report = TimelineExecutor._normalize_report(job.job_id, raw_result)
                            
                            if report.success:
                                completed_jobs += 1
                            else:
                                failed_jobs += 1
                                failures.append(
                                    JobFailure(
                                        job_id=job.job_id,
                                        phase=JobFailurePhase.EXECUTE,
                                        error=report.error or "execute returned success=False",
                                    )
                                )
                            
                            job_results.append(report)
                            
                            # 更新context进度
                            context.update_progress(report.success)
                            
                            # 回调on_result
                            if on_result:
                                progress = RunProgress(
                                    finished=context.finished_jobs,
                                    total=context.total_jobs,
                                    ok=context.success_count,
                                    fail=context.fail_count,
                                )
                                on_result(report, progress)
                        
                        except Exception as exc:
                            failed_jobs += 1
                            failures.append(
                                JobFailure(
                                    job_id=job.job_id,
                                    phase=JobFailurePhase.EXECUTE,
                                    error=str(exc),
                                )
                            )
                            
                            # 更新context进度（失败）
                            context.update_progress(success=False)
                            
                            # 回调on_result（失败）
                            if on_result:
                                report = JobReport(
                                    job_id=job.job_id,
                                    success=False,
                                    error=str(exc),
                                )
                                progress = RunProgress(
                                    finished=context.finished_jobs,
                                    total=context.total_jobs,
                                    ok=context.success_count,
                                    fail=context.fail_count,
                                )
                                on_result(report, progress)
        
        except KeyboardInterrupt:
            logger.info("%s收到Ctrl+C，停止执行", log_label)
            # TODO: 处理中断，清理资源
        
        elapsed_seconds = time.monotonic() - start_time
        
        # 构建执行结果（使用context数据）
        success = context.fail_count == 0
        result = ExecutionResult(
            success=success,
            total_jobs=context.total_jobs,
            completed_jobs=context.success_count,
            failed_jobs=context.fail_count,
            failures=failures,
            elapsed_seconds=elapsed_seconds,
            job_results=job_results,
        )
        
        logger.info(
            "%s完成: run=%s, jobs=%s, ok=%s, fail=%s, elapsed=%.2fs",
            log_label,
            context.run_name,
            context.total_jobs,
            context.success_count,
            context.fail_count,
            elapsed_seconds,
        )
        
        return result
    
    @staticmethod
    def _build_jobs_from_batches(batches: List[JobBatch]) -> List[Job]:
        """从batches构建Job列表。
        
        Args:
            batches: 切割后的job批次
            
        Returns:
            List[Job]: Job列表
        """
        jobs = []
        for batch in batches:
            job = Job(
                job_id=batch.batch_id,
                payload=batch.payload,
            )
            jobs.append(job)
        return jobs
    
    @staticmethod
    def _build_job_context(job: Job, context: ExecutionContext) -> JobContext:
        """构建JobContext（包含context信息）。
        
        Args:
            job: Job对象
            context: 执行上下文
            
        Returns:
            JobContext: Job上下文
        """
        payload = dict(job.payload)
        payload["_executor"] = context.executor
        payload["_job_id"] = job.job_id
        payload["_run_name"] = context.run_name
        
        # 传递业务数据（可选）
        if context.business_data:
            payload["_business_data"] = context.business_data
        
        return JobContext(
            job_id=job.job_id,
            payload=payload,
            run_name=context.run_name,
        )
    
    @staticmethod
    def _normalize_report(job_id: str, raw_result: object) -> JobReport:
        """规范化执行结果为JobReport。
        
        Args:
            job_id: Job ID
            raw_result: 原始执行结果
            
        Returns:
            JobReport: 规范化后的报告
        """
        if isinstance(raw_result, JobReport):
            return raw_result
        
        if isinstance(raw_result, dict):
            success = bool(raw_result.get("success", True))
            return JobReport(
                job_id=job_id,
                success=success,
                data=raw_result,
                error=raw_result.get("error") if not success else None,
            )
        
        return JobReport(job_id=job_id, success=True, data=raw_result)


def _job_worker(job_context: JobContext, execution_context: ExecutionContext) -> Dict[str, Any]:
    """子进程worker函数（执行单个job batch）。
    
    Timeline模式：每个job batch包含多个entity（entities_per_job）。
    需要遍历batch中的所有entity，分别调用Worker处理。
    
    Args:
        job_context: Job上下文（单个batch）
        execution_context: 执行上下文（全局）
        
    Returns:
        Dict[str, Any]: 执行结果（包含batch中所有entity的结果）
    """
    executor_key = str(job_context.payload.get("_executor") or "").strip()
    
    # 从payload中获取Worker类信息
    worker_class_name = job_context.payload.get("_worker_class_name")
    worker_module_path = job_context.payload.get("_worker_module_path")
    
    # 动态导入Worker类
    worker_class = _load_worker_class(
        executor_key,
        worker_class_name,
        worker_module_path,
    )
    
    # 从job_context.payload中提取jobs（多个entity）
    jobs = job_context.payload.get("jobs", [])
    
    if not jobs:
        return {
            "success": True,
            "job_id": job_context.job_id,
            "entity_results": [],
            "message": "空batch",
        }
    
    # 遍历batch中的所有entity，分别调用Worker
    entity_results = []
    for job_data in jobs:
        try:
            # 构建单个entity的job_payload
            job_payload = _build_entity_payload(job_data, job_context.job_id)
            
            # 实例化Worker（传入单个entity的payload）
            worker_instance = worker_class(job_payload)
            
            # 调用入口方法（根据executor_key选择）
            if executor_key == "tag":
                # Tag: 调用process_entity()
                entity_result = worker_instance.process_entity()
            elif executor_key.startswith("strategy"):
                # Strategy: 调用run()
                entity_result = worker_instance.run()
            else:
                raise ValueError(f"未知executor_key: {executor_key}")
            
            # 规范化结果为dict
            if isinstance(entity_result, dict):
                entity_results.append(entity_result)
            else:
                entity_results.append({
                    "success": True,
                    "entity_id": job_data.get("entity_id"),
                    "data": entity_result,
                })
            
            # 调用on_job_end钩子（如果存在）
            if hasattr(worker_instance, 'on_job_end'):
                try:
                    worker_instance.on_job_end(entity_results[-1])
                except Exception as hook_exc:
                    logger.warning(
                        "on_job_end钩子失败: job_id=%s, error=%s",
                        job_context.job_id,
                        hook_exc,
                    )
        
        except Exception as exc:
            entity_results.append({
                "success": False,
                "entity_id": job_data.get("entity_id"),
                "error": str(exc),
            })
    
    # 构建batch结果
    success_count = sum(1 for r in entity_results if r.get("success", False))
    fail_count = len(entity_results) - success_count
    
    return {
        "success": fail_count == 0,
        "job_id": job_context.job_id,
        "entity_results": entity_results,
        "success_count": success_count,
        "fail_count": fail_count,
        "entities_count": len(jobs),
    }


def _load_worker_class(
    executor_key: str,
    worker_class_name: Optional[str],
    worker_module_path: Optional[str],
) -> Any:
    """动态加载Worker类。
    
    Args:
        executor_key: 执行器标识（"tag", "strategy.enum", "strategy.price"）
        worker_class_name: Worker类名称（可选）
        worker_module_path: Worker模块路径（可选）
        
    Returns:
        Worker类
    """
    # 如果提供了具体的Worker类信息，直接导入
    if worker_class_name and worker_module_path:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            worker_class_name,
            worker_module_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, worker_class_name)
    
    # 否则使用默认的BaseWorker
    if executor_key == "tag":
        from core.modules.tag.engines.shared.base_worker import BaseTagWorker
        return BaseTagWorker
    elif executor_key.startswith("strategy"):
        from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
        return BaseStrategyWorker
    else:
        raise ValueError(f"未知executor_key: {executor_key}")


def _build_entity_payload(job_data: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
    """构建单个entity的job_payload（传递给Worker.__init__）。
    
    Args:
        job_data: 单个entity的数据
        batch_id: Batch ID
        
    Returns:
        Dict[str, Any]: 单个entity的job_payload
    """
    # 复制job_data作为payload基础
    payload = dict(job_data)
    
    # 添加batch信息（可选，用于日志追踪）
    payload["_batch_id"] = batch_id
    
    return payload


__all__ = [
    "ExecutionResult",
    "TimelineExecutor",
    "OnResultHook",
    "OnReleaseHook",
]