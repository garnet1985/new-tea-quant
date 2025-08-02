#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare
from loguru import logger

def test_first_run_logic():
    db = DatabaseManager()
    db.initialize()
    
    akshare = AKShare(db, is_verbose=True)
    
    print("=" * 60)
    print("测试首次运行逻辑")
    print("=" * 60)
    
    # 清空数据库中的复权因子数据，模拟首次运行
    print("\n1. 清空复权因子数据，模拟首次运行:")
    adj_factor_table = db.get_table_instance('adj_factor')
    meta_info_table = db.get_table_instance('meta_info')
    
    adj_factor_table.execute_raw_update("DELETE FROM adj_factor")
    meta_info_table.execute_raw_update("DELETE FROM meta_info")
    print("已清空复权因子数据")
    
    test_stocks = [
        {'code': '000001', 'market': 'SZ'},
        {'code': '600000', 'market': 'SH'}
    ]
    
    print("\n2. 检查是否为首运行:")
    is_first = akshare.service.is_first_run(akshare.storage)
    print(f"是否首次运行: {is_first}")
    
    print("\n3. 获取首次运行的日期范围:")
    start_date, end_date = akshare.service.get_full_date_range_for_first_run()
    print(f"日期范围: {start_date} 到 {end_date}")
    
    print("\n4. 执行首次运行更新:")
    result = akshare.renew_stock_K_line_factors(stock_index=test_stocks)
    print(f"首次运行结果: {result}")
    
    print("\n5. 验证因子存储:")
    # 检查不同日期的因子
    test_dates = ['20080101', '20100101', '20200101', '20250801']
    for test_date in test_dates:
        factor = akshare.storage.get_adj_factor('000001', 'SZ', test_date)
        if factor:
            print(f"000001.SZ {test_date} 复权因子: {factor['hfq_factor']}")
        else:
            print(f"000001.SZ {test_date} 无复权因子")
    
    print("\n6. 检查更新状态:")
    status = akshare.check_update_status()
    print(f"更新状态: {status}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_first_run_logic() 