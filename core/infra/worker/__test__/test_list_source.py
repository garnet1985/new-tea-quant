"""
ListJobSource 单元测试
"""
try:
    import pytest
except ImportError:
    pytest = None

from core.infra.worker.queues.list_source import ListJobSource


class TestListJobSource:
    """ListJobSource 测试类"""
    
    def test_init(self):
        """测试初始化"""
        if pytest is None:
            return
        jobs = [
            {'id': '1', 'data': {'value': 1}},
            {'id': '2', 'data': {'value': 2}},
            {'id': '3', 'data': {'value': 3}},
        ]
        source = ListJobSource(jobs)
        # ListJobSource 使用 _jobs 私有属性
        assert len(source._jobs) == 3
    
    def test_get_batch(self):
        """测试获取批次"""
        if pytest is None:
            return
        jobs = [
            {'id': '1', 'data': {'value': 1}},
            {'id': '2', 'data': {'value': 2}},
            {'id': '3', 'data': {'value': 3}},
        ]
        source = ListJobSource(jobs)
        
        batch1 = source.get_batch(2)
        assert len(batch1) == 2
        assert batch1[0]['id'] == '1'
        assert batch1[1]['id'] == '2'
        
        batch2 = source.get_batch(2)
        assert len(batch2) == 1
        assert batch2[0]['id'] == '3'
    
    def test_has_more(self):
        """测试是否还有更多任务"""
        if pytest is None:
            return
        jobs = [
            {'id': '1', 'data': {'value': 1}},
            {'id': '2', 'data': {'value': 2}},
        ]
        source = ListJobSource(jobs)
        
        assert source.has_more() is True
        source.get_batch(1)
        assert source.has_more() is True
        source.get_batch(1)
        assert source.has_more() is False
    
    def test_get_batch_empty(self):
        """测试空任务列表"""
        if pytest is None:
            return
        source = ListJobSource([])
        assert source.has_more() is False
        batch = source.get_batch(10)
        assert len(batch) == 0
    
    def test_get_batch_larger_than_total(self):
        """测试批次大小大于总数"""
        if pytest is None:
            return
        jobs = [
            {'id': '1', 'data': {'value': 1}},
        ]
        source = ListJobSource(jobs)
        
        batch = source.get_batch(10)
        assert len(batch) == 1
        assert source.has_more() is False
