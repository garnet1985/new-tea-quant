#!/usr/bin/env python3
"""
同步核心股票表结构并拉取数据。

日期区间由 ``userspace/config/data.json`` 的 ``default_start_date`` / ``default_end_date`` 控制
（当前试跑建议 20240101～20240601）。

顺序：schema 迁移（若有快照）→ stock_list → trade_calendar → stock_st_periods → stock_klines

用法（仓库根目录）::
    python devtools/quick_tools/renew_core_stock_data.py
    python devtools/quick_tools/renew_core_stock_data.py --sources stock_st_periods
    python devtools/quick_tools/renew_core_stock_data.py --skip-migrate
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

DEFAULT_START = "20240101"
SOURCES_ORDER = ("stock_list", "trade_calendar", "stock_st_periods", "stock_klines")

# 本分支改动的表：先 DROP 再按当前 schema 重建（全量重拉，不做列级兼容迁移）
TABLES_RECREATE_ORDER = (
    "sys_trade_calendar",
    "sys_stock_st_periods",
    "sys_stock_area_map",
    "sys_stock_board_map",
    "sys_stock_industry_map",
    "sys_stock_market_map",
    "sys_stock_list",
    "sys_areas",
    "sys_boards",
    "sys_industries",
    "sys_markets",
)


def _ensure_tushare_token() -> None:
    from core.infra.project_context.path_manager import PathManager

    us = PathManager.userspace()
    dst = us / "data_source" / "providers" / "tushare" / "auth_token.txt"
    if dst.is_file():
        return
    src = (
        REPO_ROOT
        / "setup"
        / "init_userspace"
        / "userspace"
        / "data_source"
        / "providers"
        / "tushare"
        / "auth_token.txt"
    )
    if src.is_file():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info("已从 setup/init_userspace 复制 Tushare token")
        return
    raise FileNotFoundError(
        f"缺少 Tushare token: {dst}（可复制 auth_token.txt.example 并填入）"
    )


def _write_schema_snapshot_if_missing() -> Path:
    from core.infra.db.migration.runner import default_pre_mirror_snapshot_path

    snap = default_pre_mirror_snapshot_path(REPO_ROOT)
    if snap.is_file():
        return snap
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text("{}", encoding="utf-8")
    logger.warning(
        "无 pre_mirror schema 快照，已写入空快照 %s；"
        "仅会创建库中缺失的新表，已有表结构变更请用 migrate 或手工 DDL",
        snap,
    )
    return snap


def _run_migrate() -> None:
    from core.infra.db.migrate import _cmd_apply
    from argparse import Namespace

    snap = _write_schema_snapshot_if_missing()
    code = _cmd_apply(
        Namespace(
            pre_mirror_snapshot=str(snap),
            repo_root=str(REPO_ROOT),
            tables_dir=None,
            database_type="postgresql",
            dry_run=False,
            result_json=None,
            verbose=True,
        )
    )
    if code != 0:
        raise SystemExit(f"schema migrate 失败 exit={code}")


def _recreate_modified_tables() -> None:
    """DROP + CREATE 本分支涉及的表（MySQL 下解决旧列结构与索引不一致）。"""
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=True)
    dm.initialize()
    for name in TABLES_RECREATE_ORDER:
        model = dm.get_table(name)
        if model is None:
            logger.warning("跳过未注册表: %s", name)
            continue
        if dm.db.is_table_exists(name):
            model.drop_table()
            logger.info("已删除表 %s", name)
        if model.schema:
            dm.db.schema_manager.create_table_with_indexes(
                model.schema, dm.db.get_connection
            )
        else:
            model.create_table()
        logger.info("已重建表 %s", name)


def _execute_sources(keys: tuple[str, ...], *, force: bool = False) -> None:
    from core.modules.data_manager import DataManager
    from core.modules.data_source.data_source_manager import DataSourceManager

    DataManager(is_verbose=True).initialize()
    mgr = DataSourceManager(is_verbose=True)
    for key in keys:
        mgr.renew(key, force=force)


def main() -> int:
    parser = argparse.ArgumentParser(description="同步表结构并拉取 stock_list / ST / K线")
    parser.add_argument("--skip-migrate", action="store_true")
    parser.add_argument(
        "--no-recreate-tables",
        action="store_true",
        help="不 DROP 改动表（仅当已手工 migrate 时）",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="",
        help="逗号分隔，如 stock_st_periods,stock_klines；默认全部",
    )
    parser.add_argument(
        "--renew-force",
        action="store_true",
        help="强制全量重拉（等同 start-cli renew --renew-force）",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    from core.infra.project_context.path_manager import PathManager

    data_cfg = PathManager.user_config() / "data.json"
    if not data_cfg.is_file():
        logger.error("缺少 %s（需 default_start_date=%s）", data_cfg, DEFAULT_START)
        return 1

    _ensure_tushare_token()

    skip_migrate = args.skip_migrate or args.no_recreate_tables
    if not args.no_recreate_tables:
        _recreate_modified_tables()
    elif not skip_migrate:
        try:
            _run_migrate()
        except Exception as e:
            logger.warning("migrate 失败: %s", e)

    if args.sources.strip():
        sources = tuple(s.strip() for s in args.sources.split(",") if s.strip())
    else:
        sources = SOURCES_ORDER

    try:
        _execute_sources(sources, force=bool(args.renew_force))
    except Exception as e:
        logger.exception("数据拉取失败: %s", e)
        return 1

    from core.infra.project_context import ConfigManager

    end_hint = ConfigManager.get_default_end_date() or "（未配置，至真实世界最新交易日）"
    logger.info(
        "完成。K 线区间 %s ~ %s（userspace/config/data.json）；"
        "stock_st_periods 按股全量 namechange（约 5800 只 / 800 per min）",
        ConfigManager.get_default_start_date(),
        end_hint,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
