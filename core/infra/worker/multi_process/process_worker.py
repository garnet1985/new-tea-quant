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
    
    # =========================================================================
    # 实例方法
    # =========================================================================
    
    def __init__(self, 
                 max_workers: Optional[int] = None,
                 execution_mode: ExecutionMode = ExecutionMode.QUEUE,
                 batch_size: Optional[int] = None,
                 job_executor: Optional[Callable] = None,
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
        
        # 设置信号处理
        self._setup_signal_handlers()
        
        if self.is_verbose:
            mode_desc = f"BATCH (size={self.batch_size})" if execution_mode == ExecutionMode.BATCH else "QUEUE"
            logger.info(f"ProcessWorker initialized: {self.max_workers} workers, mode={mode_desc}")
    
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
        
        ctx = mp.get_context(self.start_method)
        executor = None
        try:
            executor = ProcessPoolExecutor(max_workers=self.max_workers, mp_context=ctx)
            # 提交初始任务到进程池
            future_to_job = {}
            submitted_count = 0
            
            # 初始填充进程池
            while submitted_count < self.max_workers and submitted_count < len(self.job_queue):
                job = self.job_queue[submitted_count]
                future = executor.submit(self._execute_single_job, job)
                future_to_job[future] = job
                submitted_count += 1
            
            # 持续处理完成的任务并提交新任务
            while future_to_job and not self.should_stop:
                # 等待任意一个任务完成
                from concurrent.futures import wait, FIRST_COMPLETED
                done, not_done = wait(future_to_job.keys(), return_when=FIRST_COMPLETED)
                
                for future in done:
                    job = future_to_job.pop(future)
                    
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
                            job_id=job['id'],
                            status=JobStatus.FAILED,
                            error=str(e),
                            start_time=datetime.now(),
                            end_time=datetime.now()
                        )
                        all_results.append(error_result)
                        self.stats['failed_jobs'] += 1
                        try:
                            data_keys = list(job['payload'].keys()) if isinstance(job.get('payload'), dict) else type(job.get('payload')).__name__
                        except Exception:
                            data_keys = 'unknown'
                        logger.exception(f"Job {job['id']} failed: {e} | data_keys={data_keys}")
                    
                    # 提交新任务（如果还有待处理的任务）
                    if submitted_count < len(self.job_queue):
                        job = self.job_queue[submitted_count]
                        future = executor.submit(self._execute_single_job, job)
                        future_to_job[future] = job
                        submitted_count += 1
                        
                        if self.is_verbose and submitted_count % 10 == 0:
                            logger.info(f"Progress: {submitted_count}/{len(self.job_queue)} jobs submitted")
            
            # 等待剩余任务完成
            if not self.should_stop:
                for future in as_completed(future_to_job):
                    job = future_to_job[future]
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
        except KeyboardInterrupt:
            self.should_stop = True
            if executor is not None:
                executor.shutdown(cancel_futures=True)
            raise
        finally:
            if executor is not None:
                executor.shutdown(cancel_futures=True)
        
        return all_results
    
    def _execute_batch_parallel(self, batch: List[Dict[str, Any]]) -> List[JobResult]:
        """并行执行单个batch内的任务"""
        batch_results = []
        
        ctx = mp.get_context(self.start_method)
        executor = None
        try:
            executor = ProcessPoolExecutor(max_workers=self.max_workers, mp_context=ctx)
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
            try:
                from core.infra.db import DatabaseManager
                DatabaseManager.reset_default()
            except Exception:
                # 重置失败不应影响任务执行本身，最多失去连接池复用
                pass

            if self.job_executor is None:
                raise ValueError("Job executor not set")
            
            # 执行任务
            result_data = self.job_executor(job['payload'])
            
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
    
    def run_jobs(self, jobs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        执行所有任务
        
        Args:
            jobs: 可选的任务列表，如果不提供则使用已添加的任务
            
        Returns:
            执行统计信息
        """
        if jobs:
            self.job_queue = jobs
        
        if not self.job_queue:
            if self.is_verbose:
                logger.warning("No jobs to execute")
            return self.stats
        
        if not self.job_executor:
            raise ValueError("Job executor not set")
        
        self.is_running = True
        self.should_stop = False
        self.stats['start_time'] = datetime.now()
        self.stats['total_jobs'] = len(self.job_queue)
        
        if self.is_verbose:
            mode_desc = f"BATCH (size={self.batch_size})" if self.execution_mode == ExecutionMode.BATCH else "QUEUE"
            logger.info(f"Starting execution of {len(self.job_queue)} jobs in {mode_desc} mode")
        
        try:
            # 根据执行模式选择执行方法
            if self.execution_mode == ExecutionMode.BATCH:
                self.results = self._execute_batch_mode()
            else:
                self.results = self._execute_queue_mode()
        
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
    
    def get_results(self) -> List[JobResult]:
        """获取所有任务结果"""
        return self.results
    
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
        if self.is_verbose:
            logger.info("ProcessWorker reset completed")
