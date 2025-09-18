#!/usr/bin/env python3
"""
测试连接池解决方案 - 解决MySQL多进程连接问题
"""
import asyncio
from loguru import logger
from utils.db.connection_pool import get_connection_pool, get_connection, return_connection
from utils.db.process_safe_db_manager import ProcessSafeDatabaseManager
from app.analyzer.analyzer import Analyzer


async def test_connection_pool_solution():
    """测试连接池解决方案"""
    logger.info("🧪 开始测试连接池解决方案")
    
    # 测试连接池
    logger.info("📊 测试连接池功能")
    pool = get_connection_pool()
    
    # 测试获取和归还连接
    conn1 = get_connection()
    if conn1:
        logger.info("✅ 成功获取连接1")
        return_connection(conn1)
        logger.info("✅ 成功归还连接1")
    
    conn2 = get_connection()
    if conn2:
        logger.info("✅ 成功获取连接2")
        return_connection(conn2)
        logger.info("✅ 成功归还连接2")
    
    # 测试多进程安全的数据库管理器
    logger.info("📊 测试多进程安全数据库管理器")
    db = ProcessSafeDatabaseManager(is_verbose=True)
    db.initialize()
    
    # 测试查询
    try:
        result = db.execute_query("SELECT 1 as test")
        logger.info(f"✅ 查询测试成功: {result}")
    except Exception as e:
        logger.error(f"❌ 查询测试失败: {e}")
    
    # 测试分析器
    logger.info("📊 测试分析器（使用连接池）")
    analyzer = Analyzer(db, is_verbose=True)
    
    try:
        # 初始化分析器
        logger.info("初始化分析器")
        analyzer.initialize()
        
        # 获取策略实例
        strategies = analyzer.get_all_strategies()
        logger.info(f"✅ 成功初始化 {len(strategies)} 个策略")
        
        # 测试每个策略的扫描功能
        for key, strategy in strategies.items():
            logger.info(f"🔍 测试策略 {key}: {strategy.name}")
            
            try:
                # 测试扫描功能 - 应该使用连接池，避免多进程数据库连接问题
                logger.info("开始多进程扫描，观察是否还有数据库连接错误...")
                opportunities = strategy.scan()
                
                logger.info(f"  ✅ 策略 {key} 扫描完成，发现 {len(opportunities)} 个机会")
                
                # 显示前几个机会的详细信息
                for i, opp in enumerate(opportunities[:3]):
                    logger.info(f"    机会 {i+1}: {opp}")
                
            except Exception as e:
                logger.error(f"  ❌ 策略 {key} 扫描失败: {e}")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
    
    logger.info("✅ 连接池解决方案测试完成")


if __name__ == "__main__":
    asyncio.run(test_connection_pool_solution())
