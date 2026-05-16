"""
迁移执行历史表 ``sys_schema_migration_log``（由迁移器自举创建，不依赖 ``core/tables``）。

以 ``step_id`` 为幂等键；已记录的步骤在后续 ``execute_plan`` 中跳过。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from core.infra.db.helpers.db_helpers import DBHelper
from core.infra.db.migration.execution_plan import MigrationStep

if TYPE_CHECKING:
    from core.infra.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

MIGRATION_LOG_TABLE = "sys_schema_migration_log"


def qualified_log_table(config: dict) -> str:
    return DBHelper.sql_qualify_table_name(config, MIGRATION_LOG_TABLE)


def create_history_table_sql(config: dict) -> str:
    qt = DBHelper.quote_identifier(config, MIGRATION_LOG_TABLE)
    t = DBHelper.normalize_database_type(config)
    if t == "postgresql":
        schema = (config.get("postgresql") or {}).get("pgsql_schema") or "public"
        qschema = DBHelper.quote_identifier(config, schema)
        full = f"{qschema}.{qt}"
        return (
            f"CREATE TABLE IF NOT EXISTS {full} ("
            f"step_id VARCHAR(255) PRIMARY KEY, "
            f"action_id VARCHAR(128) NOT NULL, "
            f"kind VARCHAR(64) NOT NULL, "
            f"applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
            f")"
        )
    return (
        f"CREATE TABLE IF NOT EXISTS {qt} ("
        f"step_id VARCHAR(255) PRIMARY KEY, "
        f"action_id VARCHAR(128) NOT NULL, "
        f"kind VARCHAR(64) NOT NULL, "
        f"applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
        f")"
    )


def ensure_history_table(db: "DatabaseManager") -> None:
    """若历史表不存在则创建（幂等）。"""
    sql = create_history_table_sql(db.config)
    with db.get_connection() as conn:
        conn.execute(sql)


def is_step_applied(db: "DatabaseManager", step_id: str) -> bool:
    ensure_history_table(db)
    qt = qualified_log_table(db.config)
    rows = db.execute_sync_query(
        f"SELECT 1 AS ok FROM {qt} WHERE step_id = %s LIMIT 1",
        (step_id,),
    )
    return bool(rows)


def record_step_applied(db: "DatabaseManager", step: MigrationStep) -> None:
    ensure_history_table(db)
    qt = qualified_log_table(db.config)
    applied_at = datetime.now(timezone.utc).replace(tzinfo=None)
    with db.get_connection() as conn:
        conn.execute(
            f"INSERT INTO {qt} (step_id, action_id, kind, applied_at) VALUES (%s, %s, %s, %s)",
            (step.step_id, step.action_id, step.kind.value, applied_at),
        )
    logger.debug("migration recorded: %s", step.step_id)
