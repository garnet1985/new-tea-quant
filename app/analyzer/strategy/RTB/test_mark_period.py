#!/usr/bin/env python3
"""
测试mark_period函数的功能
"""
import sys
import os
from typing import List, Dict
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from app.analyzer.components.base_strategy import BaseStrategy
from app.data_loader import DataLoader
from utils.db.db_manager import DatabaseManager

class TestStrategy(BaseStrategy):
    """测试策略类"""
    
    def __init__(self):
        super().__init__(name="TestStrategy", description="测试策略", abbreviation="TEST")
    
    def scan_opportunity(self, stock_id: str) -> List[Dict]:
        """必须实现的抽象方法"""
        return []

def test_mark_period_functions():
    """测试mark_period相关函数"""
    print("="*80)
    print("测试mark_period函数功能")
    print("="*80)
    
    # 初始化测试策略
    strategy = TestStrategy()
    
    # 初始化数据加载器
    data_loader = DataLoader()
    
    # 测试股票
    test_stock = "000001.SZ"
    
    print(f"📈 测试股票: {test_stock}")
    
    # 获取周线数据
    weekly_data = data_loader.load_klines(test_stock, term='weekly', adjust='qfq')
    
    if not weekly_data:
        print("❌ 无法获取数据")
        return
    
    print(f"📊 获取到 {len(weekly_data)} 条周线数据")
    
    # 测试1: 标记均线收敛区间
    print(f"\n🔍 测试1: 标记均线收敛区间")
    print("-" * 60)
    
    convergence_periods = strategy.mark_convergence_periods(weekly_data, convergence_threshold=0.08, min_period_length=3)
    
    print(f"找到 {len(convergence_periods)} 个收敛区间")
    
    for i, period in enumerate(convergence_periods[:5], 1):  # 显示前5个
        print(f"\n{i}. 收敛区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 周")
        print(f"   开始价格: {period['start_price']:.2f}")
        print(f"   结束价格: {period['end_price']:.2f}")
        print(f"   价格变化: {period['price_change_pct']:.2f}%")
    
    # 测试2: 标记多头排列区间
    print(f"\n🔍 测试2: 标记多头排列区间")
    print("-" * 60)
    
    bull_periods = strategy.mark_ma_trend_periods(weekly_data, trend_type="bull", min_period_length=5)
    
    print(f"找到 {len(bull_periods)} 个多头排列区间")
    
    for i, period in enumerate(bull_periods[:3], 1):  # 显示前3个
        print(f"\n{i}. 多头排列区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 周")
        print(f"   开始价格: {period['start_price']:.2f}")
        print(f"   结束价格: {period['end_price']:.2f}")
        print(f"   价格变化: {period['price_change_pct']:.2f}%")
    
    # 测试3: 标记空头排列区间
    print(f"\n🔍 测试3: 标记空头排列区间")
    print("-" * 60)
    
    bear_periods = strategy.mark_ma_trend_periods(weekly_data, trend_type="bear", min_period_length=5)
    
    print(f"找到 {len(bear_periods)} 个空头排列区间")
    
    for i, period in enumerate(bear_periods[:3], 1):  # 显示前3个
        print(f"\n{i}. 空头排列区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 周")
        print(f"   开始价格: {period['start_price']:.2f}")
        print(f"   结束价格: {period['end_price']:.2f}")
        print(f"   价格变化: {period['price_change_pct']:.2f}%")
    
    # 测试4: 自定义条件函数
    print(f"\n🔍 测试4: 自定义条件函数 - 价格突破MA20")
    print("-" * 60)
    
    def price_above_ma20_condition(record):
        close = record.get('close', 0)
        ma20 = record.get('ma20', 0)
        return close > ma20 and ma20 > 0
    
    breakout_periods = strategy.mark_period(weekly_data, price_above_ma20_condition, min_period_length=3)
    
    print(f"找到 {len(breakout_periods)} 个价格突破MA20区间")
    
    for i, period in enumerate(breakout_periods[:3], 1):  # 显示前3个
        print(f"\n{i}. 突破区间:")
        print(f"   开始日期: {period['start_date']}")
        print(f"   结束日期: {period['end_date']}")
        print(f"   持续时间: {period['duration']} 周")
        print(f"   开始价格: {period['start_price']:.2f}")
        print(f"   结束价格: {period['end_price']:.2f}")
        print(f"   价格变化: {period['price_change_pct']:.2f}%")
    
    # 统计信息
    print(f"\n📊 统计信息:")
    print("-" * 60)
    print(f"收敛区间总数: {len(convergence_periods)}")
    print(f"多头排列区间总数: {len(bull_periods)}")
    print(f"空头排列区间总数: {len(bear_periods)}")
    print(f"价格突破MA20区间总数: {len(breakout_periods)}")
    
    # 分析收敛区间的表现
    if convergence_periods:
        print(f"\n📈 收敛区间表现分析:")
        positive_changes = [p for p in convergence_periods if p['price_change_pct'] > 0]
        negative_changes = [p for p in convergence_periods if p['price_change_pct'] < 0]
        
        print(f"   上涨区间: {len(positive_changes)} 个")
        print(f"   下跌区间: {len(negative_changes)} 个")
        
        if positive_changes:
            avg_positive = sum(p['price_change_pct'] for p in positive_changes) / len(positive_changes)
            print(f"   平均上涨幅度: {avg_positive:.2f}%")
        
        if negative_changes:
            avg_negative = sum(p['price_change_pct'] for p in negative_changes) / len(negative_changes)
            print(f"   平均下跌幅度: {avg_negative:.2f}%")

def test_mark_period_with_rtb_strategy():
    """使用RTB策略测试mark_period函数"""
    print(f"\n" + "="*80)
    print("使用RTB策略测试mark_period函数")
    print("="*80)
    
    # 这里可以导入RTB策略进行更具体的测试
    # from app.analyzer.strategy.RTB.RTB import RTB
    # rtb_strategy = RTB()
    # 然后使用RTB策略的特定条件进行测试
    
    print("✅ mark_period函数测试完成！")

if __name__ == "__main__":
    test_mark_period_functions()
    test_mark_period_with_rtb_strategy()
