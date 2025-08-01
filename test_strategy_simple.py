#!/usr/bin/env python3
"""
简单的策略测试脚本
"""

from utils.db.db_manager import DatabaseManager
from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy

def test_strategy():
    print("🔍 测试策略逻辑...")
    
    # 初始化数据库
    db = DatabaseManager()
    
    # 初始化策略
    strategy = HistoricLowStrategy(db, is_verbose=True)
    
    # 获取股票信息
    stock = {'code': '000002', 'name': '万科A', 'market': 'sz'}
    
    # 获取最新数据
    kline_table = db.get_table_instance('stock_kline_qfq')
    daily_data = kline_table.get_all_klines_by_term('000002', 'daily')
    monthly_data = kline_table.get_all_klines_by_term('000002', 'monthly')
    
    print(f"📊 数据统计:")
    print(f"   日度数据: {len(daily_data)} 条")
    print(f"   月度数据: {len(monthly_data)} 条")
    
    if daily_data and monthly_data:
        # 获取最新日度数据
        latest_daily = daily_data[-1]
        print(f"📅 最新日期: {latest_daily['date']}")
        print(f"💰 最新价格: {latest_daily['close']}")
        
        # 扫描投资机会
        opportunities = strategy.scan_single_stock(stock, latest_daily, monthly_data)
        
        if opportunities:
            print(f"✅ 发现投资机会！")
            print(f"   投资价格: {opportunities['opportunity_record']['close']}")
            print(f"   止损价格: {opportunities['goal']['loss']:.2f}")
            print(f"   止盈价格: {opportunities['goal']['win']:.2f}")
        else:
            print(f"❌ 未发现投资机会")
    else:
        print("❌ 没有数据")

if __name__ == "__main__":
    test_strategy() 