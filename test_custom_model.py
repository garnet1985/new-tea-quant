#!/usr/bin/env python3
"""
测试自定义模型功能
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import get_sync_db_manager

def test_custom_model():
    """测试自定义模型功能"""
    logger.info("🧪 开始测试自定义模型功能...")
    
    # 获取数据库管理器并初始化
    db = get_sync_db_manager()
    db.initialize()
    
    # 获取 stock_index 表的模型实例
    stock_index_model = db.get_base_table_instance('stock_index')
    
    # 检查模型类型
    logger.info(f"Stock Index 模型类型: {type(stock_index_model).__name__}")
    
    # 测试自定义方法
    if hasattr(stock_index_model, 'get_alive_stocks'):
        logger.info("✅ 自定义方法 get_alive_stocks 存在")
        alive_stocks = stock_index_model.get_alive_stocks()
        logger.info(f"活跃股票数量: {len(alive_stocks)}")
    else:
        logger.warning("❌ 自定义方法 get_alive_stocks 不存在")
    
    if hasattr(stock_index_model, 'search_stocks'):
        logger.info("✅ 自定义方法 search_stocks 存在")
        # 测试搜索功能
        search_result = stock_index_model.search_stocks('000001')
        logger.info(f"搜索结果数量: {len(search_result)}")
    else:
        logger.warning("❌ 自定义方法 search_stocks 不存在")
    
    # 测试基础方法（继承自 BaseTableModel）
    if hasattr(stock_index_model, 'count'):
        logger.info("✅ 基础方法 count 存在")
        total_count = stock_index_model.count()
        logger.info(f"表总记录数: {total_count}")
    else:
        logger.warning("❌ 基础方法 count 不存在")
    
    # 获取 meta_info 表的模型实例（应该使用 BaseTableModel）
    meta_info_model = db.get_base_table_instance('meta_info')
    logger.info(f"Meta Info 模型类型: {type(meta_info_model).__name__}")
    
    # 检查是否有自定义方法
    if hasattr(meta_info_model, 'get_alive_stocks'):
        logger.warning("❌ Meta Info 模型不应该有 get_alive_stocks 方法")
    else:
        logger.info("✅ Meta Info 模型没有自定义方法，使用 BaseTableModel")
    
    logger.info("🎉 自定义模型测试完成！")

if __name__ == "__main__":
    test_custom_model() 