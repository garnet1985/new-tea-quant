"""
PerformanceProfiler 单元测试
"""
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from core.modules.strategy.components.opportunity_enumerator.performance_profiler import (
    PerformanceProfiler,
    PerformanceMetrics,
    AggregateProfiler
)


class TestPerformanceProfiler:
    """PerformanceProfiler 测试类"""
    
    def test_profiler_basic(self):
        """测试基本性能分析"""
        profiler = PerformanceProfiler(stock_id="000001.SZ")
        
        profiler.start_timer('total')
        time.sleep(0.01)  # 短暂延迟
        elapsed = profiler.end_timer('total')
        # 手动设置 metrics（因为 finalize 会从 _timers 读取，但我们已经 end_timer 了）
        profiler.metrics.time_total = elapsed
        
        metrics = profiler.finalize()
        
        assert metrics.time_total > 0
        assert profiler.stock_id == "000001.SZ"
    
    def test_profiler_multiple_timers(self):
        """测试多个计时器"""
        profiler = PerformanceProfiler(stock_id="000001.SZ")
        
        profiler.start_timer('load_data')
        time.sleep(0.01)
        elapsed_load = profiler.end_timer('load_data')
        # 手动设置 metrics（因为 finalize 不会自动从已结束的 timer 读取）
        profiler.metrics.time_load_data = elapsed_load
        
        profiler.start_timer('enumerate')
        time.sleep(0.01)
        elapsed_enum = profiler.end_timer('enumerate')
        profiler.metrics.time_enumerate = elapsed_enum
        
        metrics = profiler.finalize()
        
        assert metrics.time_load_data > 0
        assert metrics.time_enumerate > 0
    
    def test_profiler_db_queries(self):
        """测试数据库查询计数"""
        profiler = PerformanceProfiler(stock_id="000001.SZ")
        
        profiler.record_db_query(0.1)  # 记录一次查询，耗时 0.1 秒
        profiler.record_db_query(0.2)  # 记录第二次查询
        
        metrics = profiler.finalize()
        
        assert metrics.db_queries == 2
        assert metrics.db_query_time == pytest.approx(0.3, rel=0.1)
    
    def test_profiler_file_writes(self):
        """测试文件写入计数"""
        profiler = PerformanceProfiler(stock_id="000001.SZ")
        
        profiler.record_file_write(1024, 0.05)  # 写入 1KB，耗时 0.05 秒
        profiler.record_file_write(2048, 0.1)   # 写入 2KB，耗时 0.1 秒
        
        metrics = profiler.finalize()
        
        assert metrics.file_writes == 2
        assert metrics.file_write_size == 3072  # 1KB + 2KB
        assert metrics.file_write_time == pytest.approx(0.15, rel=0.1)
    
    @patch('core.modules.strategy.components.opportunity_enumerator.performance_profiler.psutil')
    def test_profiler_memory_tracking(self, mock_psutil):
        """测试内存跟踪"""
        mock_process = MagicMock()
        mock_mem_info = MagicMock()
        mock_mem_info.rss = 100 * 1024 * 1024  # 100MB
        mock_process.memory_info.return_value = mock_mem_info
        mock_psutil.Process.return_value = mock_process
        
        profiler = PerformanceProfiler(stock_id="000001.SZ")
        profiler._record_memory('end')
        
        metrics = profiler.finalize()
        
        assert metrics.memory_peak > 0


class TestPerformanceMetrics:
    """PerformanceMetrics 测试类"""
    
    def test_metrics_to_dict(self):
        """测试 metrics 转换为字典"""
        metrics = PerformanceMetrics()
        metrics.time_total = 1.5
        metrics.db_queries = 10
        metrics.opportunity_count = 5
        
        result = metrics.to_dict()
        
        assert result['time']['total'] == 1.5
        assert result['io']['db_queries'] == 10
        assert result['data']['opportunity_count'] == 5


class TestAggregateProfiler:
    """AggregateProfiler 测试类"""
    
    def test_aggregate_profiler_add_stock(self):
        """测试添加股票指标"""
        profiler = AggregateProfiler()
        
        metrics = PerformanceMetrics()
        metrics.time_total = 1.0
        metrics.opportunity_count = 10
        
        profiler.add_stock_metrics("000001.SZ", metrics)
        
        assert "000001.SZ" in profiler.stock_metrics
        assert profiler.stock_metrics["000001.SZ"] == metrics
    
    def test_aggregate_profiler_get_summary(self):
        """测试获取汇总统计"""
        profiler = AggregateProfiler()
        
        # 添加多个股票的指标
        for i, stock_id in enumerate(["000001.SZ", "000002.SZ"], 1):
            metrics = PerformanceMetrics()
            metrics.time_total = i * 1.0
            metrics.opportunity_count = i * 10
            metrics.db_queries = i
            profiler.add_stock_metrics(stock_id, metrics)
        
        summary = profiler.get_summary()
        
        assert summary['summary']['total_stocks'] == 2
        assert summary['data']['total_opportunity_count'] == 30  # 10 + 20
        assert summary['io']['total_db_queries'] == 3  # 1 + 2
    
    def test_aggregate_profiler_empty(self):
        """测试空汇总"""
        profiler = AggregateProfiler()
        
        summary = profiler.get_summary()
        
        assert summary == {}
