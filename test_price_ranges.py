#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试价格区间功能
展示动态百分比阈值和价格区间的效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.data_source.data_source_service import DataSourceService
from utils.db.db_manager import DatabaseManager

def test_price_ranges():
    """测试价格区间功能"""
    print("🔍 测试价格区间功能")
    print("=" * 60)
    
    # 初始化服务
    strategy_service = HistoricLowService()
    data_source_service = DataSourceService()
    
    # 获取股票数据
    stock_id = "000002.SZ"
    print(f"📊 分析股票: {stock_id}")
    
    # 获取日线数据
    db_manager = DatabaseManager()
    db_manager.connect()
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
    
    # 应用前复权
    print("🔧 应用前复权处理...")
    adj_factor_table = db_manager.get_table_instance("adj_factor")
    qfq_factors = adj_factor_table.get_stock_factors(stock_id)
    daily_data = data_source_service.to_qfq(daily_data, qfq_factors)
    print("✅ 前复权处理完成")
    
    # 过滤负价格
    daily_data = [record for record in daily_data if record['close'] > 0]
    print(f"✅ 过滤负价格后剩余 {len(daily_data)} 条数据")
    
    # 获取最终整合结果
    print("\n📊 获取最终整合结果...")
    merged_lows = strategy_service.find_merged_historic_lows(daily_data)
    
    if not merged_lows:
        print("❌ 未找到历史低点")
        return
    
    print(f"\n📋 共找到 {len(merged_lows)} 个历史低点")
    print("\n🏆 前20个支撑位详细信息:")
    print("-" * 80)
    
    for i, low_point in enumerate(merged_lows[:20], 1):
        price = low_point['price']
        date = low_point['date']
        sources = low_point['conclusion_from']
        
        # 显示价格区间信息
        if 'price_range' in low_point:
            price_range = low_point['price_range']
            range_min = price_range['min']
            range_max = price_range['max']
            range_percent = price_range['percent']
            
            print(f"{i:2d}. {date} - 价格: {price:6.2f} 区间: [{range_min:5.2f}, {range_max:5.2f}] (±{range_percent:.0f}%)")
            print(f"    来源: {sources}")
            
            # 计算投资实用性
            if i < len(merged_lows):
                next_price = merged_lows[i]['price']
                distance = abs(price - next_price)
                print(f"    与下一个支撑位距离: {distance:.2f}元")
        else:
            print(f"{i:2d}. {date} - 价格: {price:6.2f} (无价格区间信息)")
            print(f"    来源: {sources}")
        
        print()
    
    # 分析价格区间分布
    print("\n📊 价格区间分布分析:")
    print("-" * 40)
    
    price_ranges = []
    for low_point in merged_lows:
        if 'price_range' in low_point:
            price_range = low_point['price_range']
            price_ranges.append({
                'price': low_point['price'],
                'range_min': price_range['min'],
                'range_max': price_range['max'],
                'range_percent': price_range['percent'],
                'range_width': price_range['max'] - price_range['min']
            })
    
    # 按价格区间分组统计
    low_price = [p for p in price_ranges if p['price'] <= 5.0]
    mid_price = [p for p in price_ranges if 5.0 < p['price'] <= 20.0]
    high_price = [p for p in price_ranges if 20.0 < p['price'] <= 50.0]
    ultra_price = [p for p in price_ranges if p['price'] > 50.0]
    
    print(f"低价区间 (≤5元): {len(low_price)} 个, 平均区间宽度: {sum(p['range_width'] for p in low_price)/len(low_price):.2f}元" if low_price else "低价区间 (≤5元): 0 个")
    print(f"中价区间 (5-20元): {len(mid_price)} 个, 平均区间宽度: {sum(p['range_width'] for p in mid_price)/len(mid_price):.2f}元" if mid_price else "中价区间 (5-20元): 0 个")
    print(f"高价区间 (20-50元): {len(high_price)} 个, 平均区间宽度: {sum(p['range_width'] for p in high_price)/len(high_price):.2f}元" if high_price else "高价区间 (20-50元): 0 个")
    print(f"超高价格 (≥50元): {len(ultra_price)} 个, 平均区间宽度: {sum(p['range_width'] for p in ultra_price)/len(ultra_price):.2f}元" if ultra_price else "超高价格 (≥50元): 0 个")
    
    # 检查关键支撑位的价格区间
    print("\n🔍 关键支撑位价格区间检查:")
    print("-" * 40)
    
    key_levels = [
        {"name": "6.3-6.4元", "min": 6.3, "max": 6.4},
        {"name": "12.7-12.9元", "min": 12.7, "max": 12.9},
        {"name": "15.9元", "min": 15.0, "max": 15.95},
        {"name": "20.7元", "min": 20.4, "max": 21.0}
    ]
    
    for level in key_levels:
        found = False
        for low_point in merged_lows:
            if 'price_range' in low_point:
                price_range = low_point['price_range']
                # 检查价格区间是否与关键支撑位重叠
                if (price_range['min'] <= level['max'] and price_range['max'] >= level['min']):
                    print(f"✅ {level['name']}: 与支撑位 {low_point['price']:.2f} 区间 [{price_range['min']:.2f}, {price_range['max']:.2f}] 重叠")
                    found = True
                    break
        
        if not found:
            print(f"❌ {level['name']}: 未找到重叠的支撑位区间")

if __name__ == "__main__":
    test_price_ranges()
