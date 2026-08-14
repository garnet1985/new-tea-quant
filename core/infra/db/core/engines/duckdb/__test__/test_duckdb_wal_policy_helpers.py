"""DuckDB wal_policy 配置解析。"""
import pytest

from core.infra.db.core.engines.duckdb.wal_policy import DuckdbWalPolicy


def test_should_checkpoint_defaults():
    cfg = {"database_type": "duckdb", "duckdb": {"domains": {}}}
    shared = DuckdbWalPolicy.shared_config(cfg)
    assert shared.get("wal_autocheckpoint") is None
    assert DuckdbWalPolicy.should_checkpoint_after_batch(cfg) is True
    assert DuckdbWalPolicy.should_checkpoint_on_sigint(cfg) is True
    assert DuckdbWalPolicy.should_checkpoint_after_tag_run(cfg) is True


def test_should_checkpoint_can_disable():
    cfg = {
        "database_type": "duckdb",
        "duckdb": {
            "checkpoint_after_batch_save": False,
            "checkpoint_on_sigint": False,
        },
    }
    assert DuckdbWalPolicy.should_checkpoint_after_batch(cfg) is False
    assert DuckdbWalPolicy.should_checkpoint_on_sigint(cfg) is False


def test_checkpoint_duckdb_engine_requires_checkpoint_method():
    with pytest.raises(TypeError, match="checkpoint"):
        DuckdbWalPolicy.checkpoint_engine(object())
