"""
Backtest Engine - Slice-based Executor

切片模式的执行器：读算分离（Reader多进程 + Compute单进程）。

职责：
- SliceExecutor.execute()：接受plan并执行slice jobs
- Reader多进程读取数据
- Compute单进程计算结果
- 管道队列控制（queue_capacity）
- 进程间通信（Queue传递payload）

特点：
- 读算分离（Reader多进程 + Compute单进程）
- 管道队列控制（防止OOM）
- 更严格的内存管控
"""
from __future__ import annotations

import logging
import time
import multiprocessing as mp
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.types import (
    JobReport,
    RunProgress,
)
from core.modules.backtest_engine.core.slice_based.planner import (
    SliceDispatchPlan,
    SliceJobBatch,
)
from core.modules.backtest_engine.core.shared.context import ExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class SliceExecutionResult:
    """切片执行结果。"""
    
    success: bool
    total_slices: int
    completed_slices: int
    failed_slices: int
    elapsed_seconds: float
    slice_results: List[Dict[str, Any]]


class SliceExecutor:
    """切片模式执行器（读算分离）。
    
    核心特点：
    - Reader多进程读取数据
    - Compute单进程计算结果
    - 管道队列控制（防止OOM）
    """
    
    @staticmethod
    def execute(
        plan: SliceDispatchPlan,
        batches: List[SliceJobBatch],
        context: ExecutionContext,
        log_label: str = "切片执行",
    ) -> SliceExecutionResult:
        """接受plan并执行slice jobs（读算分离）。
        
        Args:
            plan: 切片调度规划
            batches: 切割后的切片批次
            context: 执行上下文
            log_label: 日志标签
            
        Returns:
            SliceExecutionResult: 执行结果
        """
        if not batches:
            logger.info("%s无slices需要执行", log_label)
            return SliceExecutionResult(
                success=True,
                total_slices=0,
                completed_slices=0,
                failed_slices=0,
                elapsed_seconds=0.0,
                slice_results=[],
            )
        
        total_slices = sum(batch.slices_count for batch in batches)
        completed_slices = 0
        failed_slices = 0
        slice_results: List[Dict[str, Any]] = []
        
        logger.info(
            "%s启动: run=%s, slices=%s, reader=%s, compute=%s, queue=%s",
            log_label,
            context.run_name,
            total_slices,
            plan.reader_workers,
            plan.compute_processes,
            plan.queue_capacity,
        )
        
        start_time = time.monotonic()
        interrupted = False
        
        try:
            # 读算分离执行逻辑（核心特点）
            result = SliceExecutor._execute_read_compute_separation(
                plan=plan,
                batches=batches,
                context=context,
                log_label=log_label,
            )
            
            completed_slices = result.completed_slices
            failed_slices = result.failed_slices
            slice_results = result.slice_results
        
        except KeyboardInterrupt:
            logger.warning("%s收到Ctrl+C，停止执行并清理资源", log_label)
            interrupted = True
            # 进程清理会在finally块中执行
        
        elapsed_seconds = time.monotonic() - start_time
        
        # 构建执行结果
        success = not interrupted and failed_slices == 0
        result = SliceExecutionResult(
            success=success,
            total_slices=total_slices,
            completed_slices=completed_slices,
            failed_slices=failed_slices if not interrupted else 0,
            elapsed_seconds=elapsed_seconds,
            slice_results=slice_results,
        )
        
        if interrupted:
            logger.warning(
                "%s中断: run=%s, slices=%s, completed=%s, elapsed=%.2fs",
                log_label,
                context.run_name,
                total_slices,
                completed_slices,
                elapsed_seconds,
            )
        else:
            logger.info(
                "%s完成: run=%s, slices=%s, ok=%s, fail=%s, elapsed=%.2fs",
                log_label,
                context.run_name,
                total_slices,
                completed_slices,
                failed_slices,
                elapsed_seconds,
            )
        
        return result
    
    @staticmethod
    def _execute_read_compute_separation(
        plan: SliceDispatchPlan,
        batches: List[SliceJobBatch],
        context: ExecutionContext,
        log_label: str = "切片执行",
    ) -> SliceExecutionResult:
        """读算分离执行逻辑（核心特点）。
        
        流程：
        1. 启动Reader多进程读取数据
        2. 启动Compute单进程计算结果
        3. 管道队列控制（queue_capacity）
        4. 进程生命周期管理
        
        Args:
            plan: 切片调度规划
            batches: 切割后的切片批次
            context: 执行上下文
            log_label: 日志标签
            
        Returns:
            SliceExecutionResult: 执行结果
        """
        # 构建所有slice任务
        all_slice_ids: List[str] = []
        for batch in batches:
            all_slice_ids.extend(batch.slice_ids)
        
        if not all_slice_ids:
            return SliceExecutionResult(
                success=True,
                total_slices=0,
                completed_slices=0,
                failed_slices=0,
                elapsed_seconds=0.0,
                slice_results=[],
            )
        
        total_slices = len(all_slice_ids)
        completed_slices = 0
        failed_slices = 0
        slice_results: List[Dict[str, Any]] = []
        
        # 创建管道队列（Reader → Compute）
        ctx = mp.get_context("spawn")
        reader_cmd_q = ctx.Queue()  # Reader命令队列
        payload_q = ctx.Queue(maxsize=plan.queue_capacity)  # Payload队列（控制容量）
        done_q = ctx.Queue()  # 完成队列
        
        logger.info(
            "%s读算分离启动: reader=%s, compute=%s, queue=%s, preload=%s",
            log_label,
            plan.reader_workers,
            plan.compute_processes,
            plan.queue_capacity,
            plan.preload_depth,
        )
        
        # 启动Reader进程（多进程）
        reader_procs: List[mp.Process] = []
        for worker_idx in range(plan.reader_workers):
            proc = ctx.Process(
                target=SliceExecutor._reader_worker,
                args=(reader_cmd_q, payload_q, context),
                name=f"slice_reader_{worker_idx}",
                daemon=True,
            )
            reader_procs.append(proc)
            proc.start()
        
        # 启动Compute进程（单进程）
        compute_proc = ctx.Process(
            target=SliceExecutor._compute_worker,
            args=(payload_q, done_q, context),
            name="slice_compute",
            daemon=True,
        )
        compute_proc.start()
        
        try:
            # 驱动slice执行
            loads_dispatched = 0
            
            def _dispatch_slice_load(slice_index: int) -> None:
                """发送slice加载命令到Reader。"""
                slice_id = all_slice_ids[slice_index]
                reader_cmd_q.put({
                    "type": "load",
                    "slice_index": slice_index,
                    "slice_id": slice_id,
                })
            
            def _in_flight_loads(consumed_count: int) -> int:
                """计算当前in-flight的loads数量。"""
                return max(0, loads_dispatched - consumed_count)
            
            def _seed_pipeline() -> None:
                """初始化管道（preload depth）。"""
                nonlocal loads_dispatched
                while loads_dispatched < total_slices and _in_flight_loads(0) < plan.preload_depth:
                    _dispatch_slice_load(loads_dispatched)
                    loads_dispatched += 1
            
            def _top_up_pipeline(consumed_count: int) -> None:
                """补充管道（保持preload depth）。"""
                nonlocal loads_dispatched
                while loads_dispatched < total_slices and _in_flight_loads(consumed_count) < plan.preload_depth:
                    _dispatch_slice_load(loads_dispatched)
                    loads_dispatched += 1
            
            # 初始化管道
            _seed_pipeline()
            
            # 驱动slice执行
            for i in range(total_slices):
                # 等待Compute完成slice
                done_msg = done_q.get()
                
                if not isinstance(done_msg, dict):
                    logger.error("%s收到未知消息类型: %s", log_label, type(done_msg))
                    failed_slices += 1
                    context.update_progress(success=False)
                    continue
                
                if not done_msg.get("success", True):
                    logger.error(
                        "%sslice失败: slice_id=%s, error=%s",
                        log_label,
                        done_msg.get("slice_id"),
                        done_msg.get("error"),
                    )
                    failed_slices += 1
                    slice_results.append(done_msg)
                    context.update_progress(success=False)
                    continue
                
                # 检查slice顺序
                slice_index = int(done_msg.get("slice_index", 0))
                if slice_index != i:
                    logger.warning(
                        "%sslice顺序不匹配: expected=%s, got=%s",
                        log_label,
                        i,
                        slice_index,
                    )
                
                # 记录成功slice
                completed_slices += 1
                slice_results.append(done_msg)
                context.update_progress(success=True)
                
                # 补充管道
                _top_up_pipeline(i + 1)
                
                logger.info(
                    "%sslice %s/%s done (%s)",
                    log_label,
                    i + 1,
                    total_slices,
                    done_msg.get("slice_id"),
                )
            
            # 发送SHUTDOWN命令
            for _ in range(plan.reader_workers):
                reader_cmd_q.put({"type": "shutdown"})
            payload_q.put({"type": "shutdown"})
            
            logger.info("%s所有slices完成，等待进程结束...", log_label)
        
        finally:
            # 清理进程
            for proc in reader_procs:
                proc.join(timeout=30.0)
                if proc.is_alive():
                    logger.warning("%sReader进程未正常退出，强制终止", log_label)
                    proc.terminate()
                    proc.join(timeout=5.0)
            
            compute_proc.join(timeout=30.0)
            if compute_proc.is_alive():
                logger.warning("%sCompute进程未正常退出，强制终止", log_label)
                compute_proc.terminate()
                compute_proc.join(timeout=5.0)
        
        success = failed_slices == 0
        elapsed_seconds = time.monotonic() - context.start_time
        
        return SliceExecutionResult(
            success=success,
            total_slices=total_slices,
            completed_slices=completed_slices,
            failed_slices=failed_slices,
            elapsed_seconds=elapsed_seconds,
            slice_results=slice_results,
        )
    
    @staticmethod
    def _reader_worker(
        reader_cmd_q: mp.Queue,
        payload_q: mp.Queue,
        context: ExecutionContext,
    ) -> None:
        """Reader worker：读取slice数据并传递到payload队列。
        
        Args:
            reader_cmd_q: Reader命令队列
            payload_q: Payload队列（传递到Compute）
            context: 执行上下文
        """
        logger.info("Reader worker启动: run=%s", context.run_name)
        
        try:
            while True:
                # 等待命令
                cmd = reader_cmd_q.get()
                
                if cmd.get("type") == "shutdown":
                    logger.info("Reader worker收到SHUTDOWN命令，退出")
                    break
                
                if cmd.get("type") != "load":
                    logger.warning("Reader worker收到未知命令: %s", cmd.get("type"))
                    continue
                
                slice_index = int(cmd.get("slice_index", 0))
                slice_id = str(cmd.get("slice_id", ""))
                
                try:
                    # TODO: 实现实际的slice数据读取逻辑
                    # 简化版：模拟读取
                    
                    # 构建payload（模拟slice数据）
                    payload = {
                        "slice_index": slice_index,
                        "slice_id": slice_id,
                        "data": {"模拟数据": slice_id},  # 简化版
                        "load_elapsed_sec": 0.1,  # 简化版
                    }
                    
                    # 发送到payload队列（可能阻塞，等待Compute消费）
                    payload_q.put(payload)
                    
                    logger.info(
                        "Reader worker: slice %s loaded (%s)",
                        slice_index,
                        slice_id,
                    )
                
                except Exception as exc:
                    logger.error(
                        "Reader worker失败: slice_id=%s, error=%s",
                        slice_id,
                        exc,
                    )
                    # 发送错误消息到payload队列
                    payload_q.put({
                        "slice_index": slice_index,
                        "slice_id": slice_id,
                        "success": False,
                        "error": str(exc),
                    })
        
        except Exception as exc:
            logger.error("Reader worker异常退出: %s", exc, exc_info=True)
        
        logger.info("Reader worker退出")
    
    @staticmethod
    def _compute_worker(
        payload_q: mp.Queue,
        done_q: mp.Queue,
        context: ExecutionContext,
    ) -> None:
        """Compute worker：计算slice结果并发送到完成队列。
        
        Args:
            payload_q: Payload队列（从Reader接收）
            done_q: 完成队列（发送到主进程）
            context: 执行上下文
        """
        logger.info("Compute worker启动: run=%s", context.run_name)
        
        try:
            while True:
                # 等待payload
                payload = payload_q.get()
                
                if payload.get("type") == "shutdown":
                    logger.info("Compute worker收到SHUTDOWN命令，退出")
                    break
                
                slice_index = int(payload.get("slice_index", 0))
                slice_id = str(payload.get("slice_id", ""))
                
                # 检查是否为错误消息（Reader失败）
                if not payload.get("success", True):
                    # 直接转发错误消息
                    done_q.put(payload)
                    continue
                
                try:
                    # TODO: 实现实际的slice计算逻辑
                    # 简化版：模拟计算
                    
                    # 计算结果（模拟）
                    result = {
                        "slice_index": slice_index,
                        "slice_id": slice_id,
                        "success": True,
                        "data": {"模拟结果": slice_id},  # 简化版
                        "compute_elapsed_sec": 0.2,  # 简化版
                    }
                    
                    # 发送到完成队列
                    done_q.put(result)
                    
                    logger.info(
                        "Compute worker: slice %s done (%s)",
                        slice_index,
                        slice_id,
                    )
                
                except Exception as exc:
                    logger.error(
                        "Compute worker失败: slice_id=%s, error=%s",
                        slice_id,
                        exc,
                    )
                    # 发送错误消息到完成队列
                    done_q.put({
                        "slice_index": slice_index,
                        "slice_id": slice_id,
                        "success": False,
                        "error": str(exc),
                    })
        
        except Exception as exc:
            logger.error("Compute worker异常退出: %s", exc, exc_info=True)
        
        logger.info("Compute worker退出")


