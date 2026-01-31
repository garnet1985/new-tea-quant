#!/usr/bin/env python3
"""
从 Tushare stock_basic 拉取股票列表，按 industry / exchange / market 分组，
向 sys_stock_industries、sys_stock_markets、sys_stock_boards、sys_stock_list 四张表注入初始值。

使用前请先运行 scripts/create_sys_tables.py 创建表。

使用：
    python scripts/seed_stock_list_tables.py
    或从项目根目录：python -m scripts.seed_stock_list_tables

Tushare token：优先从 userspace/data_source/providers/tushare/auth_token.txt 读取，
否则从环境变量 TUSHARE_TOKEN 读取。
"""
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from core.modules.data_manager.data_manager import DataManager
from core.infra.project_context import PathManager


def _load_tushare_token() -> str:
    """加载 Tushare token：优先 auth_token.txt，否则环境变量 TUSHARE_TOKEN。"""
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


def _fetch_stock_basic():
    """调用 Tushare stock_basic，返回 list[dict]，每项含 ts_code, name, industry, market, exchange。"""
    import tushare as ts

    token = _load_tushare_token()
    ts.set_token(token)
    api = ts.pro_api()
    df = api.stock_basic(fields="ts_code,symbol,name,area,industry,market,exchange,list_date")
    if df is None or df.empty:
        return []
    # 统一空值为占位
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
            "ts_code": ts_code,
            "name": name,
            "industry": industry,
            "market": market,
            "exchange": exchange,
        })
    return out


def _group_unique(rows, key) -> list:
    """按 key 去重，保持出现顺序，返回唯一值列表。"""
    seen = set()
    unique = []
    for r in rows:
        v = r.get(key, "")
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def main():
    logger.info("拉取 Tushare stock_basic ...")
    rows = _fetch_stock_basic()
    if not rows:
        logger.warning("未获取到任何股票数据，退出")
        return
    logger.info(f"获取到 {len(rows)} 条股票记录")

    dm = DataManager(is_verbose=True)
    dm.initialize()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 行业定义表 sys_stock_industries
    industries = _group_unique(rows, "industry")
    ind_rows = [{"id": i, "value": v, "is_alive": 1} for i, v in enumerate(industries, start=1)]
    value_to_industry_id = {v: i for i, v in enumerate(industries, start=1)}
    ind_model = dm.get_table("sys_stock_industries")
    if ind_model:
        ind_model.replace(ind_rows, unique_keys=["id"], use_batch=True)
        logger.info(f"sys_stock_industries: 写入 {len(ind_rows)} 条")
    else:
        logger.warning("未找到表 sys_stock_industries，跳过")

    # 2. 市场定义表 sys_stock_markets（exchange -> 市场）
    markets = _group_unique(rows, "exchange")
    mkt_rows = [{"id": i, "value": v, "is_alive": 1} for i, v in enumerate(markets, start=1)]
    value_to_market_id = {v: i for i, v in enumerate(markets, start=1)}
    mkt_model = dm.get_table("sys_stock_markets")
    if mkt_model:
        mkt_model.replace(mkt_rows, unique_keys=["id"], use_batch=True)
        logger.info(f"sys_stock_markets: 写入 {len(mkt_rows)} 条")
    else:
        logger.warning("未找到表 sys_stock_markets，跳过")

    # 3. 板块定义表 sys_stock_boards（market -> 板块）
    boards = _group_unique(rows, "market")
    board_rows = [{"id": i, "value": v, "is_alive": 1} for i, v in enumerate(boards, start=1)]
    value_to_board_id = {v: i for i, v in enumerate(boards, start=1)}
    board_model = dm.get_table("sys_stock_boards")
    if board_model:
        board_model.replace(board_rows, unique_keys=["id"], use_batch=True)
        logger.info(f"sys_stock_boards: 写入 {len(board_rows)} 条")
    else:
        logger.warning("未找到表 sys_stock_boards，跳过")

    # 4. 股票列表 sys_stock_list
    list_rows = []
    for r in rows:
        list_rows.append({
            "id": r["ts_code"],
            "name": r["name"],
            "industry_id": value_to_industry_id.get(r["industry"]),
            "market_id": value_to_market_id.get(r["exchange"]),
            "board_id": value_to_board_id.get(r["market"]),
            "is_active": 1,
            "last_update": now,
        })
    list_model = dm.get_table("sys_stock_list")
    if list_model:
        list_model.replace(list_rows, unique_keys=["id"], use_batch=True)
        logger.info(f"sys_stock_list: 写入 {len(list_rows)} 条")
    else:
        logger.warning("未找到表 sys_stock_list，跳过")

    logger.info("四张表初始值写入完成。")


if __name__ == "__main__":
    main()
