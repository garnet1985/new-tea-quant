#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from datetime import datetime

def main():
    print("🚀 开始调试日期逻辑...")
    
    # 初始化数据库
    db = DatabaseManager()
    
    # 获取股票数据
    stock_idx = db.get_table_instance("stock_index").get_stock_index()
    stock = stock_idx[1]  # 000002
    
    print(f"🎯 测试股票: {stock['code']} - {stock['name']}")
    
    # 获取数据
    kline_table = db.get_table_instance("stock_kline_qfq")
    monthly_data = kline_table.get_all_klines_by_term(stock['code'], 'monthly')
    daily_data = kline_table.get_all_klines_by_term(stock['code'], 'daily')
    
    print(f"📊 月度数据: {len(monthly_data)} 条")
    print(f"📊 日度数据: {len(daily_data)} 条")
    
    # 测试日期
    test_date = "20080102"
    target_date = datetime.strptime(test_date, '%Y%m%d')
    print(f"\n🎯 测试日期: {test_date}")
    print(f"   目标日期对象: {target_date}")
    
    # 检查前20条月度数据
    print(f"\n📅 前20条月度数据与目标日期比较:")
    for i in range(min(20, len(monthly_data))):
        record = monthly_data[i]
        record_date = datetime.strptime(record['date'], '%Y%m%d')
        is_before = record_date < target_date
        print(f"   {i+1}. {record['date']} -> {record_date} {'<' if is_before else '>='} {target_date}")
    
    # 手动实现逻辑
    print(f"\n🔍 手动实现 get_records_before_date 逻辑:")
    before_records = []
    for i, record in enumerate(monthly_data):
        record_date = datetime.strptime(record['date'], '%Y%m%d')
        if record_date >= target_date:
            print(f"   找到第一个 >= 目标日期的记录: {record['date']} (索引 {i})")
            before_records = monthly_data[:i]
            break
    else:
        print(f"   所有记录都 < 目标日期")
        before_records = monthly_data
    
    print(f"   返回记录数: {len(before_records)}")

if __name__ == "__main__":
    main() 