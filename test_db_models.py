#!/usr/bin/env python3
"""
测试数据库模型功能
"""

import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.analyser.strategy.strategy_manager import StrategyManager

def test_db_models():
    """测试数据库模型功能"""
    
    logger.info("🧪 开始测试数据库模型功能...")
    
    try:
        # 创建数据库管理器
        db = DatabaseManager()
        db.set_verbose(True)  # 开启详细日志
        
        # 初始化数据库（包含策略模型和表创建）
        logger.info("📊 初始化数据库...")
        db.initialize()
        
        # 验证表是否创建成功
        logger.info("✅ 验证表创建结果...")
        
        # 通过数据库管理器获取表实例
        hl_meta_table = db.get_table_instance('HL_meta')
        if hl_meta_table:
            logger.info(f"✅ HL_meta 表获取成功: {hl_meta_table.table_name}")
            
            # 测试获取最新元数据
            latest_meta = hl_meta_table.load_one(order_by="dateTime DESC")
            logger.info(f"📊 最新元数据: {latest_meta}")
        else:
            logger.error("❌ HL_meta 表获取失败")
        
        # 验证其他表
        hl_opportunity_table = db.get_table_instance('HL_opportunity_history')
        hl_summary_table = db.get_table_instance('HL_strategy_summary')
        
        logger.info(f"📋 验证的表: HL_meta={hl_meta_table is not None}, HL_opportunity_history={hl_opportunity_table is not None}, HL_strategy_summary={hl_summary_table is not None}")
        
        logger.info("🎉 数据库模型测试完成！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_db_models() 