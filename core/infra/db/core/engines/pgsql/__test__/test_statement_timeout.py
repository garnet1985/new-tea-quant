"""PostgreSQL 读语句超时。"""
from core.infra.db.core.engines.pgsql.connector import statement_timeout_sql
from core.infra.db.core.engines.pgsql.settings import PgsqlSettings


def test_timeout_is_milliseconds():
    assert statement_timeout_sql(300) == "SET statement_timeout = 300000"
    assert statement_timeout_sql(0) is None


def test_settings_default_timeout_is_five_minutes():
    settings = PgsqlSettings.from_dict(
        {
            "host": "127.0.0.1",
            "database": "db",
            "user": "u",
            "password": "p",
        }
    )
    assert settings.statement_timeout_seconds == 300
    assert settings.as_dict()["statement_timeout_seconds"] == 300
