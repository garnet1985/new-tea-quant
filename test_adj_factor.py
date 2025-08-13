#!/usr/bin/env python3
"""
测试复权因子更新功能
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare
from app.data_source.providers.tushare.main import Tushare

async def test_adj_factor():
    """测试复权因子更新功能"""
    logger.info("🧪 开始测试复权因子更新功能...")
    
    # 初始化数据库
    db = DatabaseManager(is_verbose=True)
    db.initialize()
    
    # 创建数据源实例
    tu = Tushare(db, is_verbose=True)
    ak = AKShare(db, is_verbose=True)
    
    # 注入依赖
    ak.inject_dependency(tu)
    
    # 获取最新交易日
    latest_market_open_day = await tu.get_latest_market_open_day()
    logger.info(f"📅 最新交易日: {latest_market_open_day}")
    
    # 获取股票指数
    stock_index = tu.renew_stock_index(latest_market_open_day)
    logger.info(f"📊 股票指数数量: {len(stock_index)}")
    
    # 限制测试数量
    test_stocks = stock_index[:3]
    logger.info(f"🧪 测试股票: {[s['id'] for s in test_stocks]}")
    
    # 测试复权因子更新
    logger.info("🔄 开始测试复权因子更新...")
    try:
        result = ak.renew_stock_K_line_factors(latest_market_open_day, test_stocks)
        logger.info(f"✅ 复权因子更新完成: {result}")
    except Exception as e:
        logger.error(f"❌ 复权因子更新失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_adj_factor())
