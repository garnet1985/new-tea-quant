#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进的止损机制
验证确认性止损和多重止损价格
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService

def test_improved_stop_loss():
    """测试改进的止损机制"""
    print("🧪 测试改进的止损机制")
    print("=" * 60)
    
    strategy_service = HistoricLowService()
    
    # 模拟一个低点
    mock_low_point = {
        'price': 10.0,
        'price_range': {
            'min': 9.5,   # 区间下限
            'max': 10.5,  # 区间上限
            'percent': 5.0
        }
    }
    
    print(f"📊 模拟低点: 价格 {mock_low_point['price']:.2f}")
    print(f"   区间: [{mock_low_point['price_range']['min']:.2f}, {mock_low_point['price_range']['max']:.2f}] (±{mock_low_point['price_range']['percent']:.1f}%)")
    
    # 测试不同入场价格
    test_entry_prices = [9.5, 9.8, 10.0, 10.2, 10.5]
    
    print("\n🧪 测试不同入场价格的投资目标:")
    print("-" * 80)
    
    for entry_price in test_entry_prices:
        # 创建模拟记录
        mock_record = {
            'date': '20241201',
            'close': entry_price,
            'highest': entry_price * 1.02,
            'lowest': entry_price * 0.98
        }
        
        print(f"\n💰 入场价格: {entry_price:.2f}")
        
        # 计算基础投资目标
        targets = strategy_service.calculate_investment_targets(mock_record, mock_low_point)
        if targets:
            print(f"   基础止损价: {targets['stop_loss_price']:.2f} ({targets['stop_loss_percentage']:.1f}%)")
            print(f"   基础止盈价: {targets['take_profit_price']:.2f} ({targets['take_profit_percentage']:.1f}%)")
            print(f"   Buffer: {targets['buffer_percentage']:.1f}%")
        
        # 计算改进的止损参数
        buffer_params = strategy_service.calculate_percentage_buffer_stop_loss(
            entry_price, 
            mock_low_point['price_range']['min']
        )
        
        print(f"   🔒 百分比缓冲止损机制:")
        print(f"      基础止损价: {buffer_params['base_stop_loss']:.2f}")
        print(f"      缓冲带下限: {buffer_params['buffer_zone_bottom']:.2f} (区间下限下方{buffer_params['buffer_percentage']:.1f}%)")
        print(f"      缓冲带宽度: {buffer_params['buffer_zone_width']:.2f}元")
        print(f"      入场Buffer: {buffer_params['entry_buffer_percentage']:.1f}%")
    
    print("\n🧪 测试止损触发逻辑:")
    print("-" * 80)
    
    # 测试不同当前价格的止损判断
    entry_price = 10.0
    price_range_min = 9.5
    
    print(f"📊 入场价格: {entry_price:.2f}, 区间下限: {price_range_min:.2f}")
    
    test_current_prices = [10.5, 10.0, 9.8, 9.5, 9.2, 8.8, 8.5]
    
    for current_price in test_current_prices:
        # 计算基础止损价
        price_buffer = entry_price - price_range_min
        buffer_percentage = max(price_buffer / price_range_min, 0.05)
        base_stop_loss = entry_price - (price_range_min * buffer_percentage)
        
        # 判断是否应该止损
        should_stop = strategy_service.should_stop_loss(
            current_price, 
            entry_price, 
            price_range_min
        )
        
        # 计算缓冲带下限
        buffer_zone_bottom = price_range_min * 0.97  # 3%缓冲带
        
        # 计算跌破区间下限和缓冲带的百分比
        if current_price < price_range_min:
            drop_below_min = (price_range_min - current_price) / price_range_min
            drop_percent = drop_below_min * 100
        else:
            drop_percent = 0
            
        if current_price < buffer_zone_bottom:
            drop_below_buffer = (buffer_zone_bottom - current_price) / buffer_zone_bottom
            buffer_percent = drop_below_buffer * 100
        else:
            buffer_percent = 0
        
        status = "🔴 止损" if should_stop else "🟢 持有"
        print(f"   当前价格: {current_price:.2f} → {status}")
        
        if current_price < price_range_min:
            print(f"     跌破区间下限: {drop_percent:.1f}%")
        
        if current_price < buffer_zone_bottom:
            print(f"     跌破缓冲带: {buffer_percent:.1f}%")
        
        if should_stop:
            print(f"     触发缓冲带止损 (跌破缓冲带下限)")
    
    print("\n📊 止损机制测试完成！")
    print("\n💡 改进要点:")
    print("1. 基础止损价：基于入场价格和buffer计算")
    print("2. 缓冲带下限：区间下限下方增加3%缓冲带")
    print("3. 缓冲带止损：只有跌破缓冲带才触发止损")
    print("4. 风险控制：避免短期波动导致的频繁止损")

if __name__ == "__main__":
    test_improved_stop_loss()
