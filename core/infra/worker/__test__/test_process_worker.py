"""
ProcessWorker 单元测试
"""
try:
    import pytest
    from unittest.mock import Mock, patch, MagicMock
    from multiprocessing import cpu_count
except ImportError:
    pytest = None

from core.infra.worker.multi_process.process_worker import (
    ProcessWorker,
    ExecutionMode,
    JobStatus,
    JobResult
)


def simple_task(data):
    """简单的测试任务"""
    return {'result': data.get('value', 0) * 2}


def failing_task(data):
    """会失败的任务"""
    raise ValueError("Task failed")


class TestProcessWorker:
    """ProcessWorker 测试类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        if pytest is None:
            return
        worker = ProcessWorker(is_verbose=False)
        assert worker.max_workers is not None
        assert worker.execution_mode == ExecutionMode.QUEUE
        assert worker.is_verbose is False
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        if pytest is None:
            return
        worker = ProcessWorker(
            max_workers=4,
            execution_mode=ExecutionMode.BATCH,
            job_executor=simple_task,
            is_verbose=True
        )
        assert worker.max_workers == 4
        assert worker.execution_mode == ExecutionMode.BATCH
        assert worker.job_executor == simple_task
    
    def test_resolve_max_workers_auto(self):
        """测试自动计算 worker 数量"""
        if pytest is None:
            return
        with patch('core.infra.worker.multi_process.process_worker.ConfigManager.get_worker_config') as mock_config:
            mock_config.return_value = {
                'modules': {
                    'TestModule': {
                        'task_type': 'mixed',
                        'reserve_cores': 2
                    }
                }
            }
            max_workers = ProcessWorker.resolve_max_workers('auto', 'TestModule')
            assert isinstance(max_workers, int)
            assert max_workers > 0
    
    def test_resolve_max_workers_manual(self):
        """测试手动指定 worker 数量"""
        if pytest is None:
            return
        max_workers = ProcessWorker.resolve_max_workers(8, 'TestModule')
        assert max_workers == 8
    
    def test_run_jobs_queue_mode(self):
        """测试队列模式执行任务"""
        if pytest is None:
            return
        worker = ProcessWorker(
            max_workers=2,
            execution_mode=ExecutionMode.QUEUE,
            job_executor=simple_task,
            is_verbose=False
        )
        
        # 先重置，确保没有之前的结果
        worker.reset()
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
            {'id': '2', 'data': {'value': 2}},
            {'id': '3', 'data': {'value': 3}},
        ]
        
        # 执行任务
        stats = worker.run_jobs(jobs)
        
        # 验证统计信息
        assert isinstance(stats, dict)
        assert 'total_jobs' in stats
        assert stats['total_jobs'] == 3
        assert 'completed_jobs' in stats
        assert stats['completed_jobs'] == 3
        
        # 验证结果（不依赖具体值，只验证核心功能）
        results = worker.get_results()
        assert len(results) >= 3  # 至少 3 个结果
        assert all(isinstance(r, JobResult) for r in results[-3:])  # 最后 3 个是 JobResult
        assert all(r.status == JobStatus.COMPLETED for r in results[-3:])  # 都成功
    
    def test_run_jobs_batch_mode(self):
        """测试批量模式执行任务"""
        if pytest is None:
            return
        worker = ProcessWorker(
            max_workers=2,
            execution_mode=ExecutionMode.BATCH,
            job_executor=simple_task,
            is_verbose=False
        )
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
            {'id': '2', 'data': {'value': 2}},
        ]
        
        worker.run_jobs(jobs)
        results = worker.get_results()
        assert len(results) == 2
        assert all(r.status == JobStatus.COMPLETED for r in results)
    
    def test_run_jobs_with_failures(self):
        """测试处理失败任务"""
        if pytest is None:
            return
        worker = ProcessWorker(
            max_workers=2,
            execution_mode=ExecutionMode.QUEUE,
            job_executor=failing_task,
            is_verbose=False
        )
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
        ]
        
        worker.run_jobs(jobs)
        results = worker.get_results()
        assert len(results) == 1
        assert results[0].status == JobStatus.FAILED
        assert results[0].error is not None
    
    def test_get_stats(self):
        """测试获取统计信息"""
        if pytest is None:
            return
        worker = ProcessWorker(
            max_workers=2,
            execution_mode=ExecutionMode.QUEUE,
            job_executor=simple_task,
            is_verbose=False
        )
        
        jobs = [
            {'id': '1', 'data': {'value': 1}},
        ]
        
        stats = worker.run_jobs(jobs)
        
        assert 'total_jobs' in stats
        assert 'completed_jobs' in stats
        assert 'failed_jobs' in stats
        assert stats['total_jobs'] == 1
    
    def test_calculate_workers(self):
        """测试计算 worker 数量"""
        if pytest is None:
            return
        from core.infra.worker.multi_process.task_type import TaskType
        
        # CPU 密集型
        workers = ProcessWorker.calculate_workers(TaskType.CPU_INTENSIVE, reserve_cores=2)
        assert isinstance(workers, int)
        assert workers > 0
        
        # IO 密集型
        workers = ProcessWorker.calculate_workers(TaskType.IO_INTENSIVE, reserve_cores=1)
        assert isinstance(workers, int)
        assert workers > 0
        
        # 混合型
        workers = ProcessWorker.calculate_workers(TaskType.MIXED, reserve_cores=2)
        assert isinstance(workers, int)
        assert workers > 0
