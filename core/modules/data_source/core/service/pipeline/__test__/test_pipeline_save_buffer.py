"""DataSourceSaveBuffer：DuckDB immediate 攒批 flush。"""
from unittest.mock import Mock

from core.modules.data_source.core.service.pipeline.save_buffer import DataSourceSaveBuffer


def _mock_config(*, save_mode: str, batch_size=32, auto=False):
    cfg = Mock()
    cfg.get_save_mode.return_value = save_mode
    cfg.is_save_batch_size_auto.return_value = auto
    cfg.get_save_batch_size.return_value = batch_size
    return cfg


def test_unified_does_not_save():
    single = Mock()
    batch = Mock()
    buf = DataSourceSaveBuffer(
        context={"data_manager": Mock(db=Mock(config={"database_type": "duckdb"}))},
        config=_mock_config(save_mode="unified"),
        save_mode="unified",
        total_bundles=10,
        on_single_bundle_complete=single,
        on_batch_bundles_complete=batch,
    )
    buf.add(Mock(), {"j1": [1]})
    buf.flush_remaining()
    single.assert_not_called()
    batch.assert_not_called()


def test_duckdb_immediate_flushes_as_batch_when_threshold_met():
    single = Mock()
    batch = Mock()
    ctx = {"data_manager": Mock(db=Mock(config={"database_type": "duckdb"}))}
    buf = DataSourceSaveBuffer(
        context=ctx,
        config=_mock_config(save_mode="immediate", batch_size=2),
        save_mode="immediate",
        total_bundles=10,
        on_single_bundle_complete=single,
        on_batch_bundles_complete=batch,
    )
    buf.add(Mock(), {"a": 1})
    batch.assert_not_called()
    buf.add(Mock(), {"b": 2})
    batch.assert_called_once()
    single.assert_not_called()
