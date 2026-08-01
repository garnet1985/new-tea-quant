"""DuckDB wal_policy 配置解析。"""
from core.infra.db.core.engines.duckdb.wal_policy import (
    duckdb_shared_config,
    should_checkpoint_after_batch,
    should_checkpoint_after_tag_run,
    should_checkpoint_on_sigint,
)


def test_should_checkpoint_defaults():
    cfg = {"database_type": "duckdb", "duckdb": {"domains": {}}}
    shared = duckdb_shared_config(cfg)
    assert shared.get("wal_autocheckpoint") is None
    assert should_checkpoint_after_batch(cfg) is True
    assert should_checkpoint_on_sigint(cfg) is True
    assert should_checkpoint_after_tag_run(cfg) is True


def test_should_checkpoint_can_disable():
    cfg = {
        "database_type": "duckdb",
        "duckdb": {
            "checkpoint_after_batch_save": False,
            "checkpoint_on_sigint": False,
        },
    }
    assert should_checkpoint_after_batch(cfg) is False
    assert should_checkpoint_on_sigint(cfg) is False
