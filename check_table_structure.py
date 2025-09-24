#!/usr/bin/env python3
"""
检查数据库表结构
"""
import pymysql
from utils.db.db_config import DB_CONFIG

def check_table_structure():
    """检查表结构"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG['base']['host'],
            port=DB_CONFIG['base']['port'],
            user=DB_CONFIG['base']['user'],
            password=DB_CONFIG['base']['password'],
            database=DB_CONFIG['base']['database'],
            charset='utf8mb4',
            autocommit=True
        )
        
        cursor = connection.cursor()
        
        # 检查表是否存在
        cursor.execute("SHOW TABLES LIKE 'stock_kline'")
        tables = cursor.fetchall()
        print(f"stock_kline 表存在: {len(tables) > 0}")
        
        if len(tables) > 0:
            # 查看表结构
            cursor.execute("DESCRIBE stock_kline")
            columns = cursor.fetchall()
            print("stock_kline 表结构:")
            for col in columns:
                print(f"  {col[0]} - {col[1]}")
            
            # 查看一些样本数据
            cursor.execute("SELECT * FROM stock_kline LIMIT 3")
            samples = cursor.fetchall()
            print(f"\n样本数据 (共 {len(samples)} 条):")
            for sample in samples:
                print(f"  {sample}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"检查表结构失败: {e}")

if __name__ == "__main__":
    check_table_structure()
