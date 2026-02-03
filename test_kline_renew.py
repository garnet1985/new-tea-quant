#!/usr/bin/env python3
"""
测试 K 线 Handler 的 renew 逻辑

随机选择5个股票，测试它们的renew时间结果
"""
import sys
import os
import random
from typing import Dict, Any, List, Tuple

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from core.modules.data_manager import DataManager
from core.modules.data_source.data_source_manager import DataSourceManager
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.utils.date.date_utils import DateUtils


def test_kline_renew():
    """测试 K 线 Handler 的 renew 逻辑"""
    
    # 初始化 DataManager
    logger.info("初始化 DataManager...")
    data_manager = DataManager(is_verbose=False)
    
    # 获取股票列表
    logger.info("获取股票列表...")
    stock_list = data_manager.service.stock.list.load(filtered=True)
    if not stock_list:
        logger.error("股票列表为空")
        return
    
    # 随机选择5个股票
    sample_stocks = random.sample(stock_list, min(5, len(stock_list)))
    logger.info(f"随机选择了 {len(sample_stocks)} 个股票进行测试")
    
    # 打印选中的股票
    logger.info("\n选中的股票:")
    for i, stock in enumerate(sample_stocks, 1):
        stock_id = stock.get("id") or stock.get("ts_code") or str(stock)
        stock_name = stock.get("name", "未知")
        logger.info(f"  {i}. {stock_id} - {stock_name}")
    
    # 获取最新交易日
    latest_completed_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
    logger.info(f"\n最新完成交易日: {latest_completed_trading_date}")
    
    # 加载 kline config
    from userspace.data_source.handlers.stock_klines.kline import config as kline_config
    config = DataSourceConfig(kline_config.CONFIG, data_source_key="kline")
    
    # 构建 context
    context = {
        "config": config,
        "data_manager": data_manager,
        "latest_completed_trading_date": latest_completed_trading_date,
        "dependencies": {
            "stock_list": sample_stocks,  # 使用采样后的股票列表
        },
    }
    
    # 步骤1：获取 last_update_map
    logger.info("\n" + "="*60)
    logger.info("步骤1: 获取 last_update_map")
    logger.info("="*60)
    
    # 提取5个股票的ID列表
    sample_stock_ids = [str(s.get("id") or s.get("ts_code") or s) for s in sample_stocks]
    logger.info(f"只查询这 {len(sample_stock_ids)} 个股票的 last_update_map...")
    
    # 先获取所有股票的 last_update_map（因为框架需要完整查询）
    all_last_update_map = DataSourceHandlerHelper.compute_last_update_map(context)
    
    # 过滤出只包含这5个股票的数据
    last_update_map = {}
    for key, value in all_last_update_map.items():
        # 对于多字段分组（id::term），提取stock_id
        if "::" in key:
            stock_id = key.split("::")[0]
            if stock_id in sample_stock_ids:
                last_update_map[key] = value
        else:
            # 单字段分组，直接比较
            if key in sample_stock_ids:
                last_update_map[key] = value
    
    logger.info(f"\n过滤后的 last_update_map 总数: {len(last_update_map)}")
    logger.info("\n各股票的 last_update:")
    for i, (key, last_update) in enumerate(list(last_update_map.items())[:15], 1):
        logger.info(f"  {i}. {key}: {last_update}")
    
    # 步骤2：计算 entity_date_ranges
    logger.info("\n" + "="*60)
    logger.info("步骤2: 计算 entity_date_ranges")
    logger.info("="*60)
    entity_date_ranges = DataSourceHandlerHelper.compute_entity_date_ranges(context, last_update_map)
    
    logger.info(f"\nentity_date_ranges 总数: {len(entity_date_ranges)}")
    
    # 步骤3：按股票分组，报告结果
    logger.info("\n" + "="*60)
    logger.info("步骤3: Renew 结果报告（按股票分组）")
    logger.info("="*60)
    
    # 按股票分组
    stock_results: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
    for composite_key, date_range in entity_date_ranges.items():
        if "::" not in composite_key:
            continue
        
        parts = composite_key.split("::")
        if len(parts) < 2:
            continue
        
        stock_id = parts[0]
        term = parts[1]
        
        if stock_id not in stock_results:
            stock_results[stock_id] = {}
        
        last_update = last_update_map.get(composite_key)
        start_date, end_date = date_range
        
        stock_results[stock_id][term] = {
            "last_update": last_update,
            "start_date": start_date,
            "end_date": end_date,
            "composite_key": composite_key,
        }
    
    # 报告结果
    for stock_id, terms_data in stock_results.items():
        stock_info = next((s for s in sample_stocks if str(s.get("id") or s.get("ts_code") or s) == stock_id), None)
        stock_name = stock_info.get("name", "未知") if stock_info else "未知"
        
        logger.info(f"\n📊 股票: {stock_id} ({stock_name})")
        logger.info("-" * 60)
        
        for term in ["daily", "weekly", "monthly"]:
            term_data = terms_data.get(term)
            if not term_data:
                logger.info(f"  {term:8s}: ❌ 无需更新（未找到日期范围）")
                continue
            
            last_update = term_data["last_update"]
            start_date = term_data["start_date"]
            end_date = term_data["end_date"]
            
            # 判断是否需要更新
            if last_update is None:
                status = "🆕 新股票（无历史数据）"
            else:
                # 检查是否完整周期已过（仅对周线/月线）
                if term == "weekly":
                    try:
                        week_end = DateUtils.get_week_end(last_update)
                        if DateUtils.is_before(latest_completed_trading_date, week_end):
                            status = "⏸️  周期未完整（周未结束）"
                        else:
                            status = "✅ 需要更新（完整周期已过）"
                    except Exception:
                        status = "✅ 需要更新"
                elif term == "monthly":
                    try:
                        month_end = DateUtils.get_month_end(last_update)
                        if DateUtils.is_before(latest_completed_trading_date, month_end):
                            status = "⏸️  周期未完整（月未结束）"
                        else:
                            status = "✅ 需要更新（完整周期已过）"
                    except Exception:
                        status = "✅ 需要更新"
                else:
                    status = "✅ 需要更新"
            
            logger.info(f"  {term:8s}: {status}")
            logger.info(f"           最后更新: {last_update or 'N/A'}")
            logger.info(f"           更新窗口: {start_date} ~ {end_date}")
            
            # 计算天数差
            if last_update:
                try:
                    days_diff = DateUtils.diff_days(last_update, latest_completed_trading_date)
                    logger.info(f"           距离最新交易日: {days_diff} 天")
                except Exception:
                    pass
    
    # 统计信息
    logger.info("\n" + "="*60)
    logger.info("统计信息")
    logger.info("="*60)
    
    total_stocks = len(stock_results)
    total_terms = sum(len(terms) for terms in stock_results.values())
    
    logger.info(f"测试股票数: {total_stocks}")
    logger.info(f"需要更新的 term 数: {total_terms}")
    logger.info(f"entity_date_ranges 总数: {len(entity_date_ranges)}")
    
    # 检查是否有股票的所有term都需要更新
    all_terms_need_update = sum(
        1 for stock_id, terms_data in stock_results.items()
        if len(terms_data) == 3  # daily, weekly, monthly 都需要更新
    )
    logger.info(f"所有周期都需要更新的股票数: {all_terms_need_update}")


if __name__ == "__main__":
    try:
        test_kline_renew()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
