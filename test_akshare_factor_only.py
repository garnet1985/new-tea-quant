#!/usr/bin/env python3
"""
测试 AKShare 复权因子功能（配合 Tushare 数据使用）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare
from loguru import logger

def test_factor_only():
    """测试复权因子功能"""
    
    # 初始化数据库连接
    db = DatabaseManager()
    db.initialize()
    
    # 初始化 AKShare
    akshare = AKShare(db, is_verbose=True)
    
    print("=" * 60)
    print("测试 AKShare 复权因子功能（配合 Tushare 数据）")
    print("=" * 60)
    
    # 1. 强制更新复权因子
    print("\n1. 强制更新复权因子:")
    test_stocks = [
        {'code': '000001', 'market': 'SZ'},
        {'code': '600000', 'market': 'SH'}
    ]
    
    try:
        result = akshare.force_update_adj_factors(stock_index=test_stocks)
        print(f"强制更新结果: {result}")
    except Exception as e:
        print(f"强制更新失败: {e}")
        return
    
    # 2. 验证复权因子已存储到数据库
    print("\n2. 验证复权因子已存储到数据库:")
    try:
        # 直接从存储层获取复权因子
        factor = akshare.storage.get_adj_factor('000001', 'SZ', '20250801')
        print(f"000001.SZ 20250801 复权因子: {factor}")
        
        # 获取最新复权因子
        latest_factor = akshare.storage.get_latest_adj_factor('000001', 'SZ')
        print(f"000001.SZ 最新复权因子: {latest_factor}")
        
    except Exception as e:
        print(f"验证复权因子失败: {e}")
    
    # 3. 验证批量获取复权因子
    print("\n3. 验证批量获取复权因子:")
    try:
        factors = akshare.storage.get_adj_factors_by_date_range('000001', 'SZ', '20250801', '20250802')
        print(f"000001.SZ 复权因子列表: {factors}")
        
    except Exception as e:
        print(f"批量获取复权因子失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n使用说明:")
    print("1. AKShare 负责获取和存储复权因子到 adj_factor 表")
    print("2. Tushare 负责提供不复权K线数据")
    print("3. 策略层直接从 adj_factor 表读取因子进行计算")
    print("=" * 60)

if __name__ == "__main__":
    test_factor_only() 