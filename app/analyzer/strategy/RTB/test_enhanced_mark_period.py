#!/usr/bin/env python3
"""
测试增强的mark_period函数功能
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
    test_data = []
    base_price = 100
    
    for i in range(30):
        # 模拟价格波动
        if i < 10:
            price = base_price + i * 2  # 上涨
        elif i < 20:
            price = base_price + 20 - (i - 10) * 1.5  # 下跌
        else:
            price = base_price + 5 + (i - 20) * 0.5  # 震荡
        
        # 添加一些噪声
        noise = np.random.normal(0, 1)
        price += noise
        
        # 计算简单的移动平均线
        ma5 = price + np.random.normal(0, 0.5)
        ma10 = price + np.random.normal(0, 0.8)
        ma20 = price + np.random.normal(0, 1.2)
        ma60 = price + np.random.normal(0, 2.0)
        
        # 模拟高低价
        high = price + abs(np.random.normal(0, 2))
        low = price - abs(np.random.normal(0, 2))
        
        record = {
            'date': f"202301{i:02d}",
            'open': round(price + np.random.normal(0, 0.5), 2),
            'close': round(price, 2),
            'highest': round(high, 2),
            'lowest': round(low, 2),
            'volume': int(1000000 + np.random.normal(0, 200000)),
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
        }
        test_data.append(record)
    
    return test_data

def test_enhanced_mark_period():
    """测试增强的mark_period功能"""
    print("="*80)
    print("测试增强的mark_period函数功能")
    print("="*80)
    
    # 创建测试策略
    strategy = TestStrategy()
    
    # 创建测试数据
    test_data = create_test_data()
    
    print(f"📊 创建了 {len(test_data)} 条测试数据")
    
    # 显示前几条数据
    print("\n📋 前5条测试数据:")
    for i, record in enumerate(test_data[:5]):
        print(f"   {i+1}. 日期: {record['date']}, 收盘价: {record['close']:.2f}, "
              f"最高: {record['highest']:.2f}, 最低: {record['lowest']:.2f}, "
              f"成交量: {record['volume']:,}")
    
    # 测试1: 标记价格上涨区间
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
        print(f"   索引范围: {period['start_idx']} - {period['end_idx']}")
        
        # 使用工具方法获取详细统计信息
        price_stats = strategy.get_price_statistics_from_period(period)
        if price_stats:
            print(f"   价格统计: 开始{price_stats['start_price']:.2f} -> 结束{price_stats['end_price']:.2f}, "
                  f"变化{price_stats['price_change_pct']:.2f}%")
            print(f"   价格区间: 最高{price_stats['max_price']:.2f}, 最低{price_stats['min_price']:.2f}")
        
        volume_stats = strategy.get_volume_statistics_from_period(period)
        if volume_stats:
            print(f"   成交量: 平均{volume_stats['avg_volume']:,.0f}, "
                  f"最大{volume_stats['max_volume']:,.0f}")
        
        extreme_prices = strategy.get_extreme_prices_from_period(period)
        if extreme_prices:
            print(f"   极值: 最高{extreme_prices['max_price']:.2f}({extreme_prices['max_price_date']}), "
                  f"最低{extreme_prices['min_price']:.2f}({extreme_prices['min_price_date']})")
    
    # 测试2: 多头排列区间
    print(f"\n🔍 测试2: 标记多头排列区间")
    print("-" * 60)
    
    bull_periods = strategy.mark_ma_trend_periods(test_data, trend_type="bull", min_period_length=3)
    
    print(f"找到 {len(bull_periods)} 个多头排列区间")
    
    for i, period in enumerate(bull_periods, 1):
        print(f"\n{i}. 多头排列区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 天")
        
        # 获取MA统计信息
        ma_stats = strategy.get_ma_statistics_from_period(period)
        if ma_stats:
            print(f"   开始MA: MA5={ma_stats['start_ma5']:.2f}, MA10={ma_stats['start_ma10']:.2f}, "
                  f"MA20={ma_stats['start_ma20']:.2f}, MA60={ma_stats['start_ma60']:.2f}")
            print(f"   结束MA: MA5={ma_stats['end_ma5']:.2f}, MA10={ma_stats['end_ma10']:.2f}, "
                  f"MA20={ma_stats['end_ma20']:.2f}, MA60={ma_stats['end_ma60']:.2f}")
    
    # 测试3: DataFrame格式
    print(f"\n🔍 测试3: DataFrame格式输出")
    print("-" * 60)
    
    try:
        import pandas as pd
        
        up_periods_df = strategy.mark_period(test_data, price_up_condition, min_period_length=2, return_format="dataframe")
        
        if not up_periods_df.empty:
            print(f"DataFrame格式成功，包含 {len(up_periods_df)} 行数据")
            print(f"列名: {list(up_periods_df.columns)}")
            print(f"\n前3行数据:")
            print(up_periods_df[['start_date', 'end_date', 'duration']].head(3).to_string())
        else:
            print("DataFrame为空")
            
    except ImportError:
        print("pandas未安装，跳过DataFrame测试")
    
    # 测试4: 整体分析
    print(f"\n🔍 测试4: 整体分析")
    print("-" * 60)
    
    if up_periods:
        analysis = strategy.analyze_periods(up_periods)
        print(f"区间分析结果:")
        print(f"   总区间数: {analysis['total_periods']}")
        print(f"   平均持续时间: {analysis['avg_duration']:.1f} 天")
        print(f"   平均价格变化: {analysis['avg_price_change']:.2f}%")
        print(f"   胜率: {analysis['win_rate']:.1%}")
        
        # 找出最佳区间
        best_periods = strategy.find_best_periods(up_periods, criteria="price_change_pct", top_n=2)
        print(f"\n最佳区间 (按价格变化排序):")
        for i, period in enumerate(best_periods, 1):
            price_stats = strategy.get_price_statistics_from_period(period)
            if price_stats:
                print(f"   {i}. {period['start_date']} - {period['end_date']}: "
                      f"{price_stats['price_change_pct']:.2f}%")
    
    print(f"\n✅ 增强的mark_period函数测试完成！")
    print(f"\n💡 使用建议:")
    print(f"   1. 使用mark_period()获取基础区间信息")
    print(f"   2. 根据需要调用工具方法获取详细统计:")
    print(f"      - get_price_statistics_from_period()")
    print(f"      - get_volume_statistics_from_period()")
    print(f"      - get_ma_statistics_from_period()")
    print(f"      - get_extreme_prices_from_period()")
    print(f"   3. 支持DataFrame格式输出，便于机器学习")

if __name__ == "__main__":
    test_enhanced_mark_period()
