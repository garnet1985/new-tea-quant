"""MySQL helpers for BE __performance__ (server probe / safe CREATE|DROP).

Safety rules:
- Only touch database names matching ``perf_test_tmp`` / ``perf_test_tmp_N``.
- Never write into the user's configured business database name.
- Refuse to DROP/reseed a schema that exists but is **not** in our registry
  (could be someone else's data that happens to share the name).
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
_MYSQL_ENV_KEYS = (
    "DB_MYSQL_HOST",
    "DB_MYSQL_PORT",
    "DB_MYSQL_USER",
    "DB_MYSQL_PASSWORD",
    "DB_MYSQL_DATABASE",
)


def _user_mysql_config_path():
    from core.infra.project_context.core.path_manager import PathManager

    return PathManager.get_user_config_root() / "database" / "mysql.json"


def _env_has_mysql_credentials() -> bool:
    return any(str(os.getenv(k) or "").strip() for k in _MYSQL_ENV_KEYS)


def assert_mysql_config_present() -> None:
    """Exit if we have no userspace/env credentials to read."""
    path = _user_mysql_config_path()
    if path.is_file() or _env_has_mysql_credentials():
        return
    raise SystemExit(
        "不知道 MySQL 的连接信息。\n"
        "请先配置 userspace/system/config/database/mysql.json"
        "（可从同目录 example 复制），\n"
        "或设置环境变量 DB_MYSQL_HOST / DB_MYSQL_PORT / DB_MYSQL_USER / "
        "DB_MYSQL_PASSWORD。"
    )


def load_mysql_server_config() -> Dict[str, Any]:
    """Load merged mysql config; keep credentials, ignore business DB name later."""
    assert_mysql_config_present()
    from core.infra.project_context import ProjectContext

    cfg = deepcopy(ProjectContext.config.load_database_config("mysql"))
    cfg["database_type"] = "mysql"
    mysql = dict(cfg.get("mysql") or {})
    missing = [
        k
        for k in ("host", "port", "user")
        if mysql.get(k) in (None, "")
    ]
    if missing:
        raise SystemExit(
            "不知道 MySQL 的连接信息（配置不完整）。\n"
            f"缺少字段: {', '.join(missing)}\n"
            f"请检查 {_user_mysql_config_path()} 或 DB_MYSQL_* 环境变量。"
        )
    # password 允许为空（本地 MySQL 常见默认）；仅拒绝未改过的占位符
    if "password" not in mysql:
        raise SystemExit(
            "不知道 MySQL 的连接信息（缺少 password 字段）。\n"
            f"请在 {_user_mysql_config_path()} 写上 password"
            "（本地无密码可写成 \"\"），或设置 DB_MYSQL_PASSWORD。"
        )
    if str(mysql.get("password") or "") == _PLACEHOLDER_PASSWORD:
        raise SystemExit(
            "不知道 MySQL 的连接信息（密码仍是占位符 your_password_here）。\n"
            f"请编辑 {_user_mysql_config_path()} 写入真实密码"
            "（本地无密码可写成 \"\"），或设置 DB_MYSQL_PASSWORD。"
        )
    cfg["mysql"] = mysql
    return cfg


def mysql_conn_kwargs(mysql: Dict[str, Any], *, with_database: bool = False) -> Dict[str, Any]:
    kw: Dict[str, Any] = {
        "host": str(mysql.get("host") or "localhost"),
        "port": int(mysql.get("port") or 3306),
        "user": str(mysql.get("user") or ""),
        "password": str(mysql.get("password") or ""),
        "charset": str(mysql.get("charset") or "utf8mb4"),
        "autocommit": True,
        "connect_timeout": 10,
    }
    if with_database:
        kw["database"] = str(mysql.get("database") or "")
    return kw


def probe_mysql_server(cfg: Dict[str, Any]) -> None:
    """Connect to the server (no database). Exit with a clear message on failure."""
    try:
        import pymysql
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "无法连接 MySQL：缺少 pymysql 依赖，请先安装项目依赖。"
        ) from exc

    mysql = dict(cfg.get("mysql") or {})
    try:
        conn = pymysql.connect(**mysql_conn_kwargs(mysql, with_database=False))
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
            "无法连接 MySQL：数据库可能没开，或配置信息不对。\n"
            f"host={mysql.get('host')!r} port={mysql.get('port')!r} "
            f"user={mysql.get('user')!r}\n"
            f"详情: {exc}"
        ) from exc


def list_mysql_schemas_matching_prefix(cfg: Dict[str, Any]) -> Set[str]:
    import pymysql

    mysql = dict(cfg.get("mysql") or {})
    conn = pymysql.connect(**mysql_conn_kwargs(mysql, with_database=False))
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME LIKE %s",
                (f"{DB_NAME_PREFIX}%",),
            )
            rows = cur.fetchall() or ()
    finally:
        conn.close()
    out: Set[str] = set()
    for row in rows:
        name = str(row[0] if not isinstance(row, dict) else row.get("SCHEMA_NAME") or "")
        if _NAME_RE.match(name):
            out.add(name)
    return out


def mysql_database_exists(cfg: Dict[str, Any], name: str) -> bool:
    import pymysql

    name = assert_safe_perf_db_name(name)
    mysql = dict(cfg.get("mysql") or {})
    conn = pymysql.connect(**mysql_conn_kwargs(mysql, with_database=False))
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME = %s",
                (name,),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def create_mysql_database(cfg: Dict[str, Any], name: str) -> None:
    import pymysql

    name = assert_safe_perf_db_name(name)
    mysql = dict(cfg.get("mysql") or {})
    safe = name.replace("`", "``")
    conn = pymysql.connect(**mysql_conn_kwargs(mysql, with_database=False))
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE `{safe}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()


def drop_mysql_database(cfg: Dict[str, Any], name: str) -> None:
    """DROP only after name safety check. Caller must ensure registry ownership."""
    import pymysql

    name = assert_safe_perf_db_name(name)
    mysql = dict(cfg.get("mysql") or {})
    safe = name.replace("`", "``")
    conn = pymysql.connect(**mysql_conn_kwargs(mysql, with_database=False))
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{safe}`")
    finally:
        conn.close()


def allocate_mysql_db_name(cfg: Dict[str, Any]) -> str:
    """Next free perf name not in registry and not present on the server."""
    used = set()
    for e in list_registry_entries(engine="mysql"):
        name = str(e.get("name") or "")
        if _NAME_RE.match(name):
            used.add(name)
    used |= list_mysql_schemas_matching_prefix(cfg)
    if DB_NAME_PREFIX not in used:
        return DB_NAME_PREFIX
    n = 1
    while f"{DB_NAME_PREFIX}_{n}" in used:
        n += 1
    return f"{DB_NAME_PREFIX}_{n}"


def active_mysql_entry() -> Optional[Dict[str, Any]]:
    """Most recent mysql registry entry with a safe perf name."""
    for e in reversed(list_registry_entries(engine="mysql")):
        name = str(e.get("name") or "")
        if _NAME_RE.match(name):
            return e
    return None


def remove_mysql_registry_entry(name: str) -> None:
    name = str(name or "")
    reg = load_registry()
    reg["entries"] = [
        e
        for e in list(reg.get("entries") or [])
        if not (
            str(e.get("engine", "")).lower() == "mysql"
            and str(e.get("name") or "") == name
        )
    ]
    save_registry(reg)


def drop_mysql_entry(entry: Dict[str, Any], *, cfg: Optional[Dict[str, Any]] = None) -> None:
    """DROP registered mysql perf DB and remove registry row."""
    name = assert_safe_perf_db_name(str(entry.get("name") or ""))
    registered = any(
        str(e.get("name") or "") == name for e in list_registry_entries(engine="mysql")
    )
    if not registered:
        raise SystemExit(
            f"拒绝删除 MySQL 库 {name!r}：不在本套件 registry 中，"
            "可能不是性能测试库。"
        )
    server_cfg = cfg or load_mysql_server_config()
    probe_mysql_server(server_cfg)
    if mysql_database_exists(server_cfg, name):
        step("db_creation", f"DROP DATABASE `{name}`（仅限本套件注册的测试库）")
        drop_mysql_database(server_cfg, name)
    remove_mysql_registry_entry(name)


def build_mysql_manager_config(server_cfg: Dict[str, Any], db_name: str) -> Dict[str, Any]:
    """Full Db.manager config pointed at the temp database (not userspace DB)."""
    db_name = assert_safe_perf_db_name(db_name)
    cfg = deepcopy(server_cfg)
    cfg["database_type"] = "mysql"
    mysql = dict(cfg.get("mysql") or {})
    mysql["database"] = db_name
    cfg["mysql"] = mysql
    return cfg


def connection_snapshot(cfg: Dict[str, Any], db_name: str) -> Dict[str, Any]:
    """Registry-safe connection info (no password)."""
    mysql = dict(cfg.get("mysql") or {})
    return {
        "host": mysql.get("host"),
        "port": mysql.get("port"),
        "user": mysql.get("user"),
        "database": db_name,
    }
