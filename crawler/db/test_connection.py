"""
Test Database Connection
"""
import os
import sys
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from crawler.db import check_database_connection, show_table_info, test_model_operations, get_database_summary


def test_connection():
    """测试数据库连接"""
    logger.info("Testing database connection...")
    
    if check_database_connection():
        logger.success("Database connection successful!")
        return True
    else:
        logger.error("Database connection failed!")
        return False


def test_initialization():
    """测试数据库初始化"""
    logger.info("Testing database validation...")
    
    try:
        show_table_info()
        logger.success("Database validation successful!")
        return True
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return False


def test_table_info():
    """测试表信息查询"""
    logger.info("Testing table info...")
    
    try:
        show_table_info()
        logger.success("Table info query successful!")
        return True
    except Exception as e:
        logger.error(f"Table info query failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting database tests...")
    
    # 测试连接
    if not test_connection():
        sys.exit(1)
    
    # 测试初始化
    if not test_initialization():
        sys.exit(1)
    
    # 测试表信息
    if not test_table_info():
        sys.exit(1)
    
    logger.success("All database tests passed!") 