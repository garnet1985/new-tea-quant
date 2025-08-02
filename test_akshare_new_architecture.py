#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare
from loguru import logger

def test_new_architecture():
    db = DatabaseManager()
    db.initialize()
    
    akshare = AKShare(db, is_verbose=True)
    
    print("=" * 60)
    print("测试新架构 AKShare 复权因子功能")
    print("=" * 60)
    
    test_stocks = [
        {'code': '000001', 'market': 'SZ'},
        {'code': '600000', 'market': 'SH'}
    ]
    
    print("\n1. 检查更新状态:")
    status = akshare.check_update_status()
    print(f"更新状态: {status}")
    
    print("\n2. 强制更新复权因子:")
    result = akshare.force_update_adj_factors(stock_index=test_stocks)
    print(f"更新结果: {result}")
    
    print("\n3. 验证因子存储:")
    factor = akshare.storage.get_adj_factor('000001', 'SZ', '20250801')
    print(f"000001.SZ 20250801 复权因子: {factor}")
    
    print("\n4. 测试增量更新:")
    result = akshare.renew_stock_K_line_factors(stock_index=test_stocks)
    print(f"增量更新结果: {result}")
    
    print("\n5. 获取更新信息:")
    info = akshare.get_update_info()
    print(f"更新信息: {info}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_new_architecture() 