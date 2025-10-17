#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析V11优化版策略的胜利案例分布，制定更好的止盈计划
"""

import sys
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

def analyze_v11_profit_distribution():
    """分析V11优化版策略的胜利案例分布"""
    
    print("📊 分析V11优化版策略胜利案例分布")
    print("="*60)
    
    # 查找最新的策略结果 - 使用187结果
    tmp_dir = Path("/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp")
    latest_dir = tmp_dir / "2025_10_17-187"  # 直接使用200股票结果
    
    if not latest_dir.exists():
        print("❌ 未找到策略结果")
        return
    
    print(f"📁 分析目录: {latest_dir.name}")
    
    # 收集所有投资数据
    investments = []
    
    for json_file in latest_dir.glob("*.json"):
        if json_file.name == "session_summary.json":
            continue
            
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if 'investments' in data:
            for investment in data['investments']:
                investments.append(investment)
    
    if not investments:
        print("❌ 未找到投资数据")
        return
    
    print(f"📊 总投资案例: {len(investments)}")
    
    # 分析胜利案例
    winning_investments = [inv for inv in investments if inv.get('overall_profit_rate', 0) > 0]
    losing_investments = [inv for inv in investments if inv.get('overall_profit_rate', 0) <= 0]
    
    print(f"✅ 胜利案例: {len(winning_investments)}")
    print(f"❌ 失败案例: {len(losing_investments)}")
    
    if not winning_investments:
        print("❌ 没有胜利案例可分析")
        return
    
    # 分析胜利案例的利润分布
    profits = [inv['overall_profit_rate'] for inv in winning_investments]
    
    print(f"\n📈 胜利案例利润分布:")
    print(f"  最小利润: {min(profits):.2%}")
    print(f"  最大利润: {max(profits):.2%}")
    print(f"  平均利润: {np.mean(profits):.2%}")
    print(f"  中位数利润: {np.median(profits):.2%}")
    print(f"  标准差: {np.std(profits):.2%}")
    
    # 利润区间分布
    print(f"\n📊 利润区间分布:")
    ranges = [
        (0.0, 0.05, "5%以下"),
        (0.05, 0.10, "5%-10%"),
        (0.10, 0.15, "10%-15%"),
        (0.15, 0.20, "15%-20%"),
        (0.20, 0.30, "20%-30%"),
        (0.30, 1.0, "30%以上")
    ]
    
    for min_p, max_p, label in ranges:
        count = len([p for p in profits if min_p <= p < max_p])
        percentage = count / len(profits) * 100
        print(f"  {label}: {count}次 ({percentage:.1f}%)")
    
    # 分析最大利润分布（用于止盈策略优化）
    max_profits = []
    for inv in winning_investments:
        if 'tracking' in inv and 'max_close_reached' in inv['tracking']:
            max_profit = inv['tracking']['max_close_reached'].get('ratio', 0)
            max_profits.append(max_profit)
    
    if max_profits:
        print(f"\n🎯 最大利润分布 (用于止盈策略优化):")
        print(f"  平均最大利润: {np.mean(max_profits):.2%}")
        print(f"  中位数最大利润: {np.median(max_profits):.2%}")
        
        # 分析不同止盈点的捕获率
        take_profit_points = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
        
        print(f"\n📊 不同止盈点的捕获率:")
        for tp_point in take_profit_points:
            captured = len([mp for mp in max_profits if mp >= tp_point])
            capture_rate = captured / len(max_profits) * 100
            print(f"  {tp_point:.0%}止盈点: 可捕获 {captured}/{len(max_profits)} 次 ({capture_rate:.1f}%)")
    
    # 分析投资时长分布
    durations = []
    for inv in investments:
        if 'entry_date' in inv and 'exit_date' in inv:
            # 简化处理，假设有duration字段
            duration = inv.get('duration_days', 0)
            if duration > 0:
                durations.append(duration)
    
    if durations:
        print(f"\n⏰ 投资时长分布:")
        print(f"  平均时长: {np.mean(durations):.1f} 天")
        print(f"  中位数时长: {np.median(durations):.1f} 天")
        print(f"  最短时长: {min(durations):.1f} 天")
        print(f"  最长时长: {max(durations):.1f} 天")
        
        # 时长区间分布
        print(f"\n📊 时长区间分布:")
        duration_ranges = [
            (0, 30, "1个月内"),
            (30, 60, "1-2个月"),
            (60, 120, "2-4个月"),
            (120, 180, "4-6个月"),
            (180, 365, "6-12个月"),
            (365, 1000, "12个月以上")
        ]
        
        for min_d, max_d, label in duration_ranges:
            count = len([d for d in durations if min_d <= d < max_d])
            percentage = count / len(durations) * 100
            print(f"  {label}: {count}次 ({percentage:.1f}%)")
    
    # 保存分析结果
    analysis_result = {
        'total_investments': len(investments),
        'winning_investments': len(winning_investments),
        'losing_investments': len(losing_investments),
        'win_rate': len(winning_investments) / len(investments),
        'profit_stats': {
            'min': min(profits),
            'max': max(profits),
            'mean': np.mean(profits),
            'median': np.median(profits),
            'std': np.std(profits)
        },
        'max_profit_stats': {
            'mean': np.mean(max_profits) if max_profits else 0,
            'median': np.median(max_profits) if max_profits else 0
        },
        'duration_stats': {
            'mean': np.mean(durations) if durations else 0,
            'median': np.median(durations) if durations else 0,
            'min': min(durations) if durations else 0,
            'max': max(durations) if durations else 0
        }
    }
    
    # 保存到文件
    output_file = Path("/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/v11_profit_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 分析结果已保存到: {output_file}")
    
    # 生成优化建议
    print(f"\n💡 优化建议:")
    
    if max_profits:
        # 基于最大利润分布建议止盈策略
        median_max = np.median(max_profits)
        mean_max = np.mean(max_profits)
        
        print(f"1. 止盈策略优化:")
        print(f"   - 平均最大利润: {mean_max:.2%}, 中位数最大利润: {median_max:.2%}")
        print(f"   - 建议设置分阶段止盈: 10%, 20%, 30%")
        print(f"   - 考虑动态止盈: 当利润达到{median_max:.0%}时开始部分止盈")
    
    if durations:
        # 基于投资时长建议
        median_duration = np.median(durations)
        print(f"2. 投资时长优化:")
        print(f"   - 中位数投资时长: {median_duration:.0f} 天")
        print(f"   - 建议设置最大持有期: {int(median_duration * 1.5)} 天")
        print(f"   - 考虑分阶段减仓策略以缩短持有期")
    
    return analysis_result

if __name__ == "__main__":
    analyze_v11_profit_distribution()
