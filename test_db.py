#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager

def main():
    print("🚀 开始测试数据库...")
    
    # 初始化数据库
    db = DatabaseManager()
    
    # 获取股票索引
    stock_index_table = db.get_table_instance("stock_index")
    stock_idx = stock_index_table.get_stock_index()
    
    print(f"📊 总共有 {len(stock_idx)} 只股票")
    
    if len(stock_idx) > 0:
        print(f"🎯 第一只股票: {stock_idx[0]['code']} - {stock_idx[0]['name']}")
        if len(stock_idx) > 1:
            print(f"🎯 第二只股票: {stock_idx[1]['code']} - {stock_idx[1]['name']}")
    
    # 获取股票K线数据
    kline_table = db.get_table_instance("stock_kline_qfq")
    
    if len(stock_idx) > 1:
        stock_code = stock_idx[1]['code']  # 000002
        print(f"\n📈 检查股票 {stock_code} 的数据:")
        
        # 获取月度数据
        monthly_data = kline_table.get_all_klines_by_term(stock_code, 'monthly')
        print(f"   月度数据: {len(monthly_data)} 条")
        
        # 获取日度数据
        daily_data = kline_table.get_all_klines_by_term(stock_code, 'daily')
        print(f"   日度数据: {len(daily_data)} 条")
        
        if len(monthly_data) > 0:
            print(f"   最新月度数据: {monthly_data[0]}")
        if len(daily_data) > 0:
            print(f"   最新日度数据: {daily_data[0]}")

if __name__ == "__main__":
    main() 