"""save_batch_size 配置与 SaveBatchSizer 测试。"""
import pytest

from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.data_class.error import DataSourceConfigError
from core.modules.data_source.service.executor.bundle_progress import AUTO_MAX_SAVE_BATCH_SIZE
from core.modules.data_source.service.executor.save_batch_sizer import SaveBatchSizer


def _minimal_config_dict(**overrides):
    base = {
        "table": "test_table",
        "save_mode": "batch",
        "renew": {
            "type": "refresh",
            "last_update_info": {"date_field": "date", "date_format": "day"},
        },
        "apis": {
            "api_a": {
                "provider_name": "tushare",
                "method": "daily",
            }
        },
    }
    base.update(overrides)
    return base


def test_config_batch_mode_defaults_to_auto():
    cfg = DataSourceConfig.from_dict(_minimal_config_dict(), "test_ds")
    assert cfg.is_save_batch_size_auto()


def test_config_accepts_save_batch_size_auto():
    cfg = DataSourceConfig.from_dict(
        _minimal_config_dict(save_batch_size="auto"),
        "test_ds",
    )
    assert cfg.is_save_batch_size_auto()
    with pytest.raises(DataSourceConfigError):
        cfg.get_save_batch_size()


def test_config_rejects_auto_for_immediate_mode():
    with pytest.raises(DataSourceConfigError, match="auto"):
        DataSourceConfig.from_dict(
            _minimal_config_dict(save_mode="immediate", save_batch_size="auto"),
            "test_ds",
        )


def test_save_batch_sizer_fixed_batch_size():
    cfg = DataSourceConfig.from_dict(
        _minimal_config_dict(save_batch_size=25),
        "test_ds",
    )
    sizer = SaveBatchSizer(cfg, total_bundles=200, save_mode="batch")
    assert not sizer.is_dynamic()
    assert sizer.current_size() == 25


def test_save_batch_sizer_immediate_is_one():
    cfg = DataSourceConfig.from_dict(
        _minimal_config_dict(save_mode="immediate", save_batch_size=100),
        "test_ds",
    )
    sizer = SaveBatchSizer(cfg, total_bundles=10, save_mode="immediate")
    assert sizer.current_size() == 1


def test_save_batch_sizer_auto_initial_size():
    cfg = DataSourceConfig.from_dict(
        _minimal_config_dict(save_batch_size="auto"),
        "test_ds",
    )
    sizer = SaveBatchSizer(cfg, total_bundles=500, save_mode="batch")
    assert sizer.is_dynamic()
    size = sizer.current_size()
    assert 10 <= size <= AUTO_MAX_SAVE_BATCH_SIZE


def test_save_batch_sizer_auto_adjusts_after_batch():
    cfg = DataSourceConfig.from_dict(
        _minimal_config_dict(save_batch_size="auto"),
        "test_ds",
    )
    sizer = SaveBatchSizer(cfg, total_bundles=500, save_mode="batch")
    first = sizer.current_size()
    sizer.record_batch_start()
    sizer.after_batch_saved(first, [{}] * first)
    second = sizer.current_size()
    assert 10 <= second <= AUTO_MAX_SAVE_BATCH_SIZE
