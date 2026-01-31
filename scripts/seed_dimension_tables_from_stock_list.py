#!/usr/bin/env python3
"""
从现有 stock list 产生新维度表与映射表的初始值。

数据来源（二选一）：
1. 从 DB：若 sys_stock_list 仍含 industry_id、market_id、board_id，则联合旧表
   sys_stock_industries、sys_stock_boards、sys_stock_markets 解析出 (stock_id, 行业/板块/市场)，
   写入新表 sys_industries、sys_boards、sys_markets 及三张映射表。
2. 从 API：若 DB 中已无上述列，则通过 --from-api 从 Tushare 拉取 stock_basic，
   按 industry / market / exchange 聚合后写入上述新表（不写 sys_stock_list 主表）。

新表：sys_industries, sys_boards, sys_markets, sys_stock_industry_map, sys_stock_board_map, sys_stock_market_map。
sys_markets 含 value（市场名如沪市）与 code（交易所代码如 SSE/SZSE/BSE）。

使用前请先运行 scripts/create_sys_tables.py 创建表。
若维度表（sys_industries/sys_boards/sys_markets）的 id 报 NOT NULL：说明表是旧版建的、无自增，
请先执行 scripts/migrate_stock_list_schema.py 为已有表补序列与 DEFAULT，再跑本脚本或 stock_list 数据源。

使用：
    python scripts/seed_dimension_tables_from_stock_list.py
    python scripts/seed_dimension_tables_from_stock_list.py --from-api   # 无 DB 维度列时从 Tushare 拉取
"""
import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from core.modules.data_manager.data_manager import DataManager
from core.infra.project_context import PathManager


# 市场 value（中文名） -> code（交易所代码）
VALUE_TO_MARKET_CODE = {
    "沪市": "SSE",
    "深市": "SZSE",
    "北交所": "BSE",
    "上海": "SSE",
    "深圳": "SZSE",
    "北京": "BSE",
}


def _load_tushare_token() -> str:
    """加载 Tushare token。"""
    token_path = PathManager.data_source_provider("tushare") / "auth_token.txt"
    if token_path.exists():
        try:
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        except Exception as e:
            logger.warning(f"读取 auth_token.txt 失败: {e}")
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "未找到 Tushare token。请设置 userspace/data_source/providers/tushare/auth_token.txt 或环境变量 TUSHARE_TOKEN"
        )
    return token


def _fetch_stock_basic_from_tushare():
    """从 Tushare 拉取 stock_basic，返回 list[dict]，每项含 ts_code, name, industry, market, exchange。"""
    import tushare as ts

    token = _load_tushare_token()
    ts.set_token(token)
    api = ts.pro_api()
    df = api.stock_basic(fields="ts_code,symbol,name,area,industry,market,exchange,list_date")
    if df is None or df.empty:
        return []
    df = df.fillna({"industry": "", "market": "", "exchange": ""})
    rows = df.to_dict("records")
    out = []
    for r in rows:
        ts_code = r.get("ts_code")
        name = r.get("name")
        if not ts_code or not name:
            continue
        industry = (r.get("industry") or "").strip() or "未知行业"
        market = (r.get("market") or "").strip() or "未知板块"
        exchange = (r.get("exchange") or "").strip() or "未知市场"
        out.append({
            "id": ts_code,
            "name": name,
            "industry": industry,
            "board": market,
            "market": exchange,
        })
    return out


def _stock_list_has_dimension_columns(db) -> bool:
    """检查 sys_stock_list 是否仍含 industry_id, market_id, board_id 列。"""
    try:
        # 查 1 行即可
        rows = db.execute_sync_query(
            "SELECT id, industry_id, market_id, board_id FROM sys_stock_list LIMIT 1",
            (),
        )
        return rows is not None and len(rows) >= 0
    except Exception:
        return False


def _load_stock_list_with_dimensions_from_db(db):
    """
    从 DB 读取 sys_stock_list 的 id, industry_id, market_id, board_id，
    并联合旧维度表解析出 (stock_id, industry_value, board_value, market_value)。
    若列不存在或旧表不存在则返回 []。
    """
    try:
        rows = db.execute_sync_query(
            "SELECT id, industry_id, market_id, board_id FROM sys_stock_list",
            (),
        )
    except Exception as e:
        logger.warning(f"读取 sys_stock_list 维度列失败: {e}")
        return []

    if not rows:
        return []

    # 旧表 id -> value
    old_ind = {}
    old_board = {}
    old_market = {}
    try:
        for r in db.execute_sync_query("SELECT id, value FROM sys_stock_industries", ()) or []:
            old_ind[r["id"]] = (r.get("value") or "").strip() or "未知行业"
    except Exception:
        pass
    try:
        for r in db.execute_sync_query("SELECT id, value FROM sys_stock_boards", ()) or []:
            old_board[r["id"]] = (r.get("value") or "").strip() or "未知板块"
    except Exception:
        pass
    try:
        for r in db.execute_sync_query("SELECT id, value FROM sys_stock_markets", ()) or []:
            old_market[r["id"]] = (r.get("value") or "").strip() or "未知市场"
    except Exception:
        pass

    out = []
    for r in rows:
        sid = r.get("id")
        if not sid:
            continue
        out.append({
            "id": sid,
            "industry": old_ind.get(r.get("industry_id"), "未知行业"),
            "board": old_board.get(r.get("board_id"), "未知板块"),
            "market": old_market.get(r.get("market_id"), "未知市场"),
        })
    return out


