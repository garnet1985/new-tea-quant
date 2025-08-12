#!/usr/bin/env python3
"""
测试优化后的限流策略
验证Tushare API的智能限流和批量处理
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data_source.providers.akshare.main import AKShare
from app.data_source.providers.akshare.main_storage import AKShareStorage
from utils.db.db_manager import DatabaseManager
from loguru import logger

def test_rate_limiting_strategy():
    """测试限流策略"""
    logger.info("🔍 测试优化后的限流策略...")
    
    # 初始化数据库连接
    db = DatabaseManager()
    storage = AKShareStorage(db)
    
    # 测试股票列表（模拟大量股票）
    test_stocks = [
        {'id': f'00000{i:03d}.SZ', 'name': f'TestStock{i:03d}'} 
        for i in range(1, 1001)  # 1000只股票
    ]
    
    logger.info(f"📊 测试股票数量: {len(test_stocks)}")
    
    # 模拟最新的市场开放日期
    latest_market_open_day = "20250812"
    
    # 1. 测试批量处理逻辑
    logger.info("🧪 测试批量处理逻辑...")
    
    # 计算批次
    batch_size = 750  # 安全限制
    total_batches = (len(test_stocks) + batch_size - 1) // batch_size
    
    logger.info(f"📋 总批次: {total_batches}")
    logger.info(f"📋 每批大小: {batch_size}")
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(test_stocks))
        batch_stocks = test_stocks[start_idx:end_idx]
        
        logger.info(f"🔄 批次 {batch_num + 1}/{total_batches}: 股票 {start_idx + 1}-{end_idx}")
        
        # 模拟处理时间
        if batch_num < total_batches - 1:
            logger.info(f"⏳ 批次 {batch_num + 1} 完成，等待下一分钟...")
            # 这里应该等待60秒，但为了测试我们只等待1秒
            time.sleep(1)
    
    # 2. 测试限流参数
    logger.info("⚙️  测试限流参数...")
    
    # 创建AKShare实例（不依赖Tushare）
    akshare = AKShare(db)
    
    logger.info(f"📊 Tushare API限制: {akshare.tushare_adj_factor_max_per_minute} 次/分钟")
    logger.info(f"📊 安全限制: {akshare.tushare_adj_factor_safe_limit} 次/批次")
    
    # 3. 计算理论处理时间
    logger.info("⏱️  计算理论处理时间...")
    
    # 假设每批处理时间很短（因为并行），主要时间花在等待上
    processing_time_per_batch = 5  # 秒
    waiting_time_per_batch = 60    # 秒
    
    total_processing_time = total_batches * processing_time_per_batch
    total_waiting_time = (total_batches - 1) * waiting_time_per_batch
    total_time = total_processing_time + total_waiting_time
    
    logger.info(f"⏱️  总处理时间: {total_processing_time} 秒")
    logger.info(f"⏱️  总等待时间: {total_waiting_time} 秒")
    logger.info(f"⏱️  总时间: {total_time} 秒 ({total_time/60:.1f} 分钟)")
    
    # 4. 验证策略的有效性
    logger.info("✅ 验证策略有效性...")
    
    # 检查是否超过API限制
    max_api_calls_per_minute = akshare.tushare_adj_factor_max_per_minute
    actual_api_calls_per_batch = akshare.tushare_adj_factor_safe_limit
    
    if actual_api_calls_per_batch <= max_api_calls_per_minute:
        logger.info(f"✅ 安全限制设置正确: {actual_api_calls_per_batch} <= {max_api_calls_per_minute}")
    else:
        logger.warning(f"⚠️  安全限制设置过高: {actual_api_calls_per_batch} > {max_api_calls_per_minute}")
    
    # 检查批次大小是否合理
    if batch_size <= actual_api_calls_per_batch:
        logger.info(f"✅ 批次大小设置合理: {batch_size} <= {actual_api_calls_per_batch}")
    else:
        logger.warning(f"⚠️  批次大小设置过高: {batch_size} > {actual_api_calls_per_batch}")
    
    logger.info("🏁 测试完成")

if __name__ == "__main__":
    test_rate_limiting_strategy()
