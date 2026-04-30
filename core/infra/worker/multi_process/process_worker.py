#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于 multiprocessing 的多进程任务执行器
支持两种模式：
1. Batch模式：batch间串行，batch内并行
2. 队列模式：持续填充进程池，完成一个立即启动下一个
"""

import time
import multiprocessing as mp
import logging
import signal
import atexit
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import os

# Worker 配置
from core.infra.worker.multi_process.task_type import TaskType
from core.infra.project_context import ConfigManager


# 设置日志
logger = logging.getLogger(__name__)
# 避免重复日志输出
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ExecutionMode(Enum):
    """执行模式枚举"""
    BATCH = "batch"      # Batch模式：batch间串行，batch内并行
    QUEUE = "queue"      # 队列模式：持续填充进程池


class JobStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """任务执行结果"""
    job_id: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    
    def __str__(self):
        return f"JobResult(job_id={self.job_id}, status={self.status.value}, duration={self.duration:.2f}s)"


class ProgressReportMode(Enum):
    """进度日志上报模式"""
    NONE = "none"
    EVERY_JOB_DONE = "every_job_done"
    EVERY_SEC_INTERVAL = "every_sec_interval"
    EVERY_PROGRESS_INTERVAL = "every_progress_interval"


@dataclass
class ProgressReportConfig:
    """进度日志配置（仅控制日志上报频率）"""
    mode: ProgressReportMode = ProgressReportMode.EVERY_PROGRESS_INTERVAL
    interval_seconds: float = 2.0
    interval_pct: int = 5
    log_on_run_started: bool = False
    log_on_run_finished: bool = True


class ProcessWorker:
    """
    基于 multiprocessing 的多进程任务执行器
    
    特性：
    ✅ 支持两种执行模式：Batch模式和队列模式
    ✅ 自动进程数管理（默认使用CPU核心数）
    ✅ 任务队列管理
    ✅ 详细的执行统计
    ✅ 优雅的信号处理
    ✅ 任务取消和超时
    ✅ 错误处理和重试
    ✅ 实时进度监控
    ✅ 内存使用监控
    """
    
    # =========================================================================
    # 静态方法：Worker 数量计算
    # =========================================================================
    
    @staticmethod
    def calculate_workers(
        task_type: TaskType,
        reserve_cores: int = 2
    ) -> int:
        """
        根据任务类型计算建议的 worker 数量
        
        Args:
            task_type: 任务类型（CPU_INTENSIVE / IO_INTENSIVE / MIXED）
            reserve_cores: 预留核心数（给系统和其他进程）
        
        Returns:
            建议的 worker 数量（至少为 1）
        """
        cpu_count = mp.cpu_count() or 1
        
        if task_type == TaskType.CPU_INTENSIVE:
            # CPU 密集型：使用物理核心数 - 预留
            # 假设超线程：物理核心 ≈ cpu_count / 2
            physical_cores = max(1, cpu_count // 2)
            return max(1, physical_cores - reserve_cores)
        
        elif task_type == TaskType.IO_INTENSIVE:
            # I/O 密集型：可以使用全部逻辑核心（等待 I/O 时 CPU 闲置）
            return max(2, cpu_count - reserve_cores + 1)
        
        else:  # MIXED（默认）
            # 混合型：使用逻辑核心数 - 预留
            return max(1, cpu_count - reserve_cores)
    
    @staticmethod
    def _validate_workers(max_workers: int) -> int:
        """
        验证并限制 worker 数量
        
        Args:
            max_workers: 请求的 worker 数量
            
        Returns:
            验证后的 worker 数量（不超过 CPU 核心数的 2 倍）
        """
        cpu_count = mp.cpu_count() or 1
        max_allowed = cpu_count * 2
        return min(max(1, max_workers), max_allowed)
    
    @staticmethod
    def resolve_max_workers(
        max_workers: Union[str, int],
        module_name: str
    ) -> int:
        """
        解析 max_workers 参数（支持 'auto' 或数字）
        
        Args:
            max_workers: 
                - 'auto': 自动计算（根据模块配置）
                - 数字: 手动指定（会做保护）
            module_name: 模块名称（用于查找配置）
        
        Returns:
            实际使用的 worker 数量
        
        示例:
            >>> ProcessWorker.resolve_max_workers('auto', 'OpportunityEnumerator')
            6  # 根据 CPU 和任务类型自动计算
            
            >>> ProcessWorker.resolve_max_workers(10, 'OpportunityEnumerator')
            10  # 手动指定，通过验证
            
            >>> ProcessWorker.resolve_max_workers(99999, 'OpportunityEnumerator')
            32  # 手动指定但超过上限，自动保护
        """
        # 1. 如果是 'auto'，自动计算
        if isinstance(max_workers, str) and max_workers.lower() == 'auto':
            # 从配置获取任务类型
            config = ConfigManager.get_module_config(module_name)
            task_type = config['task_type']
            reserve_cores = config['reserve_cores']
            
            calculated = ProcessWorker.calculate_workers(task_type, reserve_cores)
            
            logger.info(
                f"✅ Worker 数量（自动）: {calculated} "
                f"(模块={module_name}, 类型={task_type.value}, "
                f"CPU核心={mp.cpu_count()}, 预留={reserve_cores})"
            )
            
            return calculated
        else:
            # 手动指定：做保护
            validated = ProcessWorker._validate_workers(max_workers)
            
            if validated != max_workers:
                logger.warning(
                    f"⚠️ Worker 数量超过上限，已调整: {max_workers} → {validated} "
                    f"(最大允许: {mp.cpu_count() * 2})"
                )
            else:
                logger.info(f"✅ Worker 数量（手动）: {validated}")
            
            return validated
    
    @staticmethod
    def _validate_workers(max_workers: int) -> int:
        """
        验证并限制 worker 数量
        
        Args:
            max_workers: 请求的 worker 数量
            
        Returns:
            验证后的 worker 数量（不超过 CPU 核心数的 2 倍）
        """
        cpu_count = mp.cpu_count() or 1
        max_allowed = cpu_count * 2
        return min(max(1, max_workers), max_allowed)
    
    # =========================================================================
    # 实例方法
    # =========================================================================
    
    def __init__(self, 
                 max_workers: Optional[int] = None,
                 execution_mode: ExecutionMode = ExecutionMode.QUEUE,
                 batch_size: Optional[int] = None,
                 job_executor: Optional[Callable] = None,
                 on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None,
                 progress_report_config: Optional[ProgressReportConfig] = None,
                 is_main_process_used_if_single_worker: bool = True,
                 enable_monitoring: bool = True,
                 timeout: float = 300.0,
                 is_verbose: bool = False,
                 debug: bool = False,
                 start_method: str = "spawn"):
        """
        初始化多进程任务执行器
        
        Args:
            max_workers: 最大并行进程数，None时使用CPU核心数
            execution_mode: 执行模式（BATCH或QUEUE）
            batch_size: Batch模式下的batch大小，None时使用CPU核心数
            job_executor: 自定义任务执行函数
            on_job_done: 每个 job 完成时的回调（可选）
            progress_report_config: 进度日志上报配置（可选）
            is_main_process_used_if_single_worker: 当 max_workers=1 时，是否使用主进程串行执行（默认 True）
            enable_monitoring: 是否启用监控
            timeout: 任务超时时间（秒）
            is_verbose: 是否启用详细日志输出
            debug: 是否启用调试日志输出
        """
        # 进程数设置
        if max_workers is None:
            self.max_workers = mp.cpu_count()
        else:
            self.max_workers = min(max_workers, mp.cpu_count())
        
        # 执行模式设置
        self.execution_mode = execution_mode
        
        # Batch模式设置
        if execution_mode == ExecutionMode.BATCH:
            if batch_size is None:
                self.batch_size = mp.cpu_count()
            else:
                self.batch_size = max(1, batch_size)
        else:
            self.batch_size = None
        
        self.job_executor = job_executor
        self.on_job_done = on_job_done
        self.progress_report_config = progress_report_config or ProgressReportConfig()
        self.is_main_process_used_if_single_worker = bool(
            is_main_process_used_if_single_worker
        )
        self.enable_monitoring = enable_monitoring
        self.timeout = timeout
        self.is_verbose = is_verbose
        self.debug = debug
        # 进程启动方式：fork/spawn/forkserver
        self.start_method = start_method
        
        # 任务队列
        self.job_queue = []
        self.results = []
        
        # 执行状态
        self.is_running = False
        self.should_stop = False
        
        # 统计信息
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'total_duration': 0.0,
            'start_time': None,
            'end_time': None
        }
        self._last_progress_log_ts: float = 0.0
        self._last_progress_log_pct: int = -1
        
        # 设置信号处理
        self._setup_signal_handlers()
        
        if self.is_verbose:
            mode_desc = f"BATCH (size={self.batch_size})" if execution_mode == ExecutionMode.BATCH else "QUEUE"
            logger.info(f"ProcessWorker initialized: {self.max_workers} workers, mode={mode_desc}")

    def _build_progress_event(
        self,
        *,
        event: str,
        total_jobs: int,
        running_jobs: int = 0,
        last_job_id: str = "",
        last_job_status: str = "",
    ) -> Dict[str, Any]:
        completed_jobs = int(self.stats.get('completed_jobs', 0) or 0)
        failed_jobs = int(self.stats.get('failed_jobs', 0) or 0)
        cancelled_jobs = int(self.stats.get('cancelled_jobs', 0) or 0)
        done_jobs = completed_jobs + failed_jobs + cancelled_jobs
        progress_pct = int((done_jobs / total_jobs) * 100) if total_jobs > 0 else 0
        pending_jobs = max(total_jobs - done_jobs - max(running_jobs, 0), 0)
        return {
            "event": event,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "cancelled_jobs": cancelled_jobs,
            "running_jobs": max(running_jobs, 0),
            "pending_jobs": pending_jobs,
            "progress_pct": progress_pct,
            "last_job_id": str(last_job_id or ""),
            "last_job_status": str(last_job_status or ""),
            "timestamp": datetime.now().isoformat(),
        }

    def _emit_progress_event(
        self,
        *,
        event: str,
        total_jobs: int,
        running_jobs: int = 0,
        last_job_id: str = "",
        last_job_status: str = "",
    ) -> None:
        payload = self._build_progress_event(
            event=event,
            total_jobs=total_jobs,
            running_jobs=running_jobs,
            last_job_id=last_job_id,
            last_job_status=last_job_status,
        )
        if event == "job_finished" and callable(self.on_job_done):
            try:
                self.on_job_done(payload)
            except Exception:
                logger.exception("on_job_done callback failed")
        self._report_progress_log(payload)

    def _report_progress_log(self, payload: Dict[str, Any]) -> None:
        cfg = self.progress_report_config or ProgressReportConfig()
        mode = cfg.mode
        if isinstance(mode, str):
            try:
                mode = ProgressReportMode(mode)
            except Exception:
                mode = ProgressReportMode.NONE

        event = str(payload.get("event") or "")
        total_jobs = int(payload.get("total_jobs", 0) or 0)
        done_jobs = (
            int(payload.get("completed_jobs", 0) or 0)
            + int(payload.get("failed_jobs", 0) or 0)
            + int(payload.get("cancelled_jobs", 0) or 0)
        )
        progress_pct = (done_jobs / total_jobs * 100.0) if total_jobs > 0 else 0.0

        if event == "run_started":
            # 分批执行场景会多次进入 run_started，非首次开始不打日志，避免噪音。
            if done_jobs > 0:
                return
            if cfg.log_on_run_started:
                print(f"任务开始：总任务数={total_jobs}", flush=True)
            return
        if event == "run_finished":
            # 分批执行会触发多次 run_finished，仅在全量完成时输出最终日志。
            if total_jobs > 0 and done_jobs < total_jobs:
                return
            if cfg.log_on_run_finished:
                print(
                    f"任务完成：{progress_pct:.1f}%（{done_jobs}/{total_jobs}），"
                    f"成功={payload.get('completed_jobs', 0)}，"
                    f"失败={payload.get('failed_jobs', 0)}",
                    flush=True,
                )
            return

        if event != "job_finished" or mode == ProgressReportMode.NONE:
            return

        should_log = False
        if mode == ProgressReportMode.EVERY_JOB_DONE:
            should_log = True
        elif mode == ProgressReportMode.EVERY_SEC_INTERVAL:
            interval_seconds = max(float(cfg.interval_seconds or 0), 0.0)
            now_ts = time.time()
            should_log = (
                interval_seconds <= 0
                or (now_ts - self._last_progress_log_ts) >= interval_seconds
            )
            if should_log:
                self._last_progress_log_ts = now_ts
        elif mode == ProgressReportMode.EVERY_PROGRESS_INTERVAL:
            interval_pct = max(int(cfg.interval_pct or 0), 1)
            pct = int(payload.get("progress_pct", 0) or 0)
            if pct >= 100:
                should_log = True
            elif self._last_progress_log_pct < 0:
                should_log = pct >= interval_pct
            else:
                should_log = pct - self._last_progress_log_pct >= interval_pct
            if should_log:
                self._last_progress_log_pct = pct

        if not should_log:
            return

        print(
            f"进度：{progress_pct:.1f}%（{done_jobs}/{total_jobs}），"
            f"成功={payload.get('completed_jobs', 0)}，"
            f"失败={payload.get('failed_jobs', 0)}",
            flush=True,
        )
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            if self.is_verbose:
                logger.info(f"Received signal {signum}, stopping worker...")
            self.should_stop = True
        
        # 让 Ctrl+C 保持默认行为（抛出 KeyboardInterrupt），避免需要多次 Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)
        atexit.register(self._cleanup)
    
    def _cleanup(self):
        """清理资源"""
        if self.is_running:
            self.should_stop = True
            if self.is_verbose:
                logger.info("ProcessWorker cleanup completed")
    
    def set_job_executor(self, job_executor: Callable):
        """设置任务执行函数"""
        self.job_executor = job_executor
        if self.is_verbose:
            logger.info(f"Job executor set: {job_executor.__name__}")
    
    def add_job(self, job_id: str, job_payload: Any):
        """添加单个任务"""
        self.job_queue.append({
            'id': job_id,
            'payload': job_payload
        })
    
    def add_jobs(self, jobs: List[Dict[str, Any]]):
        """批量添加任务"""
        for job in jobs:
            # 兼容旧字段名
            payload = job.get('payload') if 'payload' in job else job.get('data')
            self.add_job(job['id'], payload)
    
    def _create_batches(self) -> List[List[Dict[str, Any]]]:
        """将任务分割成batch"""
        batches = []
        for i in range(0, len(self.job_queue), self.batch_size):
            batch = self.job_queue[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    def _execute_batch_mode(self) -> List[JobResult]:
        """Batch模式执行：batch间串行，batch内并行"""
        all_results = []
        batches = self._create_batches()
        
        if self.is_verbose:
            logger.info(f"Executing in BATCH mode: {len(batches)} batches, batch_size={self.batch_size}")
        
        # 串行执行每个batch
        for batch_idx, batch in enumerate(batches):
            if self.should_stop:
                if self.is_verbose:
                    logger.info("Execution stopped by user")
                break
            
            if self.is_verbose:
                logger.info(f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch)} jobs")
            
            # 并行执行batch内的任务
            batch_results = self._execute_batch_parallel(batch)
            all_results.extend(batch_results)
            
            # 更新统计
            for result in batch_results:
                if result.status == JobStatus.COMPLETED:
                    self.stats['completed_jobs'] += 1
                elif result.status == JobStatus.FAILED:
                    self.stats['failed_jobs'] += 1
            
            if self.is_verbose:
                completed = sum(1 for r in batch_results if r.status == JobStatus.COMPLETED)
                failed = sum(1 for r in batch_results if r.status == JobStatus.FAILED)
                logger.info(f"Batch {batch_idx + 1} completed: {completed} success, {failed} failed")
        
        return all_results
    
    def _execute_queue_mode(self) -> List[JobResult]:
        """队列模式执行：持续填充进程池"""
        all_results = []
        
        if self.is_verbose:
            logger.info(f"Executing in QUEUE mode: {len(self.job_queue)} jobs, max_workers={self.max_workers}")

        total_jobs = self.stats.get('total_jobs', len(self.job_queue))
        self._emit_progress_event(
            event="run_started",
            total_jobs=total_jobs,
            running_jobs=0,
        )

        # max_workers=1 且启用开关时，走主进程串行执行；
        # 若开关关闭，则仍可走单子进程模式（用于隔离场景）。
        if (
            int(self.max_workers or 1) <= 1
            and self.is_main_process_used_if_single_worker
        ):
            for job in self.job_queue:
                if self.should_stop:
                    break
                self._emit_progress_event(
                    event="job_started",
                    total_jobs=total_jobs,
                    running_jobs=1,
                    last_job_id=job.get('id', ''),
                    last_job_status=JobStatus.RUNNING.value,
                )
                try:
                    result = self._execute_single_job(job)
                    all_results.append(result)
                    if result.status == JobStatus.COMPLETED:
                        self.stats['completed_jobs'] += 1
                    elif result.status == JobStatus.FAILED:
                        self.stats['failed_jobs'] += 1
                except Exception as e:
                    error_result = JobResult(
                        job_id=job['id'],
                        status=JobStatus.FAILED,
                        error=str(e),
                        start_time=datetime.now(),
                        end_time=datetime.now()
                    )
                    all_results.append(error_result)
                    self.stats['failed_jobs'] += 1
                    logger.exception(f"Job {job['id']} failed: {e}")

                last_status = all_results[-1].status.value if all_results else JobStatus.FAILED.value
                self._emit_progress_event(
                    event="job_finished",
                    total_jobs=total_jobs,
                    running_jobs=0,
                    last_job_id=job.get('id', ''),
                    last_job_status=last_status,
                )
            self._emit_progress_event(
                event="run_finished",
                total_jobs=total_jobs,
                running_jobs=0,
            )
            return all_results
        
        ctx = mp.get_context(self.start_method)
        executor = None
        try:
            executor = ProcessPoolExecutor(
                max_workers=self.max_workers,
                mp_context=ctx,
            )
            # 提交初始任务到进程池
            future_to_job = {}
            submitted_count = 0
            
            # 初始填充进程池
            while submitted_count < self.max_workers and submitted_count < len(self.job_queue):
                job = self.job_queue[submitted_count]
                future = executor.submit(self._execute_single_job, job)
                future_to_job[future] = job
                submitted_count += 1
                self._emit_progress_event(
                    event="job_started",
                    total_jobs=total_jobs,
                    running_jobs=len(future_to_job),
                    last_job_id=job.get('id', ''),
                    last_job_status=JobStatus.RUNNING.value,
                )
            
            # 持续处理完成的任务并提交新任务
            while future_to_job and not self.should_stop:
                # 等待任意一个任务完成
                from concurrent.futures import wait, FIRST_COMPLETED
                done, not_done = wait(future_to_job.keys(), return_when=FIRST_COMPLETED)
                
                for future in done:
                    finished_job = future_to_job.pop(future)
                    
                    try:
                        result = future.result(timeout=self.timeout)
                        all_results.append(result)
                        
                        # 更新统计
                        if result.status == JobStatus.COMPLETED:
                            self.stats['completed_jobs'] += 1
                        elif result.status == JobStatus.FAILED:
                            self.stats['failed_jobs'] += 1
                        
                    except Exception as e:
                        error_result = JobResult(
                            job_id=finished_job['id'],
                            status=JobStatus.FAILED,
                            error=str(e),
                            start_time=datetime.now(),
                            end_time=datetime.now()
                        )
                        all_results.append(error_result)
                        self.stats['failed_jobs'] += 1
                        try:
                            data_keys = list(finished_job['payload'].keys()) if isinstance(finished_job.get('payload'), dict) else type(finished_job.get('payload')).__name__
                        except Exception:
                            data_keys = 'unknown'
                        logger.exception(f"Job {finished_job['id']} failed: {e} | data_keys={data_keys}")
                    
                    # 提交新任务（如果还有待处理的任务）
                    if submitted_count < len(self.job_queue):
                        next_job = self.job_queue[submitted_count]
                        future = executor.submit(self._execute_single_job, next_job)
                        future_to_job[future] = next_job
                        submitted_count += 1
                        self._emit_progress_event(
                            event="job_started",
                            total_jobs=total_jobs,
                            running_jobs=len(future_to_job),
                            last_job_id=next_job.get('id', ''),
                            last_job_status=JobStatus.RUNNING.value,
                        )
                    finished_result = all_results[-1] if all_results else None
                    self._emit_progress_event(
                        event="job_finished",
                        total_jobs=total_jobs,
                        running_jobs=len(future_to_job),
                        last_job_id=finished_job.get('id', ''),
                        last_job_status=(
                            finished_result.status.value
                            if finished_result is not None
                            else JobStatus.FAILED.value
                        ),
                    )

            # 等待剩余任务完成
            if not self.should_stop:
                for future in as_completed(list(future_to_job.keys())):
                    job = future_to_job.pop(future, None) or {"id": "unknown"}
                    try:
                        result = future.result(timeout=self.timeout)
                        all_results.append(result)
                        
                        if result.status == JobStatus.COMPLETED:
                            self.stats['completed_jobs'] += 1
                        elif result.status == JobStatus.FAILED:
                            self.stats['failed_jobs'] += 1

                    except Exception as e:
                        error_result = JobResult(
                            job_id=job['id'],
                            status=JobStatus.FAILED,
                            error=str(e),
                            start_time=datetime.now(),
                            end_time=datetime.now()
                        )
                        all_results.append(error_result)
                        self.stats['failed_jobs'] += 1
                        logger.error(f"Job {job['id']} failed: {e}")
                    finally:
                        finished_result = all_results[-1] if all_results else None
                        self._emit_progress_event(
                            event="job_finished",
                            total_jobs=total_jobs,
                            running_jobs=len(future_to_job),
                            last_job_id=job.get('id', ''),
                            last_job_status=(
                                finished_result.status.value
                                if finished_result is not None
                                else JobStatus.FAILED.value
                            ),
                        )
        except KeyboardInterrupt:
            self.should_stop = True
            if executor is not None:
                executor.shutdown(cancel_futures=True)
            raise
        finally:
            if executor is not None:
                executor.shutdown(cancel_futures=True)
            self._emit_progress_event(
                event="run_finished",
                total_jobs=total_jobs,
                running_jobs=0,
            )
            
            # 显示最终进度
            completed_count = self.stats['completed_jobs'] + self.stats['failed_jobs']
            if completed_count > 0 and self.is_verbose:
                progress_pct = (completed_count / total_jobs * 100) if total_jobs > 0 else 0
                logger.info(
                    f"✅ 完成: {completed_count}/{total_jobs} ({progress_pct:.1f}%) | "
                    f"成功: {self.stats['completed_jobs']}, 失败: {self.stats['failed_jobs']}"
                )
        
        return all_results
    
    def _execute_batch_parallel(self, batch: List[Dict[str, Any]]) -> List[JobResult]:
        """并行执行单个batch内的任务"""
        batch_results = []
        
        ctx = mp.get_context(self.start_method)
        executor = None
        try:
            executor = ProcessPoolExecutor(
                max_workers=self.max_workers,
                mp_context=ctx,
            )
            # 提交所有任务到进程池
            future_to_job = {
                executor.submit(self._execute_single_job, job): job 
                for job in batch
            }
            
            # 收集结果
            for future in as_completed(future_to_job):
                if self.should_stop:
                    future.cancel()
                    continue
                
                try:
                    result = future.result(timeout=self.timeout)
                    batch_results.append(result)
                except Exception as e:
                    job = future_to_job[future]
                    error_result = JobResult(
                        job_id=job['id'],
                        status=JobStatus.FAILED,
                        error=str(e),
                        start_time=datetime.now(),
                        end_time=datetime.now()
                    )
                    batch_results.append(error_result)
                    try:
                        data_keys = list(job['payload'].keys()) if isinstance(job.get('payload'), dict) else type(job.get('payload')).__name__
                    except Exception:
                        data_keys = 'unknown'
                    logger.exception(f"Job {job['id']} failed: {e} | data_keys={data_keys}")
        except KeyboardInterrupt:
            self.should_stop = True
            if executor is not None:
                executor.shutdown(cancel_futures=True)
            raise
        finally:
            if executor is not None:
                executor.shutdown(cancel_futures=True)
        
        return batch_results
    
    def _execute_single_job(self, job: Dict[str, Any]) -> JobResult:
        """执行单个任务"""
        start_time = datetime.now()
        
        try:
            # 每个子进程内重置 DatabaseManager 默认实例，避免父进程继承的连接池
            # 在 fork + pymysql/DBUtils 场景下，否则容易出现：
            # - "Command Out of Sync"
            # - "Packet sequence number wrong"
            # 等连接状态错误。
            # 仅在子进程中重置 DB 默认实例，避免主进程路径被误重置。
            if mp.current_process().name != "MainProcess":
                try:
                    from core.infra.db import DatabaseManager
                    DatabaseManager.reset_default()
                except Exception:
                    # 重置失败不应影响任务执行本身，最多失去连接池复用
                    pass

            if self.job_executor is None:
                raise ValueError("Job executor not set")
            
            # 执行任务（兼容 'payload' 和 'data' 两种键名）
            payload = job.get('payload') if 'payload' in job else job.get('data')
            if payload is None:
                raise ValueError(f"Job {job.get('id', 'unknown')} missing 'payload' or 'data' key")
            result_data = self.job_executor(payload)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return JobResult(
                job_id=job['id'],
                status=JobStatus.COMPLETED,
                result=result_data,
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_result = JobResult(
                job_id=job['id'],
                status=JobStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
            
            # 始终输出包含trace的异常日志，便于跨服务复用时排查
            try:
                data_summary = job.get('payload')
                if isinstance(data_summary, dict):
                    data_summary = {k: type(v).__name__ for k, v in list(data_summary.items())[:10]}
                else:
                    data_summary = type(data_summary).__name__
            except Exception:
                data_summary = 'unavailable'
            logger.exception(f"Job {job['id']} failed with error: {e} | data_summary={data_summary}")
            
            return error_result
    
    def run_jobs(self, jobs: Optional[List[Dict[str, Any]]] = None, total_jobs: Optional[int] = None) -> Dict[str, Any]:
        """
        执行所有任务
        
        Args:
            jobs: 可选的任务列表，如果不提供则使用已添加的任务
            total_jobs: 总任务数（用于进度跟踪）。如果提供，将使用此值而不是当前批次的大小
                      这对于分批执行时保持准确的进度跟踪很重要
            
        Returns:
            执行统计信息
        """
        # 初始化 is_batch_execution 变量
        is_batch_execution = False
        
        if jobs:
            # 如果提供了 total_jobs，使用它；否则使用当前批次的大小
            # 注意：如果 total_jobs 已设置且不为 None，保持它不变（用于分批执行）
            if total_jobs is not None:
                if not hasattr(self, '_total_jobs') or self._total_jobs is None:
                    self._total_jobs = total_jobs
            else:
                # 如果没有提供 total_jobs，且之前也没有设置，则使用当前批次大小
                if not hasattr(self, '_total_jobs') or self._total_jobs is None:
                    self._total_jobs = len(jobs)
            
            # 检查是否是分批执行（已有统计信息且 total_jobs 大于当前批次大小）
            is_batch_execution = (
                hasattr(self, 'stats') and 
                self.stats and 
                self.stats.get('total_jobs', 0) > 0 and
                hasattr(self, '_total_jobs') and 
                self._total_jobs is not None and
                self._total_jobs > len(jobs)
            )
            
            if is_batch_execution:
                # 分批执行：累积统计信息，不重置
                # 保存之前的完成数，用于累积
                previous_completed = self.stats.get('completed_jobs', 0)
                previous_failed = self.stats.get('failed_jobs', 0)
                previous_start_time = self.stats.get('start_time')
                
                # 更新任务队列
                self.job_queue = jobs
                
                # 累积统计信息（不重置已完成的任务数）
                self.stats = {
                    'total_jobs': self._total_jobs,  # 使用总任务数
                    'completed_jobs': previous_completed,  # 保留之前的完成数
                    'failed_jobs': previous_failed,  # 保留之前的失败数
                    'cancelled_jobs': self.stats.get('cancelled_jobs', 0),
                    'timed_out': False,
                    'not_done_count': 0,
                    'start_time': previous_start_time or datetime.now(),  # 保留开始时间
                    'end_time': None,
                    'total_duration': 0,
                    'avg_duration': 0,
                    'throughput': 0
                }
                # 不清空 results，累积所有批次的结果
                if not hasattr(self, 'results') or self.results is None:
                    self.results = []
                # 重置当前批次结果（每次批次开始时清空）
                self._current_batch_results = None
            else:
                # 首次执行或单次执行：重置状态
                self.job_queue = jobs
                self.stats = {
                    'total_jobs': 0,
                    'completed_jobs': 0,
                    'failed_jobs': 0,
                    'cancelled_jobs': 0,
                    'timed_out': False,
                    'not_done_count': 0,
                    'start_time': None,
                    'end_time': None,
                    'total_duration': 0,
                    'avg_duration': 0,
                    'throughput': 0
                }
                self.results = []
        
        if not self.job_queue:
            if self.is_verbose:
                logger.warning("No jobs to execute")
            return self.stats
        
        if not self.job_executor:
            raise ValueError("Job executor not set")
        
        self.is_running = True
        self.should_stop = False
        self._last_progress_log_ts = 0.0
        self._last_progress_log_pct = -1
        
        # 设置开始时间（如果还没有设置）
        if not self.stats.get('start_time'):
            self.stats['start_time'] = datetime.now()
        
        # 使用保存的总任务数（如果已设置），否则使用当前批次大小
        if hasattr(self, '_total_jobs') and self._total_jobs is not None:
            self.stats['total_jobs'] = self._total_jobs
        else:
            self.stats['total_jobs'] = len(self.job_queue)
        
        if self.is_verbose:
            mode_desc = f"BATCH (size={self.batch_size})" if self.execution_mode == ExecutionMode.BATCH else "QUEUE"
            logger.info(f"Starting execution of {len(self.job_queue)} jobs in {mode_desc} mode")
        
        try:
            # 根据执行模式选择执行方法
            if self.execution_mode == ExecutionMode.BATCH:
                batch_results = self._execute_batch_mode()
            else:
                batch_results = self._execute_queue_mode()
            
            # 累积结果（分批执行时）
            if is_batch_execution:
                if not hasattr(self, 'results') or self.results is None:
                    self.results = []
                self.results.extend(batch_results)
                # 保存当前批次的结果，用于 get_results() 返回
                self._current_batch_results = batch_results
            else:
                self.results = batch_results
                self._current_batch_results = batch_results
        
        except Exception as e:
            logger.error(f"Error during job execution: {e}")
            raise
        finally:
            self.is_running = False
            self.stats['end_time'] = datetime.now()
            if self.stats['start_time']:
                self.stats['total_duration'] = (
                    self.stats['end_time'] - self.stats['start_time']
                ).total_seconds()
        
        return self.stats
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息快照"""
        return dict(self.stats or {})

    def get_results(self) -> List[JobResult]:
        """
        获取任务结果
        
        注意：在分批执行模式下，返回当前批次的结果（避免重复累加）
        在单次执行模式下，返回所有结果
        """
        # 如果存在当前批次结果（分批执行），返回当前批次；否则返回累积结果
        if hasattr(self, '_current_batch_results') and self._current_batch_results is not None:
            return self._current_batch_results
        return self.results if hasattr(self, 'results') and self.results is not None else []
    
    def get_successful_results(self) -> List[JobResult]:
        """获取成功的任务结果"""
        return [r for r in self.results if r.status == JobStatus.COMPLETED]
    
    def get_failed_results(self) -> List[JobResult]:
        """获取失败的任务结果"""
        return [r for r in self.results if r.status == JobStatus.FAILED]
    
    def print_stats(self):
        """打印执行统计信息"""
        if not self.stats['start_time']:
            print("No execution stats available")
            return
        
        print("\n" + "="*50)
        print("ProcessWorker 执行统计")
        print("="*50)
        print(f"执行模式: {self.execution_mode.value}")
        if self.execution_mode == ExecutionMode.BATCH:
            print(f"Batch大小: {self.batch_size}")
        print(f"进程数: {self.max_workers}")
        print(f"总任务数: {self.stats['total_jobs']}")
        print(f"成功任务: {self.stats['completed_jobs']}")
        print(f"失败任务: {self.stats['failed_jobs']}")
        print(f"总耗时: {self.stats['total_duration']:.2f}秒")
        
        if self.stats['total_jobs'] > 0:
            success_rate = (self.stats['completed_jobs'] / self.stats['total_jobs']) * 100
            print(f"成功率: {success_rate:.1f}%")
        
        if self.stats['completed_jobs'] > 0:
            avg_duration = self.stats['total_duration'] / self.stats['completed_jobs']
            print(f"平均任务耗时: {avg_duration:.2f}秒")
        
        print("="*50)
    
    def reset(self):
        """重置执行器状态"""
        self.job_queue = []
        self.results = []
        self.is_running = False
        self.should_stop = False
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'total_duration': 0.0,
            'start_time': None,
            'end_time': None
        }
        self._last_progress_log_ts = 0.0
        self._last_progress_log_pct = -1
        if self.is_verbose:
            logger.info("ProcessWorker reset completed")
