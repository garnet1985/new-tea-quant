"""
SimpleErrorHandler 单元测试
"""
try:
    import pytest
except ImportError:
    pytest = None

from core.infra.worker.error_handlers.simple_error_handler import SimpleErrorHandler
from core.infra.worker.error_handlers.base import ErrorAction


class TestSimpleErrorHandler:
    """SimpleErrorHandler 测试类"""
    
    def test_init_default(self):
        """测试默认初始化（不重试）"""
        if pytest is None:
            return
        handler = SimpleErrorHandler()
        assert handler.max_retries == 0
    
    def test_init_with_retries(self):
        """测试带重试次数的初始化"""
        if pytest is None:
            return
        handler = SimpleErrorHandler(max_retries=3)
        assert handler.max_retries == 3
    
    def test_handle_error_no_retry(self):
        """测试不重试的错误处理"""
        if pytest is None:
            return
        handler = SimpleErrorHandler(max_retries=0)
        job = {'id': '1', 'data': {'value': 1}}
        error = ValueError("Task failed")
        
        action = handler.handle_error(job, error, retry_count=0)
        assert action == ErrorAction.SKIP
    
    def test_handle_error_with_retry(self):
        """测试带重试的错误处理"""
        if pytest is None:
            return
        handler = SimpleErrorHandler(max_retries=3)
        job = {'id': '1', 'data': {'value': 1}}
        error = ValueError("Task failed")
        
        # 第一次重试
        action = handler.handle_error(job, error, retry_count=0)
        assert action == ErrorAction.RETRY
        
        # 第二次重试
        action = handler.handle_error(job, error, retry_count=1)
        assert action == ErrorAction.RETRY
        
        # 第三次重试
        action = handler.handle_error(job, error, retry_count=2)
        assert action == ErrorAction.RETRY
        
        # 超过最大重试次数
        action = handler.handle_error(job, error, retry_count=3)
        assert action == ErrorAction.SKIP
    
    def test_should_retry(self):
        """测试是否应该重试"""
        if pytest is None:
            return
        handler = SimpleErrorHandler(max_retries=2)
        job = {'id': '1', 'data': {'value': 1}}
        error = ValueError("Task failed")
        
        assert handler.should_retry(job, error, retry_count=0) is True
        assert handler.should_retry(job, error, retry_count=1) is True
        assert handler.should_retry(job, error, retry_count=2) is False
    
    def test_get_retry_delay(self):
        """测试获取重试延迟时间"""
        if pytest is None:
            return
        handler = SimpleErrorHandler()
        
        # 指数退避：1s, 2s, 4s, 8s, ...
        assert handler.get_retry_delay(0) == 1.0
        assert handler.get_retry_delay(1) == 2.0
        assert handler.get_retry_delay(2) == 4.0
        assert handler.get_retry_delay(3) == 8.0
        
        # 最大延迟限制为 60s
        assert handler.get_retry_delay(10) <= 60.0
