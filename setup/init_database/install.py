#!/usr/bin/env python3
"""
数据库初始化步骤（探活/ready check）。

做两件事：
1) 读取并展示当前数据库配置（分层合并后的最终结果，隐藏密码）
2) 用该配置尝试连接数据库并执行最小探活 SQL（SELECT 1）
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, Dict

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from setup.setup import NewTeaQuantSetup

# 允许用户直接运行该步骤，也默认使用项目 venv
NewTeaQuantSetup.ensure_venv_for_setup_step(__file__)

USER_DB_CONFIG_DIR = _REPO_ROOT / "userspace" / "config" / "database"


def _mask_password(cfg: Dict[str, Any]) -> Dict[str, Any]:
    masked = dict(cfg)
    if "password" in masked and masked["password"]:
        masked["password"] = "***"
    return masked


def _load_json_dict(path: Path) -> Dict[str, Any]:
    import json

    with open(path, "r", encoding="utf-8") as f:
        v = json.load(f)
    return v if isinstance(v, dict) else {}

def _postgres_database_exists(db_cfg: Dict[str, Any]) -> bool:
    import psycopg2

    target_db = db_cfg.get("database")
    if not target_db:
        return False

    # connect to maintenance db; avoid requiring target db to exist
    maint_db = "postgres"
    try:
        conn = psycopg2.connect(
            host=db_cfg.get("host", "localhost"),
            port=int(db_cfg.get("port", 5432)),
            database=maint_db,
            user=db_cfg.get("user"),
            password=db_cfg.get("password"),
        )
    except Exception:
        # fallback
        conn = psycopg2.connect(
            host=db_cfg.get("host", "localhost"),
            port=int(db_cfg.get("port", 5432)),
            database="template1",
            user=db_cfg.get("user"),
            password=db_cfg.get("password"),
        )

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            return cur.fetchone() is not None
    finally:
        conn.close()

def _postgres_create_database(db_cfg: Dict[str, Any]) -> None:
    import psycopg2
    from psycopg2 import sql

    target_db = db_cfg.get("database")
    if not target_db:
        raise ValueError("missing database name")

    maint_db = "postgres"
    try:
        conn = psycopg2.connect(
            host=db_cfg.get("host", "localhost"),
            port=int(db_cfg.get("port", 5432)),
            database=maint_db,
            user=db_cfg.get("user"),
            password=db_cfg.get("password"),
        )
    except Exception:
        conn = psycopg2.connect(
            host=db_cfg.get("host", "localhost"),
            port=int(db_cfg.get("port", 5432)),
            database="template1",
            user=db_cfg.get("user"),
            password=db_cfg.get("password"),
        )

    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
    finally:
        conn.close()


def _mysql_database_exists(db_cfg: Dict[str, Any]) -> bool:
    import pymysql

    target_db = db_cfg.get("database")
    if not target_db:
        return False
    conn = pymysql.connect(
        host=db_cfg.get("host", "localhost"),
        port=int(db_cfg.get("port", 3306)),
        user=db_cfg.get("user"),
        password=db_cfg.get("password"),
        charset=db_cfg.get("charset", "utf8mb4"),
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (target_db,))
            return cur.fetchone() is not None
    finally:
        conn.close()

def _mysql_create_database(db_cfg: Dict[str, Any]) -> None:
    import pymysql

    target_db = db_cfg.get("database")
    if not target_db:
        raise ValueError("missing database name")

    conn = pymysql.connect(
        host=db_cfg.get("host", "localhost"),
        port=int(db_cfg.get("port", 3306)),
        user=db_cfg.get("user"),
        password=db_cfg.get("password"),
        charset=db_cfg.get("charset", "utf8mb4"),
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            # identifier cannot be parametrized; use backticks and escape backticks
            safe_name = str(target_db).replace("`", "``")
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{safe_name}`")
    finally:
        conn.close()


def main() -> int:
    from setup.setup import NewTeaQuantSetup
    from core.infra.project_context import ConfigManager

    common_json = USER_DB_CONFIG_DIR / "common.json"
    if not NewTeaQuantSetup.check_file_exists(
        common_json,
        "公用数据库配置 common.json 存在",
        "未找到公用数据库配置 common.json",
    ):
        NewTeaQuantSetup.print_check_info(f"下一步的操作:")
        NewTeaQuantSetup.print_check_info(f"复制: {USER_DB_CONFIG_DIR / 'common.example.json'} 并重新命名为 common.json")
        NewTeaQuantSetup.print_check_info(f"修改 common.json 中的 database_type 为您当前使用的db种类(postgresql/mysql)")
        NewTeaQuantSetup.print_check_info(f"完成之后再次运行install.py脚本，直到这一步成功为止")
        return 1

    common_cfg = _load_json_dict(common_json)
    db_type = str(common_cfg.get("database_type") or "").strip().lower()
    if db_type not in ("postgresql", "mysql"):
        NewTeaQuantSetup.print_check_fail(f"common.json 里的 database_type 无效: {db_type!r}（可选: postgresql/mysql）")
        return 1
    NewTeaQuantSetup.print_check_ok(f"您当前要使用的数据库: {db_type}")

    db_json = USER_DB_CONFIG_DIR / f"{db_type}.json"
    if not NewTeaQuantSetup.check_file_exists(
        db_json,
        f"{db_type} 数据库配置 {db_type}.json 存在",
        f"未找到 {db_type} 数据库配置 {db_type}.json",
    ):
        NewTeaQuantSetup.print_check_info(f"下一步的操作:")
        NewTeaQuantSetup.print_check_info(f"复制: {USER_DB_CONFIG_DIR / f'{db_type}.example.json'} 并重新命名为 {db_type}.json")
        NewTeaQuantSetup.print_check_info(f"修改 {db_type}.json 中的 user/password/database/host/port 等等信息")
        NewTeaQuantSetup.print_check_info(f"请确保您的数据库已经创建并启动")
        NewTeaQuantSetup.print_check_info(f"完成之后再次运行install.py脚本，直到这一步成功为止")
        return 1

    # 文件存在性校验通过后，再按系统规则加载最终合并配置（默认 + userspace + env vars）
    config = ConfigManager.load_database_config(db_type)

    db_cfg = config.get(db_type) or {}
    if isinstance(db_cfg, dict):
        NewTeaQuantSetup.print_check_ok(f"已检测到使用数据库类型: {db_type}，当前配置:")
        NewTeaQuantSetup.print_check_ok(f"host: {db_cfg.get('host')}")
        NewTeaQuantSetup.print_check_ok(f"port: {db_cfg.get('port')}")
        NewTeaQuantSetup.print_check_ok(f"user: {db_cfg.get('user')}")
        if db_type == "postgresql":
            NewTeaQuantSetup.print_check_ok(f"schema: {db_cfg.get('default_pgsql_schema')}")
    else:
        NewTeaQuantSetup.print_check_ok(f"未检测到使用数据库类型: 请检查userspace/config/database/{db_type}.json文件是否正确")

    if db_type in ("postgresql", "mysql") and isinstance(db_cfg, dict):
        pw = db_cfg.get("password")
        if pw == "your_password_here":
            NewTeaQuantSetup.print_check_fail("未配置数据库密码（当前仍是默认占位符）")
            NewTeaQuantSetup.print_check_ok(f"请编辑: {USER_DB_CONFIG_DIR / f'{db_type}.json'}（写入 user/password 等）")
            return 1

    try:
        # 额外检查：库是否已创建（比直接连目标库更容易给出可操作提示）
        if db_type == "postgresql" and isinstance(db_cfg, dict):
            try:
                exists = _postgres_database_exists(db_cfg)
            except ModuleNotFoundError:
                NewTeaQuantSetup.print_check_fail("缺少 psycopg2 依赖，请先运行步骤 resolve_deps")
                return 1
            if not exists:
                db_name = db_cfg.get("database")
                NewTeaQuantSetup.print_check_info(f"数据库 {db_name!r} 创建中...")
                try:
                    _postgres_create_database(db_cfg)
                    NewTeaQuantSetup.print_check_ok(f"数据库 {db_name!r} 创建成功")
                except Exception as e:
                    NewTeaQuantSetup.print_check_fail(f"自动创建数据库失败: {e}")
                    NewTeaQuantSetup.print_check_ok("请用具备 CREATEDB 权限的账号执行: CREATE DATABASE ...")
                    return 1
            else:
                NewTeaQuantSetup.print_check_ok(f"数据库 {db_cfg.get('database')!r} 已存在（跳过创建）")

        if db_type == "mysql" and isinstance(db_cfg, dict):
            try:
                exists = _mysql_database_exists(db_cfg)
            except ModuleNotFoundError:
                NewTeaQuantSetup.print_check_fail("缺少 pymysql 依赖，请先运行步骤 resolve_deps")
                return 1
            if not exists:
                db_name = db_cfg.get("database")
                NewTeaQuantSetup.print_check_fail(f"数据库 {db_name!r} 还没有创建")
                try:
                    _mysql_create_database(db_cfg)
                    NewTeaQuantSetup.print_check_ok(f"数据库 {db_name!r} 创建成功")
                except Exception as e:
                    NewTeaQuantSetup.print_check_fail(f"自动创建数据库失败: {e}")
                    NewTeaQuantSetup.print_check_ok("请用有 CREATE 权限的账号手动创建该 DB")
                    return 1
            else:
                NewTeaQuantSetup.print_check_ok(f"数据库 {db_cfg.get('database')!r} 已存在（跳过创建）")

        from core.infra.db.db_manager import DatabaseManager
        db = DatabaseManager(config=config, is_verbose=False)
        db.initialize()
        # 最小探活：不依赖任何业务表是否存在
        rows = db.execute_sync_query("SELECT 1 as ok")
        ok_val = None
        if rows and isinstance(rows, list) and isinstance(rows[0], dict):
            ok_val = rows[0].get("ok")
        NewTeaQuantSetup.print_check_ok(f"DB ready（SELECT 1 -> {ok_val}）")
        db.close()
        return 0
    except Exception as e:
        NewTeaQuantSetup.print_check_fail(f"DB not ready: {e}")

        # 给出一些常见排查提示（不做强假设）
        if db_type in ("postgresql", "mysql"):
            host = (db_cfg or {}).get("host", "localhost")
            port = (db_cfg or {}).get("port")
            database = (db_cfg or {}).get("database")
            user = (db_cfg or {}).get("user")
            NewTeaQuantSetup.print_check_ok(f"连接参数: host={host} port={port} database={database} user={user}")
            if db_type == "postgresql":
                NewTeaQuantSetup.print_check_ok("提示: 可参考仓库根目录的 `setup_postgresql.sh` 或 docs/getting-started/configuration.md")
            else:
                NewTeaQuantSetup.print_check_ok("提示: 请确认 MySQL 服务已启动、账号有权限、数据库已创建")

        print("\n--- traceback ---", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

