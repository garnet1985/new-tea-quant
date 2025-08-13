#!/usr/bin/env python3
"""
测试复权因子逻辑的脚本
验证数据重复和因子替换逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from loguru import logger

def test_adj_factor_logic():
    """测试复权因子的逻辑"""
    logger.info("🔍 测试复权因子逻辑...")
    
    # 初始化数据库连接
    db = DatabaseManager()
    adj_factor_table = db.get_table_instance('adj_factor')
    
    # 测试股票
    test_stock = "000001.SZ"
    
    # 1. 检查当前数据
    logger.info(f"📊 检查股票 {test_stock} 的当前复权因子...")
    current_factors = adj_factor_table.load("id = %s", (test_stock,), order_by="date DESC")
    
    if current_factors:
        logger.info(f"📋 当前有 {len(current_factors)} 条复权因子记录:")
        for i, factor in enumerate(current_factors[:5]):  # 只显示前5条
            logger.info(f"  {i+1}. 日期: {factor['date']}, QFQ因子: {factor['qfq']}, HFQ因子: {factor['hfq']}")
    else:
        logger.info("📋 当前没有复权因子记录")
    
    # 2. 检查是否有重复数据
    logger.info("🔍 检查是否有重复数据...")
    duplicate_check_query = """
        SELECT id, date, COUNT(*) as count
        FROM adj_factor 
        WHERE id = %s
        GROUP BY id, date
        HAVING COUNT(*) > 1
    """
    duplicates = adj_factor_table.execute_raw_query(duplicate_check_query, (test_stock,))
    
    if duplicates:
        logger.warning(f"⚠️  发现重复数据:")
        for dup in duplicates:
            logger.warning(f"  股票: {dup['id']}, 日期: {dup['date']}, 重复次数: {dup['count']}")
    else:
        logger.info("✅ 没有发现重复数据")
    
    # 3. 检查数据一致性
    logger.info("🔍 检查数据一致性...")
    # 检查是否有负数的复权因子（这通常是不合理的）
    negative_factors = adj_factor_table.load("id = %s AND (qfq < 0 OR hfq < 0)", (test_stock,))
    
    if negative_factors:
        logger.warning(f"⚠️  发现负数的复权因子:")
        for factor in negative_factors:
            logger.warning(f"  日期: {factor['date']}, QFQ因子: {factor['qfq']}, HFQ因子: {factor['hfq']}")
    else:
        logger.info("✅ 复权因子数据合理（没有负数）")
    
    # 4. 检查日期连续性
    logger.info("🔍 检查日期连续性...")
    if current_factors:
        dates = sorted([factor['date'] for factor in current_factors])
        logger.info(f"📅 日期范围: {dates[0]} 到 {dates[-1]}")
        logger.info(f"📅 总共有 {len(dates)} 个不同的日期")
    
    logger.info("🏁 测试完成")

if __name__ == "__main__":
    test_adj_factor_logic()
