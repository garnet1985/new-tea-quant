#!/usr/bin/env python3
"""
分析V11优化版策略的最大最小点，制定更好的止损策略
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

def analyze_max_min_points():
    """分析每次投资的最大最小点，制定更好的止损策略"""
    
    print("📊 分析V11优化版策略最大最小点分布")
    print("="*60)
    
    # 使用最新的200股票结果 - 187版本
    tmp_dir = Path("/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp")
    latest_dir = tmp_dir / "2025_10_17-187"  # 使用最新的200股票结果
    
    if not latest_dir.exists():
        print("❌ 未找到策略结果")
        return
    
    print(f"📁 分析目录: {latest_dir.name}")
    
    # 收集所有投资数据
    investments = []
    for file_path in latest_dir.glob("*.json"):
        if file_path.name == "meta.json" or file_path.name == "0_session_summary.json":
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            investments.extend(data.get('investments', []))
    
    if not investments:
        print("❌ 未找到任何投资记录。")
        return

    print(f"📊 总投资案例: {len(investments)}")
    
    # 分析所有投资的最大回撤和最大涨幅
    all_max_drawdowns = []
    all_max_gains = []
    winning_max_gains = []
    losing_max_drawdowns = []
    
    for inv in investments:
        tracking = inv.get('tracking', {})
        
        # 最大回撤 (从tracking中的min_close_reached获取)
        min_close = tracking.get('min_close_reached', {})
        max_drawdown = min_close.get('ratio', 0)  # 已经是负值
        all_max_drawdowns.append(abs(max_drawdown))  # 转为正值便于分析
        
        # 最大涨幅 (从tracking中的max_close_reached获取)
        max_close = tracking.get('max_close_reached', {})
        max_gain = max_close.get('ratio', 0)
        all_max_gains.append(max_gain)
        
        # 分别分析胜利和失败案例
        # 基于result字段和overall_profit_rate判断
        if inv.get('result') == 'win' and inv.get('overall_profit_rate', 0) > 0:
            winning_max_gains.append(max_gain)
        else:
            losing_max_drawdowns.append(abs(max_drawdown))
    
    print(f"✅ 胜利案例: {len(winning_max_gains)}")
    print(f"❌ 失败案例: {len(losing_max_drawdowns)}")
    
    # 转换为numpy数组
    all_max_drawdowns = np.array(all_max_drawdowns) * 100  # 转为百分比
    all_max_gains = np.array(all_max_gains) * 100
    winning_max_gains = np.array(winning_max_gains) * 100
    losing_max_drawdowns = np.array(losing_max_drawdowns) * 100
    
    print("\n📈 整体最大回撤分析:")
    print(f"  平均最大回撤: {np.mean(all_max_drawdowns):.2f}%")
    print(f"  中位数最大回撤: {np.median(all_max_drawdowns):.2f}%")
    print(f"  最大回撤: {np.max(all_max_drawdowns):.2f}%")
    print(f"  最小回撤: {np.min(all_max_drawdowns):.2f}%")
    print(f"  标准差: {np.std(all_max_drawdowns):.2f}%")
    
    print("\n📈 整体最大涨幅分析:")
    print(f"  平均最大涨幅: {np.mean(all_max_gains):.2f}%")
    print(f"  中位数最大涨幅: {np.median(all_max_gains):.2f}%")
    print(f"  最大涨幅: {np.max(all_max_gains):.2f}%")
    print(f"  最小涨幅: {np.min(all_max_gains):.2f}%")
    print(f"  标准差: {np.std(all_max_gains):.2f}%")
    
    print("\n🎯 胜利案例最大涨幅分析:")
    print(f"  平均最大涨幅: {np.mean(winning_max_gains):.2f}%")
    print(f"  中位数最大涨幅: {np.median(winning_max_gains):.2f}%")
    print(f"  最大涨幅: {np.max(winning_max_gains):.2f}%")
    print(f"  最小涨幅: {np.min(winning_max_gains):.2f}%")
    
    print("\n🔴 失败案例最大回撤分析:")
    print(f"  平均最大回撤: {np.mean(losing_max_drawdowns):.2f}%")
    print(f"  中位数最大回撤: {np.median(losing_max_drawdowns):.2f}%")
    print(f"  最大回撤: {np.max(losing_max_drawdowns):.2f}%")
    print(f"  最小回撤: {np.min(losing_max_drawdowns):.2f}%")
    
    # 回撤分布分析
    drawdown_bins = [0, 5, 10, 15, 20, 25, 30, 1000]
    drawdown_labels = ["5%以下", "5%-10%", "10%-15%", "15%-20%", "20%-25%", "25%-30%", "30%以上"]
    
    print("\n📊 最大回撤分布:")
    for i in range(len(drawdown_bins) - 1):
        lower = drawdown_bins[i]
        upper = drawdown_bins[i+1]
        if i == len(drawdown_bins) - 2:  # 最后一个区间
            count = np.sum(all_max_drawdowns >= lower)
        else:
            count = np.sum((all_max_drawdowns >= lower) & (all_max_drawdowns < upper))
        percentage = (count / len(all_max_drawdowns)) * 100
        print(f"  {drawdown_labels[i]}: {count}次 ({percentage:.1f}%)")
    
    # 涨幅分布分析
    gain_bins = [0, 10, 20, 30, 40, 50, 100, 1000]
    gain_labels = ["10%以下", "10%-20%", "20%-30%", "30%-40%", "40%-50%", "50%-100%", "100%以上"]
    
    print("\n📊 最大涨幅分布:")
    for i in range(len(gain_bins) - 1):
        lower = gain_bins[i]
        upper = gain_bins[i+1]
        if i == len(gain_bins) - 2:  # 最后一个区间
            count = np.sum(all_max_gains >= lower)
        else:
            count = np.sum((all_max_gains >= lower) & (all_max_gains < upper))
        percentage = (count / len(all_max_gains)) * 100
        print(f"  {gain_labels[i]}: {count}次 ({percentage:.1f}%)")
    
    # 分析不同止损点的效果
    print("\n🎯 不同止损点效果分析:")
    stop_loss_levels = [10, 15, 20, 25, 30]
    for level in stop_loss_levels:
        # 计算在该止损点会被止损的案例数
        stopped_count = np.sum(all_max_drawdowns >= level)
        stopped_ratio = (stopped_count / len(all_max_drawdowns)) * 100
        print(f"  {level}%止损: 会止损 {stopped_count}/{len(all_max_drawdowns)} 次 ({stopped_ratio:.1f}%)")
    
    # 分析不同止盈点的效果
    print("\n🎯 不同止盈点效果分析:")
    take_profit_levels = [10, 15, 20, 25, 30, 40, 50]
    for level in take_profit_levels:
        # 计算在该止盈点会被止盈的案例数
        taken_count = np.sum(all_max_gains >= level)
        taken_ratio = (taken_count / len(all_max_gains)) * 100
        print(f"  {level}%止盈: 会止盈 {taken_count}/{len(all_max_gains)} 次 ({taken_ratio:.1f}%)")
    
    # 保存分析结果
    analysis_summary = {
        "total_investments": len(investments),
        "winning_investments": len(winning_max_gains),
        "losing_investments": len(losing_max_drawdowns),
        "max_drawdown_stats": {
            "mean": float(np.mean(all_max_drawdowns)),
            "median": float(np.median(all_max_drawdowns)),
            "max": float(np.max(all_max_drawdowns)),
            "min": float(np.min(all_max_drawdowns)),
            "std": float(np.std(all_max_drawdowns)),
        },
        "max_gain_stats": {
            "mean": float(np.mean(all_max_gains)),
            "median": float(np.median(all_max_gains)),
            "max": float(np.max(all_max_gains)),
            "min": float(np.min(all_max_gains)),
            "std": float(np.std(all_max_gains)),
        },
        "winning_max_gain_stats": {
            "mean": float(np.mean(winning_max_gains)),
            "median": float(np.median(winning_max_gains)),
            "max": float(np.max(winning_max_gains)),
            "min": float(np.min(winning_max_gains)),
        },
        "losing_max_drawdown_stats": {
            "mean": float(np.mean(losing_max_drawdowns)),
            "median": float(np.median(losing_max_drawdowns)),
            "max": float(np.max(losing_max_drawdowns)),
            "min": float(np.min(losing_max_drawdowns)),
        },
        "drawdown_distribution": {
            label: int(np.sum((all_max_drawdowns >= drawdown_bins[i]) & (all_max_drawdowns < drawdown_bins[i+1])) if i < len(drawdown_bins) - 2 else np.sum(all_max_drawdowns >= drawdown_bins[i]))
            for i, label in enumerate(drawdown_labels)
        },
        "gain_distribution": {
            label: int(np.sum((all_max_gains >= gain_bins[i]) & (all_max_gains < gain_bins[i+1])) if i < len(gain_bins) - 2 else np.sum(all_max_gains >= gain_bins[i]))
            for i, label in enumerate(gain_labels)
        },
        "stop_loss_impact": {
            f"{level}%": float((np.sum(all_max_drawdowns >= level) / len(all_max_drawdowns)) * 100)
            for level in stop_loss_levels
        },
        "take_profit_impact": {
            f"{level}%": float((np.sum(all_max_gains >= level) / len(all_max_gains)) * 100)
            for level in take_profit_levels
        }
    }
    
    output_path = Path(__file__).parent / "v11_max_min_analysis.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_summary, f, ensure_ascii=False, indent=4)
    print(f"\n💾 分析结果已保存到: {output_path}")
    
    print("\n💡 止损止盈优化建议:")
    print("1. 止损策略优化:")
    print(f"   - 当前20%止损可能过于宽松，{np.mean(all_max_drawdowns):.1f}%的平均最大回撤")
    print(f"   - 建议考虑15%或18%止损，平衡保护资金与避免误杀")
    print("2. 止盈策略优化:")
    print(f"   - 平均最大涨幅{np.mean(all_max_gains):.1f}%，中位数{np.median(all_max_gains):.1f}%")
    print("   - 建议设置分阶段止盈: 15%, 25%, 35%")
    print("   - 考虑动态止盈: 达到20%后开始部分止盈")
    print("3. 风险控制:")
    print(f"   - 最大回撤达到{np.max(all_max_drawdowns):.1f}%，需要严格止损")
    print("   - 建议结合技术指标设置动态止损")


if __name__ == "__main__":
    analyze_max_min_points()
