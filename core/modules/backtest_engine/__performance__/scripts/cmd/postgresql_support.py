"""PostgreSQL helpers for BE __performance__ (server probe / safe CREATE|DROP).

Safety rules mirror mysql_support:
- Only touch database names matching ``perf_test_tmp`` / ``perf_test_tmp_N``.
- Never write into the user's configured business database name.
- Refuse to DROP/reseed a DB that exists but is **not** in our registry.
"""
from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Dict, Optional, Set

from common import (
    DB_NAME_PREFIX,
    _NAME_RE,
    assert_safe_perf_db_name,
    list_registry_entries,
    load_registry,
    save_registry,
)
from progress import step

_PLACEHOLDER_PASSWORD = "your_password_here"
_PG_ENV_KEYS = (
    "DB_POSTGRESQL_HOST",
    "DB_POSTGRESQL_PORT",
    "DB_POSTGRESQL_USER",
    "DB_POSTGRESQL_PASSWORD",
    "DB_POSTGRESQL_DATABASE",
)
_ENGINE = "postgresql"


def _user_pg_config_path():
    from core.infra.project_context.core.path_manager import PathManager

    return PathManager.get_user_config_root() / "database" / "postgresql.json"


def _env_has_pg_credentials() -> bool:
    return any(str(os.getenv(k) or "").strip() for k in _PG_ENV_KEYS)


def assert_postgresql_config_present() -> None:
    path = _user_pg_config_path()
    if path.is_file() or _env_has_pg_credentials():
        return
    raise SystemExit(
        "不知道 PostgreSQL 的连接信息。\n"
        "请先配置 userspace/system/config/database/postgresql.json"
        "（可从同目录 example 复制），\n"
        "或设置环境变量 DB_POSTGRESQL_HOST / DB_POSTGRESQL_PORT / "
        "DB_POSTGRESQL_USER / DB_POSTGRESQL_PASSWORD。"
    )


def load_postgresql_server_config() -> Dict[str, Any]:
    """Load merged postgresql config; ignore business DB name for seeding."""
    assert_postgresql_config_present()
    from core.infra.project_context import ProjectContext

    cfg = deepcopy(ProjectContext.config.load_database_config("postgresql"))
    cfg["database_type"] = "postgresql"
    pg = dict(cfg.get("postgresql") or {})
    missing = [
        k for k in ("host", "port", "user") if pg.get(k) in (None, "")
    ]
    if missing:
        raise SystemExit(
            "不知道 PostgreSQL 的连接信息（配置不完整）。\n"
            f"缺少字段: {', '.join(missing)}\n"
            f"请检查 {_user_pg_config_path()} 或 DB_POSTGRESQL_* 环境变量。"
        )
    if "password" not in pg:
        raise SystemExit(
            "不知道 PostgreSQL 的连接信息（缺少 password 字段）。\n"
            f"请在 {_user_pg_config_path()} 写上 password"
            "（本地无密码可写成 \"\"），或设置 DB_POSTGRESQL_PASSWORD。"
        )
    if str(pg.get("password") or "") == _PLACEHOLDER_PASSWORD:
        raise SystemExit(
            "不知道 PostgreSQL 的连接信息（密码仍是占位符 your_password_here）。\n"
            f"请编辑 {_user_pg_config_path()} 写入真实密码"
            "（本地无密码可写成 \"\"），或设置 DB_POSTGRESQL_PASSWORD。"
        )
    cfg["postgresql"] = pg
    return cfg


def _pg_connect_kwargs(pg: Dict[str, Any], *, database: str) -> Dict[str, Any]:
    return {
        "host": str(pg.get("host") or "localhost"),
        "port": int(pg.get("port") or 5432),
        "user": str(pg.get("user") or ""),
        "password": str(pg.get("password") or ""),
        "dbname": str(database),
        "connect_timeout": 10,
    }


def _connect_maintenance(pg: Dict[str, Any]):
    """Connect to postgres / template1 (no target DB required)."""
    import psycopg2

    last_exc: Optional[BaseException] = None
    for maint in ("postgres", "template1"):
        try:
            conn = psycopg2.connect(**_pg_connect_kwargs(pg, database=maint))
            conn.autocommit = True
            return conn
        except Exception as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def probe_postgresql_server(cfg: Dict[str, Any]) -> None:
    try:
        import psycopg2  # noqa: F401
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "无法连接 PostgreSQL：缺少 psycopg2 依赖，请先安装项目依赖。"
        ) from exc

    pg = dict(cfg.get("postgresql") or {})
    try:
        conn = _connect_maintenance(pg)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            conn.close()
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(
            "无法连接 PostgreSQL：数据库可能没开，或配置信息不对。\n"
            f"host={pg.get('host')!r} port={pg.get('port')!r} "
            f"user={pg.get('user')!r}\n"
            f"详情: {exc}"
        ) from exc


