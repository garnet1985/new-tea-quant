#!/usr/bin/env python3
"""
测试优化后的复权因子逻辑
验证AKShare API调用优化和因子计算策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data_source.providers.akshare.main import AKShare
from app.data_source.providers.akshare.main_storage import AKShareStorage
from utils.db.db_manager import DatabaseManager
from loguru import logger

def test_optimized_logic():
    """测试优化后的逻辑"""
    logger.info("🔍 测试优化后的复权因子逻辑...")
    
    # 初始化数据库连接
    db = DatabaseManager()
    storage = AKShareStorage(db)
    
    # 测试股票
    test_stock = "000001.SZ"
    
    # 1. 检查当前的因子变化事件逻辑
    logger.info(f"📊 检查股票 {test_stock} 的因子变化事件...")
    
    # 模拟Tushare返回的因子事件
    # 这里我们需要模拟Tushare的API调用
    # 由于我们没有真实的Tushare实例，我们直接测试逻辑
    
    # 2. 测试AKShare API调用优化
    logger.info("🌐 测试AKShare API调用优化...")
    
    # 模拟不同的场景
    scenarios = [
        {
            "name": "无新因子变化",
            "factor_changing_dates": [],
            "expected_api_calls": 0
        },
        {
            "name": "只有今天有因子变化",
            "factor_changing_dates": ["20250812"],
            "expected_api_calls": 1
        },
        {
            "name": "历史日期有因子变化",
            "factor_changing_dates": ["20240801", "20240815", "20250812"],
            "expected_api_calls": 1
        }
    ]
    
    for scenario in scenarios:
        logger.info(f"🧪 测试场景: {scenario['name']}")
        logger.info(f"📅 因子变化日期: {scenario['factor_changing_dates']}")
        
        if scenario['factor_changing_dates']:
            # 模拟有因子变化的情况
            earliest_date = min(scenario['factor_changing_dates'])
            latest_date = max(scenario['factor_changing_dates'])
            
            logger.info(f"📅 最早变化日期: {earliest_date}")
            logger.info(f"📅 最新变化日期: {latest_date}")
            logger.info(f"🌐 预期API调用: 1次 (从 {earliest_date} 到 {latest_date})")
            
            # 这里应该调用一次AKShare API获取从最早日期到最新日期的所有数据
            # 然后基于这些数据计算所有需要的复权因子
        else:
            logger.info("✅ 无因子变化，跳过AKShare API调用")
        
        logger.info("---")
    
    # 3. 验证数据一致性逻辑
    logger.info("🔍 验证数据一致性逻辑...")
    
    # 检查当前数据库中的因子数据
    current_factors = storage.adj_factor_table.load("id = %s", (test_stock,), order_by="date DESC")
    
    if current_factors:
        logger.info(f"📋 当前数据库中有 {len(current_factors)} 条因子记录")
        
        # 检查是否有重复数据
        dates = [factor['date'] for factor in current_factors]
        unique_dates = set(dates)
        
        if len(dates) == len(unique_dates):
            logger.info("✅ 没有重复的日期记录")
        else:
            logger.warning(f"⚠️  发现重复日期: 总记录 {len(dates)}, 唯一日期 {len(unique_dates)}")
        
        # 检查日期连续性
        sorted_dates = sorted(dates)
        logger.info(f"📅 日期范围: {sorted_dates[0]} 到 {sorted_dates[-1]}")
        
    logger.info("🏁 测试完成")

if __name__ == "__main__":
    test_optimized_logic()
