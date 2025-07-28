#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通用任务执行器
支持串行和并行执行，可自定义任务执行逻辑
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
from typing import List, Dict, Any, Callable, Optional
from enum import Enum
from loguru import logger


class ExecutionMode(Enum):
    """执行模式枚举"""
    SERIAL = "serial"      # 串行执行
    PARALLEL = "parallel"  # 并行执行


class JobStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"    # 等待中
    RUNNING = "running"    # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"      # 失败
    CANCELLED = "cancelled"  # 已取消


class JobResult:
    """任务执行结果"""
    
    def __init__(self, job_id: str, status: JobStatus, result: Any = None, error: Exception = None, duration: float = 0):
        self.job_id = job_id
        self.status = status
        self.result = result
        self.error = error
        self.duration = duration
        self.start_time = None
        self.end_time = None
    
    def __str__(self):
        return f"JobResult(job_id={self.job_id}, status={self.status.value}, duration={self.duration:.2f}s)"


class JobWorker:
    """
    通用任务执行器
    
    特性：
    1. 支持串行和并行执行模式
    2. 可自定义任务执行逻辑
    3. 支持任务队列管理
    4. 提供详细的执行统计和监控
    5. 支持任务取消和暂停
    """
    
    def __init__(self, 
                 max_workers: int = 5,
                 execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
                 job_executor: Optional[Callable] = None,
                 enable_monitoring: bool = True):
        """
        初始化任务执行器
        
        Args:
            max_workers: 最大并行工作线程数（仅在并行模式下有效）
            execution_mode: 执行模式（串行/并行）
            job_executor: 自定义任务执行函数
            enable_monitoring: 是否启用监控
        """
        self.max_workers = max_workers
        self.execution_mode = execution_mode
        self.job_executor = job_executor
        self.enable_monitoring = enable_monitoring
        
        # 任务队列
        self.job_queue = Queue()
        self.results_queue = Queue()
        
        # 执行状态
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        
        # 统计信息
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0,
            'start_time': None,
            'end_time': None,
            'total_duration': 0,
            'avg_duration': 0,
            'throughput': 0  # 任务/秒
        }
        
        # 线程锁
        self.stats_lock = threading.Lock()
        
        # 线程池（仅在并行模式下使用）
        self.executor = None
        if self.execution_mode == ExecutionMode.PARALLEL:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def set_job_executor(self, executor_func: Callable):
        """
        设置自定义任务执行函数
        
        Args:
            executor_func: 任务执行函数，签名应为 func(job_data) -> Any
        """
        self.job_executor = executor_func
    
    def add_job(self, job_id: str, job_data: Any):
        """
        添加任务到队列
        
        Args:
            job_id: 任务ID
            job_data: 任务数据
        """
        job = {
            'id': job_id,
            'data': job_data,
            'status': JobStatus.PENDING,
            'created_time': time.time()
        }
        self.job_queue.put(job)
        
        with self.stats_lock:
            self.stats['total_jobs'] += 1
        
        logger.debug(f"Added job {job_id} to queue")
    
    def add_jobs(self, jobs: List[Dict[str, Any]]):
        """
        批量添加任务
        
        Args:
            jobs: 任务列表，每个任务应包含 'id' 和 'data' 字段
        """
        for job in jobs:
            self.add_job(job['id'], job['data'])
    
    def run_jobs(self, jobs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        运行任务队列
        
        Args:
            jobs: 可选的任务列表，如果不提供则使用队列中的任务
            
        Returns:
            Dict: 执行统计信息
        """
        if jobs:
            self.add_jobs(jobs)
        
        if self.job_queue.empty():
            logger.warning("No jobs to execute")
            return self.get_stats()
        
        logger.info(f"Starting job execution in {self.execution_mode.value} mode")
        logger.info(f"Total jobs: {self.stats['total_jobs']}")
        
        self.is_running = True
        self.should_stop = False
        self.stats['start_time'] = time.time()
        
        try:
            if self.execution_mode == ExecutionMode.SERIAL:
                self._run_serial()
            else:
                self._run_parallel()
        except Exception as e:
            logger.error(f"Job execution failed: {e}")
            raise
        finally:
            self.is_running = False
            self.stats['end_time'] = time.time()
            self.stats['total_duration'] = self.stats['end_time'] - self.stats['start_time']
            
            # 计算平均执行时间和吞吐量
            if self.stats['completed_jobs'] > 0:
                self.stats['avg_duration'] = self.stats['total_duration'] / self.stats['completed_jobs']
                self.stats['throughput'] = self.stats['completed_jobs'] / self.stats['total_duration']
        
        return self.get_stats()
    
    def run_job(self, job_id: str, job_data: Any) -> JobResult:
        """
        运行单个任务
        
        Args:
            job_id: 任务ID
            job_data: 任务数据
            
        Returns:
            JobResult: 任务执行结果
        """
        if not self.job_executor:
            raise ValueError("Job executor not set. Use set_job_executor() first.")
        
        start_time = time.time()
        result = JobResult(job_id, JobStatus.RUNNING)
        result.start_time = start_time
        
        try:
            logger.debug(f"Executing job {job_id}")
            
            # 执行任务
            job_result = self.job_executor(job_data)
            
            # 更新结果
            result.status = JobStatus.COMPLETED
            result.result = job_result
            result.end_time = time.time()
            result.duration = result.end_time - start_time
            
            logger.debug(f"Job {job_id} completed in {result.duration:.2f}s")
            
        except Exception as e:
            result.status = JobStatus.FAILED
            result.error = e
            result.end_time = time.time()
            result.duration = result.end_time - start_time
            
            logger.error(f"Job {job_id} failed: {e}")
        
        return result
    
    def _run_serial(self):
        """串行执行任务"""
        logger.info("Running jobs in serial mode")
        
        while not self.job_queue.empty() and not self.should_stop:
            if self.is_paused:
                time.sleep(0.1)
                continue
            
            try:
                job = self.job_queue.get_nowait()
                result = self.run_job(job['id'], job['data'])
                self._update_stats(result)
                self.results_queue.put(result)
                
            except Empty:
                break
            except Exception as e:
                logger.error(f"Error in serial execution: {e}")
    
    def _run_parallel(self):
        """并行执行任务"""
        logger.info(f"Running jobs in parallel mode with {self.max_workers} workers")
        
        futures = []
        
        # 提交所有任务到线程池
        while not self.job_queue.empty() and not self.should_stop:
            try:
                job = self.job_queue.get_nowait()
                future = self.executor.submit(self.run_job, job['id'], job['data'])
                futures.append(future)
            except Empty:
                break
        
        # 等待所有任务完成
        for future in as_completed(futures):
            if self.should_stop:
                future.cancel()
                continue
            
            try:
                result = future.result()
                self._update_stats(result)
                self.results_queue.put(result)
            except Exception as e:
                logger.error(f"Error in parallel execution: {e}")
    
    def _update_stats(self, result: JobResult):
        """更新统计信息"""
        with self.stats_lock:
            if result.status == JobStatus.COMPLETED:
                self.stats['completed_jobs'] += 1
            elif result.status == JobStatus.FAILED:
                self.stats['failed_jobs'] += 1
            elif result.status == JobStatus.CANCELLED:
                self.stats['cancelled_jobs'] += 1
    
    def get_results(self) -> List[JobResult]:
        """
        获取所有执行结果
        
        Returns:
            List[JobResult]: 任务执行结果列表
        """
        results = []
        while not self.results_queue.empty():
            try:
                result = self.results_queue.get_nowait()
                results.append(result)
            except Empty:
                break
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Returns:
            Dict: 统计信息
        """
        with self.stats_lock:
            stats = self.stats.copy()
            stats['is_running'] = self.is_running
            stats['is_paused'] = self.is_paused
            stats['queue_size'] = self.job_queue.qsize()
            stats['results_count'] = self.results_queue.qsize()
        return stats
    
    def print_stats(self):
        """打印执行统计信息"""
        stats = self.get_stats()
        
        logger.info("📊 Job Execution Statistics:")
        logger.info(f"  Total Jobs: {stats['total_jobs']}")
        logger.info(f"  Completed: {stats['completed_jobs']}")
        logger.info(f"  Failed: {stats['failed_jobs']}")
        logger.info(f"  Cancelled: {stats['cancelled_jobs']}")
        logger.info(f"  Success Rate: {stats['completed_jobs']/stats['total_jobs']*100:.1f}%" if stats['total_jobs'] > 0 else "  Success Rate: N/A")
        logger.info(f"  Total Duration: {stats['total_duration']:.2f}s")
        logger.info(f"  Average Duration: {stats['avg_duration']:.2f}s")
        logger.info(f"  Throughput: {stats['throughput']:.2f} jobs/s")
        logger.info(f"  Queue Size: {stats['queue_size']}")
        logger.info(f"  Results Count: {stats['results_count']}")
    
    def pause(self):
        """暂停执行"""
        self.is_paused = True
        logger.info("Job execution paused")
    
    def resume(self):
        """恢复执行"""
        self.is_paused = False
        logger.info("Job execution resumed")
    
    def stop(self):
        """停止执行"""
        self.should_stop = True
        logger.info("Job execution stopped")
    
    def clear_queue(self):
        """清空任务队列"""
        while not self.job_queue.empty():
            try:
                self.job_queue.get_nowait()
            except Empty:
                break
        logger.info("Job queue cleared")
    
    def clear_results(self):
        """清空结果队列"""
        while not self.results_queue.empty():
            try:
                self.results_queue.get_nowait()
            except Empty:
                break
        logger.info("Results queue cleared")
    
    def reset_stats(self):
        """重置统计信息"""
        with self.stats_lock:
            self.stats = {
                'total_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'cancelled_jobs': 0,
                'start_time': None,
                'end_time': None,
                'total_duration': 0,
                'avg_duration': 0,
                'throughput': 0
            }
        logger.info("Statistics reset")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        if self.executor:
            self.executor.shutdown(wait=True) 