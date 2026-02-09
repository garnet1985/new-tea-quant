#!/usr/bin/env python3
"""
直接查 DB 核对 adj_factor_event 的预期 job 数量

renew_if_over_days=1 时：
- 应排除：last_update 距离 latest_completed_trading_date 不足 1 天的股票
- 应包含：无 last_update 或 days_diff >= 1 的股票

用法：python check_adj_factor_expected_jobs.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils


def _normalize_date(val) -> str:
    """将 datetime/str 转为 YYYYMMDD"""
    if val is None:
        return ""
    s = str(val).replace("-", "").replace(" ", "").replace(":", "")[:8]
    return s if len(s) == 8 and s.isdigit() else ""


def main():
    data_manager = DataManager.get_instance()
    if not data_manager:
        data_manager = DataManager(is_verbose=False)

    # 1. 股票总数（与 adj_factor 依赖的 stock_list 一致：可能用 load_all 或 load_filtered）
    stock_list_filtered = data_manager.service.stock.list.load(filtered=True)
    stock_list_all = data_manager.service.stock.list.load_all()
    total_filtered = len(stock_list_filtered)
    total_all = len(stock_list_all)
    # adj_factor 依赖 stock_list，通常来自 dependencies（stock_list 的 load_all 或 API 结果）
    stock_list = stock_list_all
    stock_ids = {str(s.get("id") or s.get("ts_code") or s) for s in stock_list if s}
    total_stocks = len(stock_ids)

    logger.info(f"股票列表: filtered={total_filtered}, load_all={total_all}, 使用 load_all 作为基准")

    # 2. 最新完成交易日
    latest = data_manager.service.calendar.get_latest_completed_trading_date()
    latest_ymd = _normalize_date(latest) or latest.replace("-", "")[:8]
    logger.info(f"最新完成交易日: {latest} ({latest_ymd})")

    # 3. 查 sys_adj_factor_events 每只股票的 last_update（取该股最新一条的 last_update）
    adj_model = data_manager.stock.kline._adj_factor_event
    if not adj_model:
        logger.error("无法获取 adj_factor_events model")
        return

    # load_latests 按 id 分组取 MAX(last_update)
    latest_records = adj_model.load_latests(date_field="last_update", group_fields=["id"])
    if not latest_records:
        logger.info("sys_adj_factor_events 表为空或无数据")
        logger.info(f"预期 job 数: {total_stocks}（全量首次）")
        return

    last_update_map = {}
    for r in latest_records:
        sid = r.get("id")
        lu = r.get("last_update")
        if sid:
            last_update_map[str(sid)] = _normalize_date(lu) or lu

    logger.info(f"表中有 last_update 的股票数: {len(last_update_map)}")

    # 4. 按 renew_if_over_days=1 规则分类
    threshold_days = 1
    need_update = []   # 需要更新（应建 job）
    skip_recent = []   # 刚更新过，跳过
    no_last = []       # 表内无该股（新股票）

    for sid in stock_ids:
        if not sid:
            continue
        lu = last_update_map.get(sid)
        if lu is None or lu == "":
            no_last.append(sid)
            need_update.append(sid)
            continue
        try:
            days_diff = DateUtils.diff_days(lu, latest_ymd)
        except Exception:
            need_update.append(sid)
            continue
        if days_diff >= threshold_days:
            need_update.append(sid)
        else:
            skip_recent.append(sid)

    expected_jobs = len(need_update)
    logger.info("")
    logger.info("=" * 60)
    logger.info("【预期 job 数】")
    logger.info("=" * 60)
    logger.info(f"总股票数:           {total_stocks}")
    logger.info(f"应排除（今日已更新）: {len(skip_recent)}")
    logger.info(f"应包含（需更新）:     {expected_jobs}")
    logger.info(f"  - 表内无该股:      {len(no_last)}")
    logger.info(f"  - 表内有但过期:    {expected_jobs - len(no_last)}")
    logger.info("")
    logger.info(f">>> 预期 job 数应为: {expected_jobs}")
    if skip_recent:
        logger.info(f"跳过样例（前5）: {skip_recent[:5]}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
