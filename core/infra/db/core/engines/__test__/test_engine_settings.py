"""Engine 配置 dataclass 与 build_engine_meta 解析。"""
import pytest

pytestmark = pytest.mark.force_run

from core.infra.db.core.engines.duckdb.settings import DuckdbSettings
from core.infra.db.core.engines.meta import build_engine_meta
from core.infra.db.core.engines.mysql.settings import MysqlSettings
from core.infra.db.core.engines.pgsql.settings import PgsqlSettings
from core.infra.db.core.engines.shared.config_parse import parse_database_config
from core.infra.db.core.engines.shared.batch_write_settings import BatchWriteSettings


def test_build_engine_meta_mysql():
    raw = {
        "database_type": "mysql",
        "mysql": {
            "host": "127.0.0.1",
            "port": 3306,
            "database": "db",
            "user": "u",
            "password": "p",
            "pool_size_min": 2,
            "pool_size_max": 20,
        },
        "batch_write": {"batch_size": 500, "_advanced": {"insert_batch_size": 2000}},
    }
    parsed = parse_database_config(raw)
    meta = build_engine_meta(parsed)
    assert isinstance(meta.backend, MysqlSettings)
    assert meta.backend.pool_minconn == 2
    assert meta.backend.pool_maxconn == 20
    assert meta.batch_write == BatchWriteSettings(
        enable=True, batch_size=500, flush_interval=5.0, insert_batch_size=2000
    )


def test_build_engine_meta_duckdb_checkpoint_keys():
    raw = {
        "database_type": "duckdb",
        "duckdb": {
            "domains": {
                "data": {"db_path": "data.duckdb"},
                "tag": {"db_path": "tag.duckdb"},
                "strategy": {"db_path": "strategy.duckdb"},
            },
            "checkpoint_after_batch_save": False,
        },
        "batch_write": {"enable": True},
    }
    parsed = parse_database_config(raw)
    meta = build_engine_meta(parsed)
    assert isinstance(meta.backend, DuckdbSettings)
    assert meta.backend.checkpoint_after_batch_save is False
    assert meta.options["checkpoint_after_write"] is False
    assert meta.options["checkpoint_after_batch_save"] is False


def test_build_engine_meta_pgsql_schema():
    raw = {
        "database_type": "postgresql",
        "postgresql": {
            "host": "h",
            "port": 5432,
            "database": "d",
            "user": "u",
            "password": "p",
            "default_pgsql_schema": "app",
        },
    }
    parsed = parse_database_config(raw)
    meta = build_engine_meta(parsed)
    assert isinstance(meta.backend, PgsqlSettings)
    assert meta.backend.pgsql_schema == "app"
