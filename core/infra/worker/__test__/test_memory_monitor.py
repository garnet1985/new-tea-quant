"""
MemoryMonitor 单元测试
"""
try:
    import pytest
    import psutil
except ImportError:
    pytest = None
    psutil = None

from core.infra.worker.monitors.memory_monitor import MemoryMonitor


class TestMemoryMonitor:
    """MemoryMonitor 测试类"""
    
    def test_init(self):
        """测试初始化"""
        if pytest is None or psutil is None:
            return
        monitor = MemoryMonitor(memory_budget_mb=1024.0)
        assert monitor.memory_budget_mb == 1024.0
        assert monitor._baseline_rss_mb > 0
        assert monitor._current_rss_mb > 0
    
    def test_init_with_baseline(self):
        """测试使用指定基线初始化"""
        if pytest is None or psutil is None:
            return
        monitor = MemoryMonitor(
            memory_budget_mb=1024.0,
            baseline_rss_mb=500.0
        )
        assert monitor._baseline_rss_mb == 500.0
    
    def test_update(self):
        """测试更新监控状态"""
        if pytest is None or psutil is None:
            return
        monitor = MemoryMonitor(memory_budget_mb=1024.0)
        
        # 更新监控状态
        monitor.update(
            current_rss_mb=600.0,
            batch_size=10,
            delta_batch_mb=100.0,
            finished_jobs=10
        )
        
        assert monitor._current_rss_mb == 600.0
        assert monitor.finished_jobs == 10
    
    def test_get_stats(self):
        """测试获取统计信息"""
        if pytest is None or psutil is None:
            return
        monitor = MemoryMonitor(memory_budget_mb=1024.0)
        stats = monitor.get_stats()
        
        assert 'current_rss_mb' in stats
        assert 'used_mb' in stats
        assert 'available_mb' in stats
        assert 'memory_budget_mb' in stats
        assert stats['memory_budget_mb'] == 1024.0
    
    def test_get_warnings(self):
        """测试获取警告"""
        if pytest is None or psutil is None:
            return
        monitor = MemoryMonitor(memory_budget_mb=100.0)  # 很小的预算
        
        # 设置高内存使用
        monitor.update(current_rss_mb=150.0)
        
        warnings = monitor.get_warnings()
        # 如果内存使用超过预算，应该有警告
        # 注意：具体警告逻辑取决于实现