def list_postgresql_dbs_matching_prefix(cfg: Dict[str, Any]) -> Set[str]:
    pg = dict(cfg.get("postgresql") or {})
    conn = _connect_maintenance(pg)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT datname FROM pg_database WHERE datname LIKE %s",
                (f"{DB_NAME_PREFIX}%",),
            )
            rows = cur.fetchall() or ()
    finally:
        conn.close()
    out: Set[str] = set()
    for row in rows:
        name = str(row[0] if not isinstance(row, dict) else row.get("datname") or "")
        if _NAME_RE.match(name):
            out.add(name)
    return out


def postgresql_database_exists(cfg: Dict[str, Any], name: str) -> bool:
    name = assert_safe_perf_db_name(name)
    pg = dict(cfg.get("postgresql") or {})
    conn = _connect_maintenance(pg)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def create_postgresql_database(cfg: Dict[str, Any], name: str) -> None:
    from psycopg2 import sql

    name = assert_safe_perf_db_name(name)
    pg = dict(cfg.get("postgresql") or {})
    conn = _connect_maintenance(pg)
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    finally:
        conn.close()


def drop_postgresql_database(cfg: Dict[str, Any], name: str) -> None:
    from psycopg2 import sql

    name = assert_safe_perf_db_name(name)
    pg = dict(cfg.get("postgresql") or {})
    conn = _connect_maintenance(pg)
    try:
        with conn.cursor() as cur:
            # Kick other sessions so DROP can proceed.
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            cur.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name))
            )
    finally:
        conn.close()


def allocate_postgresql_db_name(cfg: Dict[str, Any]) -> str:
    used = set()
    for e in list_registry_entries(engine=_ENGINE):
        name = str(e.get("name") or "")
        if _NAME_RE.match(name):
            used.add(name)
    used |= list_postgresql_dbs_matching_prefix(cfg)
    if DB_NAME_PREFIX not in used:
        return DB_NAME_PREFIX
    n = 1
    while f"{DB_NAME_PREFIX}_{n}" in used:
        n += 1
    return f"{DB_NAME_PREFIX}_{n}"


def active_postgresql_entry() -> Optional[Dict[str, Any]]:
    for e in reversed(list_registry_entries(engine=_ENGINE)):
        name = str(e.get("name") or "")
        if _NAME_RE.match(name):
            return e
    return None


def remove_postgresql_registry_entry(name: str) -> None:
    name = str(name or "")
    reg = load_registry()
    reg["entries"] = [
        e
        for e in list(reg.get("entries") or [])
        if not (
            str(e.get("engine", "")).lower() == _ENGINE
            and str(e.get("name") or "") == name
        )
    ]
    save_registry(reg)


def drop_postgresql_entry(
    entry: Dict[str, Any], *, cfg: Optional[Dict[str, Any]] = None
) -> None:
    name = assert_safe_perf_db_name(str(entry.get("name") or ""))
    registered = any(
        str(e.get("name") or "") == name for e in list_registry_entries(engine=_ENGINE)
    )
    if not registered:
        raise SystemExit(
            f"拒绝删除 PostgreSQL 库 {name!r}：不在本套件 registry 中，"
            "可能不是性能测试库。"
        )
    server_cfg = cfg or load_postgresql_server_config()
    probe_postgresql_server(server_cfg)
    if postgresql_database_exists(server_cfg, name):
        step("db_creation", f"DROP DATABASE {name}（仅限本套件注册的测试库）")
        drop_postgresql_database(server_cfg, name)
    remove_postgresql_registry_entry(name)


def build_postgresql_manager_config(
    server_cfg: Dict[str, Any], db_name: str
) -> Dict[str, Any]:
    db_name = assert_safe_perf_db_name(db_name)
    cfg = deepcopy(server_cfg)
    cfg["database_type"] = "postgresql"
    pg = dict(cfg.get("postgresql") or {})
    pg["database"] = db_name
    cfg["postgresql"] = pg
    return cfg


def connection_snapshot(cfg: Dict[str, Any], db_name: str) -> Dict[str, Any]:
    pg = dict(cfg.get("postgresql") or {})
    snap: Dict[str, Any] = {
        "host": pg.get("host"),
        "port": pg.get("port"),
        "user": pg.get("user"),
        "database": db_name,
    }
    schema = pg.get("default_pgsql_schema")
    if schema:
        snap["default_pgsql_schema"] = schema
    return snap
