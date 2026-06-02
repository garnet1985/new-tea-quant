"""batch 保存调度：batch 模式应一次 batch 回调，immediate 应多次 single 回调。"""
from unittest.mock import Mock

from core.modules.data_source.service.executor.bundle_execution_service import (
    _invoke_bundle_save,
)


def test_invoke_bundle_save_batch_mode_calls_batch_once():
    single = Mock()
    batch = Mock()
    items = [("b1", {"a": 1}), ("b2", {"b": 2})]
    n = _invoke_bundle_save({}, items, "batch", single, batch)
    assert n == 2
    batch.assert_called_once_with({}, items)
    single.assert_not_called()


def test_invoke_bundle_save_immediate_calls_single_per_item():
    single = Mock()
    batch = Mock()
    items = [("b1", {"a": 1}), ("b2", {"b": 2})]
    n = _invoke_bundle_save({}, items, "immediate", single, batch)
    assert n == 2
    assert single.call_count == 2
    batch.assert_not_called()
