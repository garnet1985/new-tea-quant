#!/usr/bin/env python3
"""
测试多进程数据库连接
"""
import multiprocessing
import pymysql
from utils.db.db_config import DB_CONFIG

def worker_process(stock_id):
    """工作进程函数"""
    try:
        print(f"进程 {multiprocessing.current_process().pid} 开始处理股票 {stock_id}")
        
        # 创建独立的pymysql连接
        connection = pymysql.connect(
            host=DB_CONFIG['base']['host'],
            port=DB_CONFIG['base']['port'],
            user=DB_CONFIG['base']['user'],
            password=DB_CONFIG['base']['password'],
            database=DB_CONFIG['base']['database'],
            charset='utf8mb4',
            autocommit=True
        )
        
        print(f"进程 {multiprocessing.current_process().pid} 连接成功")
        
        # 查询数据
        cursor = connection.cursor()
        cursor.execute("""
            SELECT date, open, close, highest, lowest, volume, amount
            FROM stock_kline 
            WHERE id = %s AND term = 'daily'
            ORDER BY date ASC
            LIMIT 5
        """, (stock_id,))
        
        results = cursor.fetchall()
        print(f"进程 {multiprocessing.current_process().pid} 查询到 {len(results)} 条记录")
        
        cursor.close()
        connection.close()
        
        print(f"进程 {multiprocessing.current_process().pid} 处理完成")
        return f"成功处理 {stock_id}"
        
    except Exception as e:
        print(f"进程 {multiprocessing.current_process().pid} 处理失败: {e}")
        return f"失败: {e}"

def test_multiprocess_db():
    """测试多进程数据库访问"""
    print("开始多进程数据库测试...")
    
    # 测试股票列表
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '002001.SZ']
    
    # 使用进程池
    with multiprocessing.Pool(processes=3) as pool:
        results = pool.map(worker_process, test_stocks)
    
    print("多进程测试结果:")
    for i, result in enumerate(results):
        print(f"  {test_stocks[i]}: {result}")

if __name__ == "__main__":
    test_multiprocess_db()
