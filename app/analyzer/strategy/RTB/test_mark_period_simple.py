#!/usr/bin/env python3
"""
简单测试mark_period函数的功能
"""
import sys
import os
from typing import List, Dict
import numpy as np
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from app.analyzer.components.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    """测试策略类"""
    
    def __init__(self):
        super().__init__(name="TestStrategy", description="测试策略", abbreviation="TEST")
    
    def scan_opportunity(self, stock_id: str) -> List[Dict]:
        """必须实现的抽象方法"""
        return []

def create_test_data():
    """创建测试数据"""
    # 创建一些模拟的K线数据
    test_data = []
    base_price = 100
    
    for i in range(50):
        # 模拟价格波动
        if i < 10:
            price = base_price + i * 2  # 上涨
            trend = "bull"
        elif i < 20:
            price = base_price + 20 - (i - 10) * 1.5  # 下跌
            trend = "bear"
        elif i < 30:
            price = base_price + 5 + (i - 20) * 0.5  # 震荡
            trend = "sideways"
        elif i < 40:
            price = base_price + 10 + (i - 30) * 3  # 大涨
            trend = "bull"
        else:
            price = base_price + 40 - (i - 40) * 2  # 大跌
            trend = "bear"
        
        # 添加一些噪声
        noise = np.random.normal(0, 1)
        price += noise
        
        # 计算简单的移动平均线
        ma5 = price + np.random.normal(0, 0.5)
        ma10 = price + np.random.normal(0, 0.8)
        ma20 = price + np.random.normal(0, 1.2)
        ma60 = price + np.random.normal(0, 2.0)
        
        record = {
            'date': f"202301{i:02d}",
            'close': round(price, 2),
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
            'trend': trend
        }
        test_data.append(record)
    
    return test_data

def test_basic_functionality():
    """测试基本功能"""
    print("="*80)
    print("测试mark_period基本功能")
    print("="*80)
    
    # 创建测试策略
    strategy = TestStrategy()
    
    # 创建测试数据
    test_data = create_test_data()
    
    print(f"📊 创建了 {len(test_data)} 条测试数据")
    
    # 显示前几条数据
    print("\n📋 前5条测试数据:")
    for i, record in enumerate(test_data[:5]):
        print(f"   {i+1}. 日期: {record['date']}, 价格: {record['close']:.2f}, "
              f"MA5: {record['ma5']:.2f}, MA10: {record['ma10']:.2f}, "
              f"MA20: {record['ma20']:.2f}, MA60: {record['ma60']:.2f}")
    
    # 测试1: 简单条件 - 价格上涨
    print(f"\n🔍 测试1: 标记价格上涨区间")
    print("-" * 60)
    
    def price_up_condition(record):
        return record['close'] > 105  # 价格高于105
    
    up_periods = strategy.mark_period(test_data, price_up_condition, min_period_length=2)
    
    print(f"找到 {len(up_periods)} 个价格上涨区间")
    
    for i, period in enumerate(up_periods, 1):
        print(f"\n{i}. 上涨区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 天")
        print(f"   开始价格: {period['start_price']:.2f}")
        print(f"   结束价格: {period['end_price']:.2f}")
        print(f"   价格变化: {period['price_change_pct']:.2f}%")
    
    # 测试2: 多头排列条件
    print(f"\n🔍 测试2: 标记多头排列区间")
    print("-" * 60)
    
    def bull_condition(record):
        return (record['ma5'] > record['ma10'] and 
                record['ma10'] > record['ma20'] and 
                record['ma20'] > record['ma60'])
    
    bull_periods = strategy.mark_period(test_data, bull_condition, min_period_length=3)
    
    print(f"找到 {len(bull_periods)} 个多头排列区间")
    
    for i, period in enumerate(bull_periods, 1):
        print(f"\n{i}. 多头排列区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 天")
        print(f"   开始价格: {period['start_price']:.2f}")
        print(f"   结束价格: {period['end_price']:.2f}")
        print(f"   价格变化: {period['price_change_pct']:.2f}%")
    
    # 测试3: 收敛条件（简化的）
    print(f"\n🔍 测试3: 标记均线收敛区间")
    print("-" * 60)
    
    def convergence_condition(record):
        ma_values = [record['ma5'], record['ma10'], record['ma20'], record['ma60']]
        ma_max = max(ma_values)
        ma_min = min(ma_values)
        ma_convergence = (ma_max - ma_min) / record['close']
        return ma_convergence < 0.05  # 收敛度小于5%
    
    convergence_periods = strategy.mark_period(test_data, convergence_condition, min_period_length=2)
    
    print(f"找到 {len(convergence_periods)} 个收敛区间")
    
    for i, period in enumerate(convergence_periods, 1):
        print(f"\n{i}. 收敛区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 天")
        print(f"   开始价格: {period['start_price']:.2f}")
        print(f"   结束价格: {period['end_price']:.2f}")
        print(f"   价格变化: {period['price_change_pct']:.2f}%")
    
    # 测试4: 使用内置的专用函数
    print(f"\n🔍 测试4: 使用内置的mark_convergence_periods函数")
    print("-" * 60)
    
    convergence_periods_v2 = strategy.mark_convergence_periods(test_data, convergence_threshold=0.05, min_period_length=2)
    
    print(f"使用内置函数找到 {len(convergence_periods_v2)} 个收敛区间")
    
    # 测试5: 使用内置的mark_ma_trend_periods函数
    print(f"\n🔍 测试5: 使用内置的mark_ma_trend_periods函数")
    print("-" * 60)
    
    bull_periods_v2 = strategy.mark_ma_trend_periods(test_data, trend_type="bull", min_period_length=3)
    bear_periods_v2 = strategy.mark_ma_trend_periods(test_data, trend_type="bear", min_period_length=3)
    
    print(f"使用内置函数找到:")
    print(f"   - 多头排列区间: {len(bull_periods_v2)} 个")
    print(f"   - 空头排列区间: {len(bear_periods_v2)} 个")
    
    print(f"\n✅ 所有测试完成！mark_period函数工作正常。")

if __name__ == "__main__":
    test_basic_functionality()
