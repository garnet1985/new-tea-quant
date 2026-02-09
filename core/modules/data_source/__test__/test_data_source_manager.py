"""
DataSourceManager 单元测试（与当前 API 一致）
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    class pytest:
        @staticmethod
        def fixture(func):
            return func


class TestDataSourceManager:
    """DataSourceManager 测试类"""

    def test_init(self):
        """测试初始化：当前 Manager 仅有 config/handler 缓存与 execution_scheduler"""
        from core.modules.data_source.data_source_manager import DataSourceManager

        manager = DataSourceManager(is_verbose=False)

        assert hasattr(manager, '_all_valid_configs_cache')
        assert hasattr(manager, '_all_valid_handlers_cache')
        assert hasattr(manager, '_execution_scheduler')
        assert hasattr(manager, 'execute')

    def test_flush_cache(self):
        """测试 _flush_cache 清空缓存"""
        from core.modules.data_source.data_source_manager import DataSourceManager

        manager = DataSourceManager(is_verbose=False)
        manager._flush_cache()
        assert len(manager._all_valid_configs_cache) == 0
        assert len(manager._all_valid_handlers_cache) == 0


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        test = TestDataSourceManager()
        for name in ["test_init", "test_flush_cache"]:
            try:
                getattr(test, name)()
                print(f"✅ {name} 通过")
            except Exception as e:
                print(f"❌ {name} 失败: {e}")
