#!/usr/bin/env python3
"""
测试特定股票的 renew 时间窗口

针对返回空数据的股票进行分析
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from core.modules.data_manager import DataManager
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.data_class.config import DataSourceConfig
from core.utils.date.date_utils import DateUtils

# 要测试的股票列表（从日志中看到的返回空数据的股票）
TEST_STOCKS = ["000001.SZ", "000002.SZ", "000004.SZ", "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ", "000010.SZ", "000012.SZ"]

def test_specific_stocks():
    """测试特定股票的 renew 时间窗口"""
    
    # 初始化 DataManager
    logger.info("初始化 DataManager...")
    data_manager = DataManager(is_verbose=False)
    
    # 获取股票列表（只包含测试股票）
    logger.info("获取股票列表...")
    all_stocks = data_manager.service.stock.list.load(filtered=True)
    test_stock_list = [s for s in all_stocks if str(s.get("id") or s.get("ts_code") or s) in TEST_STOCKS]
    
    if not test_stock_list:
        logger.error("没有找到测试股票")
        return
    
    logger.info(f"找到 {len(test_stock_list)} 个测试股票")
    
    # 获取最新交易日
    latest_completed_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
    logger.info(f"最新完成交易日: {latest_completed_trading_date}")
    
    # 加载 kline config
    from userspace.data_source.handlers.stock_klines.kline import config as kline_config
    config = DataSourceConfig(kline_config.CONFIG, data_source_key="kline")
    
    # 构建 context
    context = {
        "config": config,
        "data_manager": data_manager,
        "latest_completed_trading_date": latest_completed_trading_date,
        "dependencies": {
            "stock_list": test_stock_list,
        },
    }
    
    # 步骤1：获取 last_update_map
    logger.info("\n" + "="*80)
    logger.info("步骤1: 获取 last_update_map")
    logger.info("="*80)
    
    last_update_map = DataSourceHandlerHelper.compute_last_update_map(context)
    
    logger.info(f"\nlast_update_map 总数: {len(last_update_map)}")
    logger.info("\n各股票的 last_update:")
    for stock_id in TEST_STOCKS:
        for term in ["daily", "weekly", "monthly"]:
            composite_key = f"{stock_id}::{term}"
            last_update = last_update_map.get(composite_key)
            if last_update:
                logger.info(f"  {composite_key}: {last_update}")
    
    # 步骤2：计算 entity_date_ranges
    logger.info("\n" + "="*80)
    logger.info("步骤2: 计算 entity_date_ranges")
    logger.info("="*80)
    
    entity_date_ranges = DataSourceHandlerHelper.compute_entity_date_ranges(context, last_update_map)
    
    logger.info(f"\nentity_date_ranges 总数: {len(entity_date_ranges)}")
    
    # 步骤3：按股票分组，报告结果
    logger.info("\n" + "="*80)
    logger.info("步骤3: Renew 结果报告（按股票分组）")
    logger.info("="*80)
    
    # 按股票分组
    stock_results = {}
    
    for composite_key, date_range in entity_date_ranges.items():
        if "::" not in composite_key:
            continue
        
        parts = composite_key.split("::")
        if len(parts) < 2:
            continue
        
        stock_id = parts[0]
        term = parts[1]
        
        if stock_id not in TEST_STOCKS:
            continue
        
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
    for stock_id in TEST_STOCKS:
        terms_data = stock_results.get(stock_id, {})
        
        logger.info(f"\n📊 股票: {stock_id}")
        logger.info("-" * 80)
        
        for term in ["daily", "weekly", "monthly"]:
            term_data = terms_data.get(term)
            if not term_data:
                logger.info(f"  {term:8s}: ❌ 无需更新（未找到日期范围）")
                continue
            
            last_update = term_data["last_update"]
            start_date = term_data["start_date"]
            end_date = term_data["end_date"]
            
            # 检查日期范围是否有效
            is_valid = DateUtils.is_before(start_date, end_date)
            
            logger.info(f"  {term:8s}:")
            logger.info(f"            最后更新: {last_update or 'N/A'}")
            logger.info(f"            更新窗口: {start_date} ~ {end_date}")
            logger.info(f"            日期范围有效: {'✅ 是' if is_valid else '❌ 否（start_date >= end_date）'}")
            
            if not is_valid:
                logger.info(f"            ⚠️ 日期范围无效，该 term 会被跳过，不会创建 job")
            else:
                # 计算天数差
                if last_update:
                    try:
                        days_diff = DateUtils.diff_days(last_update, latest_completed_trading_date)
                        logger.info(f"            距离最新交易日: {days_diff} 天")
                    except Exception:
                        pass
    
    # 统计信息
    logger.info("\n" + "="*80)
    logger.info("统计信息")
    logger.info("="*80)
    
    total_stocks_with_ranges = len(stock_results)
    total_valid_ranges = sum(
        sum(1 for term_data in terms_data.values() 
            if DateUtils.is_before(term_data["start_date"], term_data["end_date"]))
        for terms_data in stock_results.values()
    )
    total_invalid_ranges = sum(
        sum(1 for term_data in terms_data.values() 
            if not DateUtils.is_before(term_data["start_date"], term_data["end_date"]))
        for terms_data in stock_results.values()
    )
    
    logger.info(f"测试股票数: {len(TEST_STOCKS)}")
    logger.info(f"有日期范围的股票数: {total_stocks_with_ranges}")
    logger.info(f"有效的日期范围数: {total_valid_ranges}")
    logger.info(f"无效的日期范围数: {total_invalid_ranges}")
    logger.info(f"entity_date_ranges 总数: {len(entity_date_ranges)}")


if __name__ == "__main__":
    try:
        test_specific_stocks()
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        sys.exit(1)
