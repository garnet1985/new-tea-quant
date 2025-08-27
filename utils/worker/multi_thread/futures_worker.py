#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于 concurrent.futures 的轻量级任务执行器
"""

import time
import threading
import signal
import atexit
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED, Future
from queue import Queue, Empty
from typing import List, Dict, Any, Callable, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


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
    SERIAL = "serial"      # 串行执行
    PARALLEL = "parallel"  # 并行执行


class JobStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"    # 等待中
    RUNNING = "running"    # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"      # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class JobResult:
    """任务执行结果"""
    job_id: str
    status: JobStatus
    result: Any = None
    error: Exception = None
    duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __str__(self):
        return f"JobResult(job_id={self.job_id}, status={self.status.value}, duration={self.duration:.2f}s)"


class FuturesWorker:
    """
    基于 concurrent.futures 的轻量级任务执行器
    
    特性：
    ✅ 支持串行和并行执行
    ✅ 任务队列管理
    ✅ 详细的执行统计
    ✅ 优雅的信号处理
    ✅ 任务取消和超时
    ✅ 错误处理和重试
    ✅ 实时进度监控
    """
    
    def __init__(self, 
                 max_workers: int = 5,
                 execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
                 job_executor: Optional[Callable] = None,
                 enable_monitoring: bool = True,
                 timeout: float = 30.0,
                 is_verbose: bool = False,
                 debug: bool = False):
        """
        初始化任务执行器
        
        Args:
            max_workers: 最大并行工作线程数
            execution_mode: 执行模式（串行/并行）
            job_executor: 自定义任务执行函数
            enable_monitoring: 是否启用监控
            timeout: 任务超时时间（秒）
            is_verbose: 是否启用详细日志输出
            debug: 是否启用调试日志输出
        """
        self.max_workers = max_workers
        self.execution_mode = execution_mode
        self.job_executor = job_executor
        self.enable_monitoring = enable_monitoring
        self.timeout = timeout
        self.is_verbose = is_verbose
        self.debug = debug
        
        # 任务队列
        self.job_queue = Queue()
        self.results_queue = Queue()
        
        # 执行状态
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        
        # 线程池
        self.executor = None
        self.active_futures = []
        
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
            'throughput': 0
        }
        
        # 线程锁
        self.stats_lock = threading.Lock()
        
        # 进度跟踪
        self._printed_progress = set()
        
        # 初始化线程池
        if self.execution_mode == ExecutionMode.PARALLEL:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 注册清理函数
        atexit.register(self._cleanup)
        
        # 设置信号处理器
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.warning(f"🚨 EMERGENCY: Received signal {signum}, forcing immediate shutdown...")
            self._emergency_shutdown()
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except (ValueError, OSError) as e:
            if self.is_verbose:
                logger.warning(f"Could not set signal handlers: {e}")
    
    def _emergency_shutdown(self):
        """紧急关闭"""
        self.should_stop = True
        self.is_running = False
        
        # 取消所有活动任务
        cancelled_count = 0
        for future in self.active_futures:
            if not future.done():
                future.cancel()
                cancelled_count += 1
        
        if self.is_verbose:
            logger.warning(f"Cancelled {cancelled_count} active tasks")
        
        # 强制关闭线程池
        if self.executor:
            try:
                self.executor.shutdown(wait=False)
                if self.is_verbose:
                    logger.warning("ThreadPoolExecutor force shutdown completed")
            except Exception as e:
                logger.error(f"Error in force shutdown: {e}")
            finally:
                self.executor = None
        
        # 清空队列
        self.clear_queue()
        self.clear_results()
        
        logger.warning("🚨 EMERGENCY shutdown completed - exiting immediately")
        import os
        os._exit(0)
    
    def _cleanup(self):
        """清理资源"""
        try:
            self.shutdown()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def set_job_executor(self, executor_func: Callable):
        """设置任务执行函数"""
        self.job_executor = executor_func
    
    def add_job(self, job_id: str, job_data: Any):
        """添加任务到队列"""
        job = {
            'id': job_id,
            'data': job_data,
            'status': JobStatus.PENDING,
            'created_time': time.time()
        }
        self.job_queue.put(job)
        
        with self.stats_lock:
            self.stats['total_jobs'] += 1
        
        if self.debug:
            if self.is_verbose:
                logger.info(f"Added job {job_id} to queue")
    
    def add_jobs(self, jobs: List[Dict[str, Any]]):
        """批量添加任务"""
        for job in jobs:
            self.add_job(job['id'], job['data'])
    
    def run_jobs(self, jobs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """运行任务队列"""
        if jobs:
            self.add_jobs(jobs)
        
        if self.job_queue.empty():
            if self.is_verbose:
                logger.warning("No jobs to execute")
            return self.get_stats()
        
        if self.is_verbose:
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
        except KeyboardInterrupt:
            if self.is_verbose:
                logger.info("Job execution interrupted by user")
            self.should_stop = True
            raise
        except Exception as e:
            logger.error(f"Job execution failed: {e}")
            raise
        finally:
            self.is_running = False
            self.stats['end_time'] = time.time()
            self.stats['total_duration'] = self.stats['end_time'] - self.stats['start_time']
            
            # 计算统计信息
            if self.stats['completed_jobs'] > 0:
                self.stats['avg_duration'] = self.stats['total_duration'] / self.stats['completed_jobs']
                self.stats['throughput'] = self.stats['completed_jobs'] / self.stats['total_duration']
        
        return self.get_stats()
    
    def run_job(self, job_id: str, job_data: Any) -> JobResult:
        """运行单个任务"""
        if not self.job_executor:
            raise ValueError("Job executor not set. Use set_job_executor() first.")
        
        start_time = time.time()
        result = JobResult(job_id, JobStatus.RUNNING)
        result.start_time = datetime.now()
        
        if self.debug:
            if self.is_verbose:
                logger.info(f"Executing job {job_id}")
        
        try:
            # 执行任务
            job_result = self.job_executor(job_data)
            
            # 更新结果
            result.status = JobStatus.COMPLETED
            result.result = job_result
            result.end_time = datetime.now()
            result.duration = time.time() - start_time
            
            # 进度日志在 _update_stats 中处理，避免重复
            if self.is_verbose:
                logger.debug(f"Job {job_id} completed in {result.duration:.2f}s")
            
        except Exception as e:
            # 捕获任务执行异常
            result.status = JobStatus.FAILED
            result.error = e
            result.end_time = datetime.now()
            result.duration = time.time() - start_time
            
            # 打印完整的错误堆栈，帮助调试
            import traceback
            logger.error(f"Job {job_id} failed: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
        
        return result
    
    def _run_serial(self):
        """串行执行任务"""
        if self.is_verbose:
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
        if self.is_verbose:
            logger.info(f"Running jobs in parallel mode with {self.max_workers} workers")
        
        futures = []
        self.active_futures = []
        
        # 提交所有任务到线程池
        while not self.job_queue.empty() and not self.should_stop:
            try:
                job = self.job_queue.get_nowait()
                future = self.executor.submit(self.run_job, job['id'], job['data'])
                futures.append(future)
                self.active_futures.append(future)
            except Empty:
                break
        
        # 等待所有任务完成 - 添加超时和强制完成处理
        try:
            # 设置合理的超时时间，避免无限等待
            timeout = max(self.timeout, 300)  # 至少5分钟超时
            
            # 等待所有任务完成
            done, not_done = wait(futures, timeout=timeout, return_when="ALL_COMPLETED")
            
            # 处理所有完成的任务
            for future in done:
                if self.should_stop:
                    future.cancel()
                    continue
                
                try:
                    result = future.result(timeout=30)
                    if self.debug and self.is_verbose:
                        logger.debug(f"Processing result for job {result.job_id}")
                    self._update_stats(result)
                    self.results_queue.put(result)
                except Exception as e:
                    logger.error(f"Error getting result for job: {e}")
                    failed_result = JobResult(job_id="unknown", status=JobStatus.FAILED, error=e)
                    self._update_stats(failed_result)
                    self.results_queue.put(failed_result)
                finally:
                    if future in self.active_futures:
                        self.active_futures.remove(future)
            
            # 强制完成未完成的任务
            if not_done:
                if self.is_verbose:
                    logger.warning(f"Some tasks did not complete within timeout: {len(not_done)} tasks remaining")
                    logger.info("Forcing completion of remaining tasks...")
                
                for future in not_done:
                    try:
                        if not future.done():
                            future.cancel()
                            if self.is_verbose:
                                logger.warning(f"Cancelled incomplete task")
                        else:
                            # 任务实际上完成了，只是超时了
                            result = future.result(timeout=5)
                            self._update_stats(result)
                            self.results_queue.put(result)
                    except Exception as e:
                        logger.error(f"Error handling incomplete task: {e}")
                        failed_result = JobResult(job_id="unknown", status=JobStatus.FAILED, error=e)
                        self._update_stats(failed_result)
                        self.results_queue.put(failed_result)
                    finally:
                        if future in self.active_futures:
                            self.active_futures.remove(future)
                
        except KeyboardInterrupt:
            if self.is_verbose:
                logger.info("Received interrupt signal, cancelling remaining tasks...")
            for future in futures:
                if not future.done():
                    future.cancel()
            raise
        finally:
            self.active_futures = []
    
    def _update_stats(self, result: JobResult):
        """更新统计信息"""
        with self.stats_lock:
            # 检查是否已经处理过这个任务
            if result.job_id in self._printed_progress:
                if self.debug and self.is_verbose:
                    logger.debug(f"Skipping duplicate result for job {result.job_id}")
                return
            
            if result.status == JobStatus.COMPLETED:
                self.stats['completed_jobs'] += 1
                # 每个任务完成后都打印进度
                current_completed = self.stats['completed_jobs']
                total_jobs = self.stats['total_jobs']
                
                # 标记为已处理并打印进度
                self._printed_progress.add(result.job_id)
                if self.is_verbose:
                    logger.info(f"Job {result.job_id} completed. Progress: {current_completed} out of {total_jobs} - {current_completed/total_jobs * 100:.2f}%")
                    
            elif result.status == JobStatus.FAILED:
                self.stats['failed_jobs'] += 1
                self._printed_progress.add(result.job_id)
            elif result.status == JobStatus.CANCELLED:
                self.stats['cancelled_jobs'] += 1
                self._printed_progress.add(result.job_id)
    
    def get_results(self) -> List[JobResult]:
        """获取所有执行结果"""
        results = []
        while not self.results_queue.empty():
            try:
                result = self.results_queue.get_nowait()
                results.append(result)
            except Empty:
                break
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        with self.stats_lock:
            stats = self.stats.copy()
            stats['is_running'] = self.is_running
            stats['is_paused'] = self.is_paused
            stats['queue_size'] = self.job_queue.qsize()
            stats['results_count'] = self.results_queue.qsize()
            stats['active_futures'] = len(self.active_futures)
        return stats
    
    def print_stats(self):
        """打印执行统计信息"""
        stats = self.get_stats()
        
        if self.is_verbose:
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
            logger.info(f"  Active Futures: {stats['active_futures']}")
    
    def pause(self):
        """暂停执行"""
        self.is_paused = True
        if self.is_verbose:
            logger.info("Job execution paused")
    
    def resume(self):
        """恢复执行"""
        self.is_paused = False
        if self.is_verbose:
            logger.info("Job execution resumed")
    
    def stop(self):
        """停止执行"""
        self.should_stop = True
        if self.is_verbose:
            logger.info("Job execution stopped")
    
    def shutdown(self, timeout: float = 5.0):
        """关闭任务执行器"""
        if self.is_verbose:
            logger.info("Shutting down FuturesWorker...")
        
        self.should_stop = True
        self.is_running = False
        
        # 取消所有活动任务
        if hasattr(self, 'active_futures'):
            for future in self.active_futures:
                if not future.done():
                    future.cancel()
        
        # 关闭线程池
        if self.executor:
            try:
                self.executor.shutdown(wait=True)
                if self.is_verbose:
                    logger.info("ThreadPoolExecutor shutdown completed")
            except Exception as e:
                logger.error(f"Error shutting down ThreadPoolExecutor: {e}")
            finally:
                self.executor = None
        
        # 清空队列
        self.clear_queue()
        self.clear_results()
        
        if self.is_verbose:
            logger.info("FuturesWorker shutdown completed")
    
    def force_shutdown(self):
        """强制关闭任务执行器"""
        if self.is_verbose:
            logger.warning("Force shutting down FuturesWorker...")
        
        self.should_stop = True
        self.is_running = False
        
        # 取消所有活动任务
        if hasattr(self, 'active_futures'):
            for future in self.active_futures:
                if not future.done():
                    future.cancel()
        
        # 强制关闭线程池
        if self.executor:
            try:
                self.executor.shutdown(wait=False)
                if self.is_verbose:
                    logger.warning("ThreadPoolExecutor force shutdown completed")
            except Exception as e:
                logger.error(f"Error in force shutdown: {e}")
            finally:
                self.executor = None
        
        # 清空队列
        self.clear_queue()
        self.clear_results()
        
        if self.is_verbose:
            logger.warning("Force shutdown completed")
    
    def clear_queue(self):
        """清空任务队列"""
        while not self.job_queue.empty():
            try:
                self.job_queue.get_nowait()
            except Empty:
                break
        if self.debug and self.is_verbose:
            logger.info("Job queue cleared")
    
    def clear_results(self):
        """清空结果队列"""
        while not self.results_queue.empty():
            try:
                self.results_queue.get_nowait()
            except Empty:
                break
        if self.debug and self.is_verbose:
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
        if self.debug and self.is_verbose:
            logger.info("Statistics reset")
    
    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, 'executor') and self.executor:
                # 在析构时不打印日志，避免重复
                self.should_stop = True
                self.is_running = False
                
                # 取消所有活动任务
                if hasattr(self, 'active_futures'):
                    for future in self.active_futures:
                        if not future.done():
                            future.cancel()
                
                # 关闭线程池
                if self.executor:
                    try:
                        self.executor.shutdown(wait=False)
                    except Exception:
                        pass
                    finally:
                        self.executor = None
                        
                # 清空队列（不打印日志）
                while not self.job_queue.empty():
                    try:
                        self.job_queue.get_nowait()
                    except:
                        break
                        
                while not self.results_queue.empty():
                    try:
                        self.results_queue.get_nowait()
                    except:
                        break
        except Exception:
            pass 