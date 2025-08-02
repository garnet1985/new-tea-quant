#!/usr/bin/env python3
"""
简单测试 AKShare 复权因子更新频率控制功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare
from loguru import logger

def test_simple():
    """简单测试"""
    
    # 初始化数据库连接
    db = DatabaseManager()
    db.initialize()
    
    # 初始化 AKShare
    akshare = AKShare(db, is_verbose=True)
    
    print("=" * 50)
    print("简单测试 AKShare 功能")
    print("=" * 50)
    
    # 1. 检查状态
    print("\n1. 检查更新状态:")
    status = akshare.check_update_status()
    print(f"状态: {status}")
    
    # 2. 测试更新（使用少量股票）
    print("\n2. 测试更新:")
    test_stocks = [
        {'code': '000001', 'market': 'SZ'},
        {'code': '600000', 'market': 'SH'}
    ]
    
    try:
        result = akshare.renew_stock_K_line_factors(stock_index=test_stocks)
        print(f"更新结果: {result}")
    except Exception as e:
        print(f"更新失败: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    test_simple() 