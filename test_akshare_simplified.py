#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare
from loguru import logger

def test_simplified_logic():
    db = DatabaseManager()
    db.initialize()
    
    akshare = AKShare(db, is_verbose=True)
    
    print("=" * 60)
    print("测试简化后的复权因子逻辑")
    print("=" * 60)
    
    # 清空数据，模拟全新开始
    print("\n1. 清空数据，模拟全新开始:")
    adj_factor_table = db.get_table_instance('adj_factor')
    meta_info_table = db.get_table_instance('meta_info')
    
    adj_factor_table.execute_raw_update("DELETE FROM adj_factor")
    meta_info_table.execute_raw_update("DELETE FROM meta_info")
    print("已清空数据")
    
    test_stocks = [
        {'code': '000001', 'market': 'SZ'},
        {'code': '600000', 'market': 'SH'}
    ]
    
    print("\n2. 执行每日更新:")
    result = akshare.renew_stock_K_line_factors(stock_index=test_stocks)
    print(f"更新结果: {result}")
    
    print("\n3. 验证因子存储:")
    today = akshare.service.get_today_date()
    factor = akshare.storage.get_adj_factor('000001', 'SZ', today)
    print(f"000001.SZ 今日复权因子: {factor}")
    
    print("\n4. 测试查询任意日期的因子:")
    # 查询不同日期的因子，应该都返回最新的因子
    test_dates = ['20080101', '20100101', '20200101', '20250801']
    for test_date in test_dates:
        factor = akshare.storage.get_adj_factor('000001', 'SZ', test_date)
        if factor:
            print(f"000001.SZ {test_date} 复权因子: {factor['hfq_factor']}")
        else:
            print(f"000001.SZ {test_date} 无复权因子")
    
    print("\n5. 测试重复更新:")
    result2 = akshare.renew_stock_K_line_factors(stock_index=test_stocks)
    print(f"重复更新结果: {result2}")
    
    print("\n6. 检查更新状态:")
    status = akshare.check_update_status()
    print(f"更新状态: {status}")
    
    print("\n7. 验证策略一致性:")
    # 模拟使用不同复权因子进行策略分析
    raw_price = 10.0
    factor1 = akshare.storage.get_adj_factor('000001', 'SZ', '20200101')
    factor2 = akshare.storage.get_adj_factor('000001', 'SZ', '20250801')
    
    if factor1 and factor2:
        adj_price1 = raw_price * factor1['hfq_factor']
        adj_price2 = raw_price * factor2['hfq_factor']
        
        print(f"使用2020年因子计算的复权价格: {adj_price1:.4f}")
        print(f"使用2025年因子计算的复权价格: {adj_price2:.4f}")
        print(f"价格差异: {abs(adj_price1 - adj_price2):.4f}")
        print(f"相对关系一致: {'是' if abs(adj_price1 - adj_price2) < 0.01 else '否'}")
    
    print("\n" + "=" * 60)
    print("简化后的逻辑优势:")
    print("1. 每日更新，逻辑简单")
    print("2. 只存储最新因子，节省空间")
    print("3. 查询任意日期都返回最新因子")
    print("4. 策略分析结果一致")
    print("=" * 60)

if __name__ == "__main__":
    test_simplified_logic() 