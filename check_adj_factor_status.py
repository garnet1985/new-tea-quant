#!/usr/bin/env python3
"""
检查复权因子的更新状态
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager

def check_adj_factor_status():
    """检查复权因子的更新状态"""
    logger.info("🔍 检查复权因子更新状态...")
    
    # 初始化数据库
    db = DatabaseManager(is_verbose=True)
    db.initialize()
    
    # 获取 meta_info 表实例
    meta_info_table = db.get_table_instance('meta_info')
    
    # 检查复权因子最后更新时间
    last_update = meta_info_table.get_meta_info_by_key('akshare_adj_factors_last_update')
    logger.info(f"📅 复权因子最后更新时间: {last_update}")
    
    # 检查 adj_factor 表中的数据
    adj_factor_table = db.get_table_instance('adj_factor')
    
    # 获取所有复权因子记录
    all_factors = adj_factor_table.load_all()
    logger.info(f"📊 adj_factor 表总记录数: {len(all_factors)}")
    
    if all_factors:
        # 显示前几条记录
        logger.info("📋 前5条复权因子记录:")
        for i, factor in enumerate(all_factors[:5]):
            logger.info(f"  {i+1}. {factor}")
        
        # 统计不同股票的因子数量
        stock_counts = {}
        for factor in all_factors:
            stock_id = factor['id']
            stock_counts[stock_id] = stock_counts.get(stock_id, 0) + 1
        
        logger.info(f"📊 有复权因子的股票数量: {len(stock_counts)}")
        logger.info(f"📋 前5个股票的因子数量:")
        for i, (stock_id, count) in enumerate(list(stock_counts.items())[:5]):
            logger.info(f"  {i+1}. {stock_id}: {count} 个因子")
    else:
        logger.warning("⚠️  adj_factor 表中没有任何数据！")
    
    # 检查 stock_kline 表中的数据
    stock_kline_table = db.get_table_instance('stock_kline')
    kline_count = stock_kline_table.count()
    logger.info(f"📊 stock_kline 表总记录数: {kline_count}")
    
    # 检查 stock_index 表中的数据
    stock_index_table = db.get_table_instance('stock_index')
    index_count = stock_index_table.count()
    logger.info(f"📊 stock_index 表总记录数: {index_count}")

if __name__ == "__main__":
    check_adj_factor_status()
