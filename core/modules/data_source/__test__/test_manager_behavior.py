"""DataSourceManager 单元测试（与当前 API 一致）。"""
from core.modules.data_source import DataSourceManager


def test_init():
    manager = DataSourceManager(is_verbose=False)

    assert hasattr(manager, "_all_valid_configs_cache")
    assert hasattr(manager, "_all_valid_handlers_cache")
    assert hasattr(manager, "_execution_scheduler")
    assert hasattr(manager, "execute")


def test_flush_cache():
    manager = DataSourceManager(is_verbose=False)
    manager._flush_cache()
    assert len(manager._all_valid_configs_cache) == 0
    assert len(manager._all_valid_handlers_cache) == 0