# ===== Reader进程 =====

def _reader_worker(
    slice_ids: List[str],
    payload_queue: mp.Queue,
    done_queue: mp.Queue,
    log_label: str = "Reader",
) -> None:
    """Reader进程：读取数据并放入队列。
    
    Args:
        slice_ids: 切片ID列表
        payload_queue: Payload队列（传递给Compute）
        done_queue: 完成队列（通知Compute）
        log_label: 日志标签
    """
    # TODO: 实现Reader逻辑
    for slice_id in slice_ids:
        try:
            # TODO: 读取slice数据
            payload = {"slice_id": slice_id, "data": None}
            
            # 放入队列（控制容量）
            payload_queue.put(payload, timeout=10.0)
            
        except Exception as exc:
            logger.error("%s读取失败: slice_id=%s, error=%s", log_label, slice_id, exc)
            payload_queue.put({"slice_id": slice_id, "error": str(exc)})


# ===== Compute进程 =====

def _compute_worker(
    payload_queue: mp.Queue,
    done_queue: mp.Queue,
    log_label: str = "Compute",
) -> None:
    """Compute进程：从队列接收payload并计算。
    
    Args:
        payload_queue: Payload队列（接收Reader数据）
        done_queue: 完成队列（通知主进程）
        log_label: 日志标签
    """
    # TODO: 实现Compute逻辑
    while True:
        try:
            # 从队列接收payload
            payload = payload_queue.get(timeout=10.0)
            
            if payload is None:  # 结束信号
                break
            
            # TODO: 计算slice
            slice_id = payload.get("slice_id")
            result = {"slice_id": slice_id, "success": True}
            
            # 放入done队列
            done_queue.put(result)
            
        except Exception as exc:
            logger.error("%s计算失败: error=%s", log_label, exc)
            done_queue.put({"success": False, "error": str(exc)})


__all__ = [
    "SliceExecutionResult",
    "SliceExecutor",
]