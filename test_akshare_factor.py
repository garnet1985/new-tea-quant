#!/usr/bin/env python3
"""
测试 AKShare 复权因子计算功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare
from loguru import logger

def test_factor_calculation():
    """测试复权因子计算功能"""
    
    # 初始化数据库连接
    db = DatabaseManager()
    db.initialize()
    
    # 初始化 AKShare
    akshare = AKShare(db, is_verbose=True)
    
    print("=" * 60)
    print("测试 AKShare 复权因子计算功能")
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
    
    # 2. 获取复权因子数据
    print("\n2. 获取复权因子数据:")
    try:
        # 获取000001的复权因子
        factors = akshare.get_stock_adj_factors('000001', 'SZ', '20250801', '20250802')
        print(f"000001.SZ 复权因子: {factors}")
        
        # 获取最新复权因子
        latest_factor = akshare.get_latest_adj_factor('000001', 'SZ')
        print(f"000001.SZ 最新复权因子: {latest_factor}")
        
    except Exception as e:
        print(f"获取复权因子失败: {e}")
    
    # 3. 测试复权价格计算
    print("\n3. 测试复权价格计算:")
    try:
        # 假设原始价格为10.0
        raw_price = 10.0
        trade_date = '20250801'
        
        # 计算前复权价格
        qfq_price = akshare.calculate_qfq_price('000001', 'SZ', trade_date, raw_price)
        print(f"原始价格: {raw_price}, 前复权价格: {qfq_price}")
        
        # 计算后复权价格
        hfq_price = akshare.calculate_hfq_price('000001', 'SZ', trade_date, raw_price)
        print(f"原始价格: {raw_price}, 后复权价格: {hfq_price}")
        
    except Exception as e:
        print(f"计算复权价格失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_factor_calculation()
