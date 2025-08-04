#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_manager import DataSourceManager

async def test_data_source_manager():
    """测试DataSourceManager的renew_data方法"""

    print("=" * 70)
    print("测试DataSourceManager的renew_data方法")
    print("=" * 70)

    # 初始化数据库和DataSourceManager
    db = DatabaseManager()
    db.initialize()

    data_source = DataSourceManager(db, is_verbose=True)

    print("开始执行数据更新...")
    
    try:
        # 执行数据更新
        await data_source.renew_data()
        
        print("\n" + "=" * 70)
        print("数据更新完成")
        print("=" * 70)
        
        # 验证结果
        print(f"最新交易日: {data_source.latest_market_open_day}")
        print(f"股票指数数量: {len(data_source.latest_stock_index) if data_source.latest_stock_index else 0}")
        
        if data_source.latest_stock_index:
            print("\n股票指数示例 (前3条):")
            for i, stock in enumerate(data_source.latest_stock_index[:3], 1):
                print(f"  {i}. {stock}")
        
        # 检查复权因子更新状态
        print("\n" + "=" * 70)
        print("检查复权因子更新状态")
        print("=" * 70)
        
        akshare = data_source.sources['akshare']
        update_info = akshare.get_update_info()
        print(f"复权因子更新状态: {update_info}")
        
        # 检查数据库中的复权因子记录
        print("\n" + "=" * 70)
        print("检查数据库中的复权因子记录")
        print("=" * 70)
        
        # 查询复权因子记录数
        count_query = "SELECT COUNT(*) as count FROM adj_factor"
        count_result = db.execute_sync_query(count_query)
        total_count = count_result[0]['count'] if count_result else 0
        print(f"总复权因子记录数: {total_count}")
        
        # 查询最新的复权因子记录
        latest_query = """
            SELECT ts_code, date, qfq_factor, hfq_factor
            FROM adj_factor
            ORDER BY date DESC
            LIMIT 5
        """
        latest_result = db.execute_sync_query(latest_query)
        
        if latest_result:
            print("\n最新复权因子记录:")
            for i, row in enumerate(latest_result, 1):
                print(f"  {i}. {row['ts_code']} {row['date']}: QFQ={row['qfq_factor']:.6f}, HFQ={row['hfq_factor']:.6f}")
        else:
            print("无复权因子记录")
            
    except Exception as e:
        print(f"❌ 数据更新失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_data_source_manager()) 