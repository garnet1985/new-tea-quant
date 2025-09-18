#!/usr/bin/env python3
"""
简单测试数据库连接
"""
import pymysql
from utils.db.db_config import DB_CONFIG

def test_simple_connection():
    """测试简单的数据库连接"""
    try:
        print("测试数据库连接...")
        print(f"连接参数: {DB_CONFIG['base']}")
        
        # 创建连接
        connection = pymysql.connect(
            host=DB_CONFIG['base']['host'],
            port=DB_CONFIG['base']['port'],
            user=DB_CONFIG['base']['user'],
            password=DB_CONFIG['base']['password'],
            database=DB_CONFIG['base']['database'],
            charset='utf8mb4',
            autocommit=True
        )
        
        print("✅ 数据库连接成功")
        
        # 测试查询
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM stock_kline LIMIT 1")
        result = cursor.fetchone()
        print(f"✅ 查询成功，结果: {result}")
        
        cursor.close()
        connection.close()
        print("✅ 连接关闭成功")
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")

if __name__ == "__main__":
    test_simple_connection()
