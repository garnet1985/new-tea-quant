"""
SimpleAggregator 单元测试
"""
try:
    import pytest
except ImportError:
    pytest = None

from core.infra.worker.aggregators.simple_aggregator import SimpleAggregator
from core.infra.worker.executors.base import JobResult, JobStatus


class TestSimpleAggregator:
    """SimpleAggregator 测试类"""
    
    def test_init(self):
        """测试初始化"""
        if pytest is None:
            return
        aggregator = SimpleAggregator()
        summary = aggregator.get_summary()
        assert summary['total_jobs'] == 0
        assert summary['success_count'] == 0
        assert summary['failed_count'] == 0
    
    def test_add_result_success(self):
        """测试添加成功结果"""
        if pytest is None:
            return
        aggregator = SimpleAggregator()
        result = JobResult(
            job_id='1',
            status=JobStatus.COMPLETED,
            result={'value': 42},
            duration=1.5
        )
        aggregator.add_result(result)
        
        summary = aggregator.get_summary()
        assert summary['total_jobs'] == 1
        assert summary['success_count'] == 1
        assert summary['failed_count'] == 0
        assert summary['total_duration'] == 1.5
        assert summary['avg_duration'] == 1.5
        assert summary['success_rate'] == 100.0
    
    def test_add_result_failed(self):
        """测试添加失败结果"""
        if pytest is None:
            return
        aggregator = SimpleAggregator()
        result = JobResult(
            job_id='1',
            status=JobStatus.FAILED,
            error=ValueError("Task failed"),
            duration=0.5
        )
        aggregator.add_result(result)
        
        summary = aggregator.get_summary()
        assert summary['total_jobs'] == 1
        assert summary['success_count'] == 0
        assert summary['failed_count'] == 1
        assert summary['success_rate'] == 0.0
    
    def test_add_multiple_results(self):
        """测试添加多个结果"""
        if pytest is None:
            return
        aggregator = SimpleAggregator()
        
        # 添加成功结果
        aggregator.add_result(JobResult('1', JobStatus.COMPLETED, duration=1.0))
        aggregator.add_result(JobResult('2', JobStatus.COMPLETED, duration=2.0))
        
        # 添加失败结果
        aggregator.add_result(JobResult('3', JobStatus.FAILED, duration=0.5))
        
        summary = aggregator.get_summary()
        assert summary['total_jobs'] == 3
        assert summary['success_count'] == 2
        assert summary['failed_count'] == 1
        assert summary['total_duration'] == 3.5
        assert summary['avg_duration'] == pytest.approx(3.5 / 3, rel=1e-6)
        assert summary['success_rate'] == pytest.approx(2 / 3 * 100, rel=1e-6)
    
    def test_reset(self):
        """测试重置聚合器"""
        if pytest is None:
            return
        aggregator = SimpleAggregator()
        aggregator.add_result(JobResult('1', JobStatus.COMPLETED, duration=1.0))
        
        aggregator.reset()
        summary = aggregator.get_summary()
        assert summary['total_jobs'] == 0
        assert summary['success_count'] == 0
        assert summary['failed_count'] == 0