def _ensure_definition_id(model, value: str, default: str, unique_keys=None):
    """确保定义表中有 value 对应行，返回 id。先查再插；id 由表自增（schema autoIncrement 或迁移脚本补序列）。"""
    v = (value or "").strip() or default
    row = model.load_by_value(v)
    if row and row.get("id") is not None:
        return int(row["id"])
    model.batch_insert([{"value": v, "is_alive": 1}])
    row = model.load_by_value(v)
    return int(row["id"]) if row and row.get("id") is not None else None


def _ensure_market_id(dm, value: str, default: str = "未知市场"):
    """确保 sys_markets 中有 value 行，并尽量填充 code；返回 id。先查再插；id 由表自增。"""
    v = (value or "").strip() or default
    model = dm.get_table("sys_markets")
    if not model:
        return None
    row = model.load_by_value(v)
    if row and row.get("id") is not None:
        return int(row["id"])
    code = VALUE_TO_MARKET_CODE.get(v) or (v if v in ("SSE", "SZSE", "BSE") else None)
    payload = {"value": v, "is_alive": 1}
    if code:
        payload["code"] = code
    model.batch_insert([payload])
    row = model.load_by_value(v)
    return int(row["id"]) if row and row.get("id") is not None else None


def _seed_from_rows(dm, rows):
    """根据 (id, industry, board, market) 列表写入新维度表与映射表。"""
    if not rows:
        logger.warning("无股票维度数据，跳过")
        return

    industries_model = dm.get_table("sys_industries")
    boards_model = dm.get_table("sys_boards")
    markets_model = dm.get_table("sys_markets")
    industry_map_model = dm.get_table("sys_stock_industry_map")
    board_map_model = dm.get_table("sys_stock_board_map")
    market_map_model = dm.get_table("sys_stock_market_map")
    if not all([industries_model, boards_model, markets_model, industry_map_model, board_map_model, market_map_model]):
        logger.warning("缺少新维度或映射表 Model，请先运行 create_sys_tables.py")
        return

    industry_rows = []
    board_rows = []
    market_rows = []
    for r in rows:
        sid = r.get("id")
        if not sid:
            continue
        industry_val = (r.get("industry") or "").strip() or "未知行业"
        board_val = (r.get("board") or "").strip() or "未知板块"
        market_val = (r.get("market") or "").strip() or "未知市场"
        industry_id = _ensure_definition_id(industries_model, industry_val, "未知行业")
        board_id = _ensure_definition_id(boards_model, board_val, "未知板块")
        market_id = _ensure_market_id(dm, market_val, "未知市场")
        if industry_id is not None:
            industry_rows.append({"stock_id": sid, "industry_id": industry_id})
        if board_id is not None:
            board_rows.append({"stock_id": sid, "board_id": board_id})
        if market_id is not None:
            market_rows.append({"stock_id": sid, "market_id": market_id})

    stock_ids = list({r["stock_id"] for r in industry_rows + board_rows + market_rows})
    if stock_ids:
        ids_tuple = tuple(stock_ids)
        industry_map_model.delete("stock_id IN %s", (ids_tuple,))
        board_map_model.delete("stock_id IN %s", (ids_tuple,))
        market_map_model.delete("stock_id IN %s", (ids_tuple,))

    if industry_rows:
        industry_map_model.replace_mapping(industry_rows)
        logger.info(f"sys_stock_industry_map: {len(industry_rows)} 条")
    if board_rows:
        board_map_model.replace_mapping(board_rows)
        logger.info(f"sys_stock_board_map: {len(board_rows)} 条")
    if market_rows:
        market_map_model.replace_mapping(market_rows)
        logger.info(f"sys_stock_market_map: {len(market_rows)} 条")

    logger.info("新维度表与映射表初始值写入完成。")


def main():
    parser = argparse.ArgumentParser(description="从现有 stock list 产生新维度表与映射表初始值")
    parser.add_argument(
        "--from-api",
        action="store_true",
        help="不从 DB 读维度列，改为从 Tushare 拉取 stock_basic 后写入新表",
    )
    args = parser.parse_args()

    dm = DataManager(is_verbose=True)
    dm.initialize()
    db = dm.db

    if args.from_api:
        logger.info("从 Tushare 拉取 stock_basic ...")
        rows = _fetch_stock_basic_from_tushare()
        if not rows:
            logger.warning("未获取到任何股票数据，退出")
            return
        logger.info(f"获取到 {len(rows)} 条股票记录")
    else:
        if not _stock_list_has_dimension_columns(db):
            logger.warning(
                "sys_stock_list 中无 industry_id/market_id/board_id 列，无法从 DB 生成。"
                "请使用 --from-api 从 Tushare 拉取后写入新表。"
            )
            return
        rows = _load_stock_list_with_dimensions_from_db(db)
        if not rows:
            logger.warning("从 DB 未解析出任何股票维度数据，退出")
            return
        logger.info(f"从 DB 解析出 {len(rows)} 条股票维度记录")

    _seed_from_rows(dm, rows)


if __name__ == "__main__":
    main()
