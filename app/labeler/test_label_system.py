#!/usr/bin/env python3
"""
测试标签系统

测试内容：
1. 数据表创建
2. 标签定义初始化
3. 标签计算功能
4. 标签质量评估
"""
import sys
import os
from datetime import datetime

# 将项目根目录添加到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from utils.db.db_manager import DatabaseManager
from app.labeler import LabelerService
from app.data_loader import DataLoader
from loguru import logger


def test_label_system():
    """测试标签系统"""
    logger.info("🚀 开始测试标签系统")
    
    # 初始化数据库管理器
    db_manager = DatabaseManager()
    db_manager.initialize()
    
    # 创建标签服务
    labeler_service = LabelerService(db_manager)
    
    # 1. 测试标签定义初始化
    logger.info("📋 测试标签定义初始化")
    labeler_service.definitions.initialize_default_definitions()
    
    # 验证标签定义
    all_definitions = labeler_service.definitions.get_all_categories()
    logger.info(f"标签分类: {all_definitions}")
    
    # 2. 测试标签计算
    logger.info("🧮 测试标签计算")
    
    # 获取前5只股票进行测试
    stock_list_table = db_manager.get_table_instance('stock_list')
    test_stocks = stock_list_table.load_filtered_stock_list()[:5]
    
    test_date = datetime.now().strftime('%Y-%m-%d')
    
    for stock in test_stocks:
        stock_id = stock['id']
        stock_name = stock['name']
        
        logger.info(f"计算股票标签: {stock_id} - {stock_name}")
        
        # 计算标签
        labels = labeler_service.calculate_stock_labels(stock_id, test_date)
        logger.info(f"  标签: {labels}")
        
        # 保存标签
        labeler_service.data_loader.save_stock_labels(stock_id, test_date, labels)
        
        # 验证保存
        saved_labels = labeler_service.data_loader.get_stock_labels(stock_id, test_date)
        logger.info(f"  保存的标签: {saved_labels}")
    
    # 3. 测试标签统计
    logger.info("📊 测试标签统计")
    stats = labeler_service.get_label_statistics(test_date)
    logger.info(f"标签统计: {stats}")
    
    # 4. 测试标签质量评估
    logger.info("🔍 测试标签质量评估")
    evaluation = labeler_service.evaluate_label_quality(test_date)
    logger.info(f"质量评估: {evaluation}")
    
    # 5. 测试标签查询
    logger.info("🔎 测试标签查询")
    
    # 查询大盘股
    large_cap_stocks = labeler_service.data_loader.label_loader.get_stocks_with_label('LARGE_CAP', test_date)
    logger.info(f"大盘股数量: {len(large_cap_stocks)}")
    
    # 查询成长股
    growth_stocks = labeler_service.data_loader.label_loader.get_stocks_with_label('GROWTH', test_date)
    logger.info(f"成长股数量: {len(growth_stocks)}")
    
    logger.info("✅ 标签系统测试完成")


def test_label_calculator():
    """测试标签计算器"""
    logger.info("🧮 测试标签计算器")
    
    db_manager = DatabaseManager()
    db_manager.initialize()
    
    from app.labeler.calculator import LabelCalculator
    calculator = LabelCalculator(db_manager)
    
    # 测试单只股票
    test_stock = '000001.SZ'
    test_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"测试股票: {test_stock}, 日期: {test_date}")
    
    # 测试各种标签计算
    market_cap_label = calculator.calculate_market_cap_label(test_stock, test_date)
    logger.info(f"市值标签: {market_cap_label}")
    
    industry_label = calculator.calculate_industry_label(test_stock, test_date)
    logger.info(f"行业标签: {industry_label}")
    
    volatility_label = calculator.calculate_volatility_label(test_stock, test_date)
    logger.info(f"波动性标签: {volatility_label}")
    
    volume_label = calculator.calculate_volume_label(test_stock, test_date)
    logger.info(f"成交量标签: {volume_label}")
    
    # 测试综合标签计算
    all_labels = calculator.calculate_all_labels(test_stock, test_date)
    logger.info(f"所有标签: {all_labels}")


if __name__ == "__main__":
    try:
        test_label_system()
        test_label_calculator()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
