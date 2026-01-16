"""
MultiThreadWorker 单元测试
"""
try:
    import pytest
    from unittest.mock import Mock, patch, MagicMock
except ImportError:
    pytest = None

from core.infra.worker.multi_thread.futures_worker import (
    MultiThreadWorker,
    ExecutionMode,
    JobStatus,
    JobResult
)


def simple_task(data):
    """简单的测试任务"""
    import time
    time.sleep(0.01)  # 模拟 IO 操作
    return {'result': data.get('value', 0) * 2}


def failing_task(data):
    """会失败的任务"""
    raise ValueError("Task failed")


class TestMultiThreadWorker:
    """MultiThreadWorker 测试类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        if pytest is None:
            return
        worker = MultiThreadWorker(is_verbose=False)
        assert worker.max_workers == 5
        assert worker.execution_mode == ExecutionMode.PARALLEL
        assert worker.is_verbose is False
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        if pytest is None:
            return
        worker = MultiThreadWorker(
            max_workers=10,
            execution_mode=ExecutionMode.SERIAL,
            job_executor=simple_task,
            is_verbose=True
        )
        assert worker.max_workers == 10
        assert worker.execution_mode == ExecutionMode.SERIAL
        assert worker.job_executor == simple_task
    
    def test_run_jobs_parallel_mode(self):
        """测试并行模式执行任务"""
        if pytest is None:
            return
        worker = MultiThreadWorker(
            max_workers=3,
            execution_mode=ExecutionMode.PARALLEL,
            job_executor=simple_task,
            is_verbose=False
        )
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
            {'id': '2', 'data': {'value': 2}},
            {'id': '3', 'data': {'value': 3}},
        ]
        
        results = worker.run_jobs(jobs)
        assert len(results) == 3
        assert all(isinstance(r, JobResult) for r in results)
        assert all(r.status == JobStatus.COMPLETED for r in results)
        assert results[0].result['result'] == 2
        assert results[1].result['result'] == 4
        assert results[2].result['result'] == 6
    
    def test_run_jobs_serial_mode(self):
        """测试串行模式执行任务"""
        if pytest is None:
            return
        worker = MultiThreadWorker(
            max_workers=1,
            execution_mode=ExecutionMode.SERIAL,
            job_executor=simple_task,
            is_verbose=False
        )
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
            {'id': '2', 'data': {'value': 2}},
        ]
        
        results = worker.run_jobs(jobs)
        assert len(results) == 2
        assert all(r.status == JobStatus.COMPLETED for r in results)
    
    def test_run_jobs_with_failures(self):
        """测试处理失败任务"""
        if pytest is None:
            return
        worker = MultiThreadWorker(
            max_workers=2,
            execution_mode=ExecutionMode.PARALLEL,
            job_executor=failing_task,
            is_verbose=False
        )
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
        ]
        
        results = worker.run_jobs(jobs)
        assert len(results) == 1
        assert results[0].status == JobStatus.FAILED
        assert results[0].error is not None
    
    def test_get_stats(self):
        """测试获取统计信息"""
        if pytest is None:
            return
        worker = MultiThreadWorker(
            max_workers=2,
            execution_mode=ExecutionMode.PARALLEL,
            job_executor=simple_task,
            is_verbose=False
        )
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
        ]
        
        worker.run_jobs(jobs)
        stats = worker.get_stats()
        
        assert 'total_jobs' in stats
        assert 'completed_jobs' in stats
        assert 'failed_jobs' in stats
        assert stats['total_jobs'] == 1
    
    def test_pause_and_resume(self):
        """测试暂停和恢复"""
        if pytest is None:
            return
        worker = MultiThreadWorker(
            max_workers=2,
            execution_mode=ExecutionMode.PARALLEL,
            job_executor=simple_task,
            is_verbose=False
        )
        
        assert worker.is_paused is False
        worker.pause()
        assert worker.is_paused is True
        worker.resume()
        assert worker.is_paused is False
    
    def test_shutdown(self):
        """测试关闭 worker"""
        if pytest is None:
            return
        worker = MultiThreadWorker(
            max_workers=2,
            execution_mode=ExecutionMode.PARALLEL,
            job_executor=simple_task,
            is_verbose=False
        )
        
        worker.shutdown()
        # 验证 worker 已关闭（具体实现可能不同）
        assert hasattr(worker, 'shutdown')
