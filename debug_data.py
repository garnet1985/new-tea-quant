#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager

def main():
    print("🚀 开始调试数据...")
    
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
    
    # 检查前10条月度数据
    print("\n📅 前10条月度数据:")
    for i in range(min(10, len(monthly_data))):
        record = monthly_data[i]
        print(f"   {i+1}. {record['date']} - 收盘价: {record['close']}")
    
    # 检查后10条月度数据
    print("\n📅 后10条月度数据:")
    for i in range(max(0, len(monthly_data)-10), len(monthly_data)):
        record = monthly_data[i]
        print(f"   {i+1}. {record['date']} - 收盘价: {record['close']}")
    
    # 检查前10条日度数据
    print("\n📅 前10条日度数据:")
    for i in range(min(10, len(daily_data))):
        record = daily_data[i]
        print(f"   {i+1}. {record['date']} - 收盘价: {record['close']}")
    
    # 检查后10条日度数据
    print("\n📅 后10条日度数据:")
    for i in range(max(0, len(daily_data)-10), len(daily_data)):
        record = daily_data[i]
        print(f"   {i+1}. {record['date']} - 收盘价: {record['close']}")

if __name__ == "__main__":
    main() 