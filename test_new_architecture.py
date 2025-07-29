#!/usr/bin/env python3
"""
测试新的策略架构
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.analyser.strategy.strategy_manager import StrategyManager

def test_new_architecture():
    """测试新的策略架构"""
    logger.info("🧪 开始测试新的策略架构...")
    
    try:
        # 1. 初始化数据库
        logger.info("1️⃣ 初始化数据库...")
        db = DatabaseManager()
        db.set_verbose(True)
        db.initialize()
        logger.info("✅ 数据库初始化成功")
        
        # 2. 验证策略管理器
        logger.info("2️⃣ 验证策略管理器...")
        strategy_manager = db.strategy_manager
        logger.info(f"✅ 策略管理器创建成功: {type(strategy_manager)}")
        
        # 3. 显示策略信息
        logger.info("3️⃣ 显示策略信息...")
        strategy_info = strategy_manager.get_strategy_info()
        for info in strategy_info:
            strategy = info['info']
            logger.info(f"🔹 {strategy['name']} ({info['key']})")
            logger.info(f"   描述: {strategy['description']}")
            logger.info(f"   前缀: {strategy['prefix']}")
            logger.info(f"   表: {', '.join(strategy['tables'])}")
        
        # 4. 测试策略
        logger.info("4️⃣ 测试策略...")
        strategy_manager.test_all_strategies()
        logger.info("✅ 策略测试完成")
        
        # 5. 测试扫描（如果有数据的话）
        logger.info("5️⃣ 测试策略扫描...")
        try:
            results = strategy_manager.scan_all_strategies()
            total_opportunities = sum(len(opps) for opps in results.values())
            logger.info(f"✅ 策略扫描完成，发现 {total_opportunities} 个机会")
        except Exception as e:
            logger.warning(f"⚠️ 策略扫描失败（可能是数据不足）: {e}")
        
        logger.info("🎉 新架构测试完成！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise

if __name__ == "__main__":
    test_new_architecture()
