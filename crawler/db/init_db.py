"""
Database Initialization Script - 适配现有数据库
"""
import os
import sys
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from crawler.db.models import (
    stock_index_model, 
    stock_kline_model, 
    stock_detail_model,
    industry_index_model,
    industry_kline_model,
    industry_stock_map_model,
    macro_economics_model,
    real_estate_model,
    hl_opportunity_history_model,
    hl_stock_summary_model,
    hl_meta_model
)
from crawler.db.db_manager import get_sync_db_manager


def check_database_connection():
    """检查数据库连接"""
    try:
        db = get_sync_db_manager()
        
        # 测试连接
        result = db.execute_query("SELECT 1 as test")
        if result and result[0]['test'] == 1:
            logger.info("Database connection test successful")
            db.disconnect()
            return True
        else:
            logger.error("Database connection test failed")
            db.disconnect()
            return False
            
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def show_table_info():
    """显示表信息"""
    try:
        db = get_sync_db_manager()
        
        tables = [
            'stockIndex', 'stockKline', 'stockDetail', 
            'industryIndex', 'industryKline', 'industryStockMap',
            'macroEconomics', 'realEstate',
            'HL_OpportunityHistory', 'HL_StockSummary', 'HL_Meta'
        ]
        
        for table in tables:
            try:
                count = db.get_table_count(table)
                logger.info(f"Table {table}: {count} records")
            except Exception as e:
                logger.warning(f"Table {table} not found or error: {e}")
        
        db.disconnect()
        
    except Exception as e:
        logger.error(f"Failed to show table info: {e}")


def test_model_operations():
    """测试模型操作"""
    logger.info("Testing model operations...")
    
    try:
        # 测试股票指数模型
        stocks = stock_index_model.get_all_stocks()
        logger.info(f"Found {len(stocks)} stocks in stockIndex table")
        
        # 测试行业指数模型
        industries = industry_index_model.get_all_industries()
        logger.info(f"Found {len(industries)} industries in industryIndex table")
        
        # 测试K线数据模型
        if stocks:
            first_stock = stocks[0]
            klines = stock_kline_model.get_stock_kline_data(
                first_stock['code'], 
                term='daily', 
                limit=5
            )
            logger.info(f"Found {len(klines)} kline records for stock {first_stock['code']}")
        
        logger.success("Model operations test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Model operations test failed: {e}")
        return False


def get_database_summary():
    """获取数据库摘要信息"""
    try:
        db = get_sync_db_manager()
        
        summary = {}
        
        # 获取各表的记录数
        tables = [
            'stockIndex', 'stockKline', 'stockDetail', 
            'industryIndex', 'industryKline', 'industryStockMap',
            'macroEconomics', 'realEstate',
            'HL_OpportunityHistory', 'HL_StockSummary', 'HL_Meta'
        ]
        
        for table in tables:
            try:
                count = db.get_table_count(table)
                summary[table] = count
            except Exception:
                summary[table] = 0
        
        # 获取最新数据时间
        try:
            latest_kline = db.execute_query(
                "SELECT MAX(dateTime) as latest FROM stockKline WHERE term = 'daily'"
            )
            if latest_kline and latest_kline[0]['latest']:
                summary['latest_kline_date'] = latest_kline[0]['latest'].strftime('%Y-%m-%d')
        except Exception:
            summary['latest_kline_date'] = 'Unknown'
        
        db.disconnect()
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get database summary: {e}")
        return {}


if __name__ == "__main__":
    logger.info("Starting database validation...")
    
    # 检查数据库连接
    if not check_database_connection():
        logger.error("Cannot connect to database. Please check your configuration.")
        sys.exit(1)
    
    # 显示表信息
    show_table_info()
    
    # 测试模型操作
    if not test_model_operations():
        logger.error("Model operations test failed")
        sys.exit(1)
    
    # 获取数据库摘要
    summary = get_database_summary()
    logger.info("Database Summary:")
    for table, count in summary.items():
        if table != 'latest_kline_date':
            logger.info(f"  {table}: {count} records")
        else:
            logger.info(f"  {table}: {count}")
    
    logger.success("Database validation completed successfully!") 