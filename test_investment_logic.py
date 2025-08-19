#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的投资逻辑
验证基于低点价格区间的投资触发和止损止盈计算
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.data_source.data_source_service import DataSourceService
from utils.db.db_manager import DatabaseManager

def test_investment_logic():
    """测试投资逻辑"""
    print("🧪 测试新的投资逻辑")
    print("=" * 60)
    
    strategy_service = HistoricLowService()
    data_source_service = DataSourceService()
    stock_id = "000002.SZ"
    
    print(f"📊 分析股票: {stock_id}")
    
    # 连接数据库
    db_manager = DatabaseManager()
    db_manager.connect()
    
    # 获取日线数据
    daily_table = db_manager.get_table_instance("stock_kline")
    daily_data = daily_table.load(
        condition="id = %s AND term = %s",
        params=(stock_id, "daily"),
        order_by="date ASC"
    )
    
    if not daily_data:
        print("❌ 未找到日线数据")
        return
    
    print(f"✅ 获取到 {len(daily_data)} 条日线数据")
    
    # 应用前复权处理
    print("🔧 应用前复权处理...")
    adj_factor_table = db_manager.get_table_instance("adj_factor")
    qfq_factors = adj_factor_table.get_stock_factors(stock_id)
    daily_data = data_source_service.to_qfq(daily_data, qfq_factors)
    print("✅ 前复权处理完成")
    
    # 过滤负价格
    daily_data = [record for record in daily_data if record['close'] > 0]
    print(f"✅ 过滤负价格后剩余 {len(daily_data)} 条数据")
    
    # 获取历史低点
    print("\n📊 获取历史低点...")
    merged_lows = strategy_service.find_merged_historic_lows(daily_data)
    
    if not merged_lows:
        print("❌ 未找到历史低点")
        return
    
    print(f"✅ 找到 {len(merged_lows)} 个历史低点")
    
    # 选择几个低点进行测试
    test_low_points = merged_lows[:5]  # 前5个低点
    
    print("\n🧪 测试投资逻辑:")
    print("-" * 80)
    
    for i, low_point in enumerate(test_low_points, 1):
        price = low_point['price']
        date = low_point['date']
        price_range = low_point['price_range']
        
        print(f"\n{i}. 低点: {date} - 价格: {price:.2f}")
        print(f"   区间: [{price_range['min']:.2f}, {price_range['max']:.2f}] (±{price_range['percent']:.1f}%)")
        print(f"   来源: {low_point['conclusion_from']}")
        
        # 模拟不同价格的投资情况
        test_prices = [
            float(price_range['min']),  # 区间下限
            float(price),               # 低点价格
            float(price_range['max']),  # 区间上限
            (float(price_range['min']) + float(price)) / 2,  # 区间中点
            float(price_range['min']) * 0.95,  # 低于区间下限
            float(price_range['max']) * 1.05   # 高于区间上限
        ]
        
        for test_price in test_prices:
            # 创建模拟记录
            mock_record = {
                'date': '20241201',
                'close': test_price,
                'highest': test_price * 1.02,
                'lowest': test_price * 0.98
            }
            
            # 检查是否在投资范围内
            in_range = strategy_service.is_in_invest_range(mock_record, low_point)
            
            if in_range:
                # 计算投资目标
                targets = strategy_service.calculate_investment_targets(mock_record, low_point)
                
                print(f"   💰 价格 {test_price:.2f} → 触发投资 ✅")
                print(f"      入场价: {targets['entry_price']:.2f}")
                print(f"      止损价: {targets['stop_loss_price']:.2f} ({targets['stop_loss_percentage']:.1f}%)")
                print(f"      止盈价: {targets['take_profit_price']:.2f} ({targets['take_profit_percentage']:.1f}%)")
                print(f"      Buffer: {targets['buffer_percentage']:.1f}%")
            else:
                print(f"   ❌ 价格 {test_price:.2f} → 不在投资范围")
    
    print("\n📊 投资逻辑测试完成！")
    
    # 关闭数据库连接
    db_manager.close()

if __name__ == "__main__":
    test_investment_logic()
