"""
BatchWriteQueue 单元测试
"""
import pytest
import time
from unittest.mock import Mock, patch
from core.infra.db.table_queryers.services.batch_operation_queue import BatchWriteQueue, WriteRequest


class TestWriteRequest:
    """WriteRequest 测试类"""
    
    def test_init(self):
        """测试初始化写入请求"""
        request = WriteRequest(
            table_name='test_table',
            data_list=[{'id': '001'}],
            unique_keys=['id']
        )
        assert request.table_name == 'test_table'
        assert request.data_list == [{'id': '001'}]
        assert request.unique_keys == ['id']
        assert request.timestamp is not None
    
    def test_init_with_timestamp(self):
        """测试使用指定时间戳初始化"""
        timestamp = time.time()
        request = WriteRequest(
            table_name='test_table',
            data_list=[{'id': '001'}],
            unique_keys=['id'],
            timestamp=timestamp
        )
        assert request.timestamp == timestamp


class TestBatchWriteQueue:
    """BatchWriteQueue 测试类"""
    
    def test_init(self):
        """测试初始化批量写入队列"""
        mock_db = Mock()
        queue = BatchWriteQueue(
            db_manager=mock_db,
            batch_size=100,
            flush_interval=5.0,
            enable=True
        )
        assert queue.db_manager == mock_db
        assert queue.batch_size == 100
        assert queue.flush_interval == 5.0
        assert queue.enable is True
    
    def test_enqueue(self):
        """测试入队"""
        mock_db = Mock()
        queue = BatchWriteQueue(
            db_manager=mock_db,
            batch_size=10,
            enable=True
        )
        queue.enqueue('test_table', [{'id': '001'}], ['id'])
        assert len(queue._queues['test_table']) == 1
    
    def test_flush(self):
        """测试刷新队列"""
        mock_db = Mock()
        queue = BatchWriteQueue(
            db_manager=mock_db,
            batch_size=10,
            enable=True
        )
        queue.enqueue('test_table', [{'id': '001'}], ['id'])
        queue.flush('test_table')
        # 队列应该被清空
        assert len(queue._queues['test_table']) == 0
    
    def test_flush_all(self):
        """测试刷新所有队列"""
        mock_db = Mock()
        queue = BatchWriteQueue(
            db_manager=mock_db,
            batch_size=10,
            enable=True
        )
        queue.enqueue('table1', [{'id': '001'}], ['id'])
        queue.enqueue('table2', [{'id': '002'}], ['id'])
        queue.flush()
        assert len(queue._queues) == 0
    
    def test_get_stats(self):
        """测试获取统计信息"""
        mock_db = Mock()
        queue = BatchWriteQueue(
            db_manager=mock_db,
            batch_size=10,
            enable=True
        )
        queue.enqueue('test_table', [{'id': '001'}], ['id'])
        stats = queue.get_stats()
        assert 'test_table' in stats
        assert stats['test_table']['pending'] == 1
    
    def test_shutdown(self):
        """测试关闭队列"""
        mock_db = Mock()
        queue = BatchWriteQueue(
            db_manager=mock_db,
            batch_size=10,
            enable=True
        )
        queue.enqueue('test_table', [{'id': '001'}], ['id'])
        queue.shutdown()
        # 队列应该被清空
        assert len(queue._queues) == 0
