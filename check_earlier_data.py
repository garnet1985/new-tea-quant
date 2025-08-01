#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from datetime import datetime

def main():
    print("🚀 检查更早的月度数据...")
    
    # 初始化数据库
    db = DatabaseManager()
    
    # 获取股票数据
    stock_idx = db.get_table_instance("stock_index").get_stock_index()
    stock = stock_idx[1]  # 000002
    
    print(f"🎯 测试股票: {stock['code']} - {stock['name']}")
    
    # 获取数据
    kline_table = db.get_table_instance("stock_kline")
    monthly_data = kline_table.get_all_klines_by_term(stock['code'], 'monthly')
    
    print(f"📊 月度数据: {len(monthly_data)} 条")
    
    # 检查所有月度数据的年份分布
    year_count = {}
    for record in monthly_data:
        year = record['date'][:4]
        year_count[year] = year_count.get(year, 0) + 1
    
    print(f"\n📅 年度分布:")
    for year in sorted(year_count.keys()):
        print(f"   {year}: {year_count[year]} 条")
    
    # 检查最早的月度数据
    print(f"\n📅 最早的10条月度数据:")
    for i in range(min(10, len(monthly_data))):
        record = monthly_data[i]
        print(f"   {i+1}. {record['date']} - 收盘价: {record['close']}")
    
    # 检查2007年的数据
    print(f"\n📅 2007年的月度数据:")
    year_2007_data = [r for r in monthly_data if r['date'].startswith('2007')]
    for record in year_2007_data:
        print(f"   {record['date']} - 收盘价: {record['close']}")
    
    print(f"   2007年数据总数: {len(year_2007_data)}")

if __name__ == "__main__":
    main() 