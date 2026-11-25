"""读语句超时：客户端消失后，服务器仍会在限时内停掉这条 SELECT。"""
from core.infra.db.core.engines.mysql.connector import (
    clear_statement_timeout_sql,
    statement_timeout_sql,
)
from core.infra.db.core.engines.mysql.settings import MysqlSettings


def test_mariadb_limits_the_session_in_seconds_and_can_be_cleared():
    version = "10.11.6-MariaDB"
    assert statement_timeout_sql(version, 300) == "SET SESSION max_statement_time = 300"
    assert clear_statement_timeout_sql(version) == "SET SESSION max_statement_time = 0"


def test_mysql_limits_only_selects_in_milliseconds():
    version = "8.0.36"
    assert statement_timeout_sql(version, 300) == "SET SESSION max_execution_time = 300000"
    assert clear_statement_timeout_sql(version) is None


def test_zero_disables_the_limit():
    assert statement_timeout_sql("8.0.36", 0) is None


def test_settings_default_timeout_is_five_minutes():
    settings = MysqlSettings.from_dict(
        {
            "host": "127.0.0.1",
            "database": "db",
            "user": "u",
            "password": "p",
        }
    )
    assert settings.statement_timeout_seconds == 300
    assert settings.as_dict()["statement_timeout_seconds"] == 300
