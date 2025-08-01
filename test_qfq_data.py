#!/usr/bin/env python3
"""
测试前复权数据获取
"""

import tushare as ts
import pandas as pd
from datetime import datetime, timedelta

def test_qfq_data():
    """测试前复权数据获取"""
    
    # 设置token（请替换为你的token）
    ts.set_token('your_token_here')  # 请替换为实际token
    
    # 测试股票代码
    ts_code = '000001.SZ'  # 平安银行
    
    # 获取最近30天的数据
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    print(f"测试股票: {ts_code}")
    print(f"时间范围: {start_date} 到 {end_date}")
    print("-" * 50)
    
    # 测试日线前复权数据
    print("1. 日线前复权数据:")
    try:
        daily_qfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
        if daily_qfq is not None and not daily_qfq.empty:
            print(f"   获取到 {len(daily_qfq)} 条日线数据")
            print(f"   最新数据: {daily_qfq.iloc[0].to_dict()}")
        else:
            print("   未获取到数据")
    except Exception as e:
        print(f"   获取日线数据失败: {e}")
    
    print()
    
    # 测试周线前复权数据
    print("2. 周线前复权数据:")
    try:
        weekly_qfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq', freq='W')
        if weekly_qfq is not None and not weekly_qfq.empty:
            print(f"   获取到 {len(weekly_qfq)} 条周线数据")
            print(f"   最新数据: {weekly_qfq.iloc[0].to_dict()}")
        else:
            print("   未获取到数据")
    except Exception as e:
        print(f"   获取周线数据失败: {e}")
    
    print()
    
    # 测试月线前复权数据
    print("3. 月线前复权数据:")
    try:
        monthly_qfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq', freq='M')
        if monthly_qfq is not None and not monthly_qfq.empty:
            print(f"   获取到 {len(monthly_qfq)} 条月线数据")
            print(f"   最新数据: {monthly_qfq.iloc[0].to_dict()}")
        else:
            print("   未获取到数据")
    except Exception as e:
        print(f"   获取月线数据失败: {e}")

if __name__ == "__main__":
    test_qfq_data() 