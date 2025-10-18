#!/usr/bin/env python3
"""
分析V11优化版策略的投资时长，制定更优的时间管理策略
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

def analyze_investment_duration():
    """分析投资时长分布，制定更优的时间管理策略"""
    
    print("📊 分析V11优化版策略投资时长分布")
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
    
    # 分析投资时长分布
    all_durations = []
    winning_durations = []
    losing_durations = []
    
    # 分析投资时长与收益的关系
    duration_roi_pairs = []
    
    for inv in investments:
        duration = inv.get('duration_in_days', 0)
        roi = inv.get('overall_profit_rate', 0)
        result = inv.get('result', '')
        
        all_durations.append(duration)
        duration_roi_pairs.append((duration, roi))
        
        # 分别分析胜利和失败案例的时长
        if result == 'win' and roi > 0:
            winning_durations.append(duration)
        else:
            losing_durations.append(duration)
    
    print(f"✅ 胜利案例: {len(winning_durations)}")
    print(f"❌ 失败案例: {len(losing_durations)}")
    
    # 转换为numpy数组
    all_durations = np.array(all_durations)
    winning_durations = np.array(winning_durations)
    losing_durations = np.array(losing_durations)
    
    print("\n📈 整体投资时长分析:")
    print(f"  平均时长: {np.mean(all_durations):.1f}天")
    print(f"  中位数时长: {np.median(all_durations):.1f}天")
    print(f"  最长时长: {np.max(all_durations):.0f}天")
    print(f"  最短时长: {np.min(all_durations):.0f}天")
    print(f"  标准差: {np.std(all_durations):.1f}天")
    
    print("\n🎯 胜利案例投资时长分析:")
    print(f"  平均时长: {np.mean(winning_durations):.1f}天")
    print(f"  中位数时长: {np.median(winning_durations):.1f}天")
    print(f"  最长时长: {np.max(winning_durations):.0f}天")
    print(f"  最短时长: {np.min(winning_durations):.0f}天")
    
    print("\n🔴 失败案例投资时长分析:")
    print(f"  平均时长: {np.mean(losing_durations):.1f}天")
    print(f"  中位数时长: {np.median(losing_durations):.1f}天")
    print(f"  最长时长: {np.max(losing_durations):.0f}天")
    print(f"  最短时长: {np.min(losing_durations):.0f}天")
    
    # 时长分布分析
    duration_bins = [0, 30, 60, 90, 120, 180, 240, 300, 365, 1000]
    duration_labels = ["30天以内", "30-60天", "60-90天", "90-120天", "120-180天", "180-240天", "240-300天", "300-365天", "365天以上"]
    
    print("\n📊 投资时长分布:")
    for i in range(len(duration_bins) - 1):
        lower = duration_bins[i]
        upper = duration_bins[i+1]
        if i == len(duration_bins) - 2:  # 最后一个区间
            count = np.sum(all_durations >= lower)
        else:
            count = np.sum((all_durations >= lower) & (all_durations < upper))
        percentage = (count / len(all_durations)) * 100
        print(f"  {duration_labels[i]}: {count}次 ({percentage:.1f}%)")
    
    # 分析不同时长区间的胜率
    print("\n🎯 不同时长区间的胜率分析:")
    for i in range(len(duration_bins) - 1):
        lower = duration_bins[i]
        upper = duration_bins[i+1]
        if i == len(duration_bins) - 2:  # 最后一个区间
            mask = all_durations >= lower
        else:
            mask = (all_durations >= lower) & (all_durations < upper)
        
        if np.sum(mask) > 0:
            # 计算该时长区间的胜率
            winning_in_interval = 0
            for j, inv in enumerate(investments):
                if mask[j]:
                    result = inv.get('result', '')
                    roi = inv.get('overall_profit_rate', 0)
                    if result == 'win' and roi > 0:
                        winning_in_interval += 1
            
            win_rate = (winning_in_interval / np.sum(mask)) * 100
            print(f"  {duration_labels[i]}: 胜率 {winning_in_interval}/{np.sum(mask)} ({win_rate:.1f}%)")
    
    # 分析时长与ROI的关系
    print("\n📊 投资时长与ROI关系分析:")
    duration_roi_df = pd.DataFrame(duration_roi_pairs, columns=['duration', 'roi'])
    
    # 按时长分组分析ROI
    duration_groups = [
        (0, 60, "60天以内"),
        (60, 120, "60-120天"),
        (120, 180, "120-180天"),
        (180, 240, "180-240天"),
        (240, 365, "240-365天"),
        (365, 1000, "365天以上")
    ]
    
    for lower, upper, label in duration_groups:
        if upper == 1000:
            mask = duration_roi_df['duration'] >= lower
        else:
            mask = (duration_roi_df['duration'] >= lower) & (duration_roi_df['duration'] < upper)
        
        if mask.sum() > 0:
            group_data = duration_roi_df[mask]
            avg_roi = group_data['roi'].mean() * 100
            median_roi = group_data['roi'].median() * 100
            print(f"  {label}: 平均ROI {avg_roi:.2f}%, 中位数ROI {median_roi:.2f}% ({mask.sum()}次)")
    
    # 分析不同时间止损点的效果
    print("\n🎯 不同时间止损点效果分析:")
    time_stop_levels = [60, 90, 120, 180, 240, 300, 365]
    for days in time_stop_levels:
        # 计算在该时间点会被强制止损的案例数
        stopped_count = np.sum(all_durations >= days)
        stopped_ratio = (stopped_count / len(all_durations)) * 100
        print(f"  {days}天时间止损: 会止损 {stopped_count}/{len(all_durations)} 次 ({stopped_ratio:.1f}%)")
    
    # 分析最优投资时长
    print("\n💡 最优投资时长分析:")
    
    # 计算不同时长区间的年化收益率
    optimal_duration_analysis = []
    for lower, upper, label in duration_groups:
        if upper == 1000:
            mask = duration_roi_df['duration'] >= lower
        else:
            mask = (duration_roi_df['duration'] >= lower) & (duration_roi_df['duration'] < upper)
        
        if mask.sum() > 0:
            group_data = duration_roi_df[mask]
            avg_duration = group_data['duration'].mean()
            avg_roi = group_data['roi'].mean()
            annualized_return = (1 + avg_roi) ** (365 / avg_duration) - 1 if avg_duration > 0 else 0
            
            optimal_duration_analysis.append({
                'label': label,
                'count': mask.sum(),
                'avg_duration': avg_duration,
                'avg_roi': avg_roi * 100,
                'annualized_return': annualized_return * 100
            })
    
    # 按年化收益率排序
    optimal_duration_analysis.sort(key=lambda x: x['annualized_return'], reverse=True)
    
    print("  按年化收益率排序:")
    for i, analysis in enumerate(optimal_duration_analysis[:5]):  # 显示前5名
        print(f"  {i+1}. {analysis['label']}: 年化收益 {analysis['annualized_return']:.1f}% (平均{analysis['avg_duration']:.0f}天, ROI{analysis['avg_roi']:.1f}%, {analysis['count']}次)")
    
    # 保存分析结果
    analysis_summary = {
        "total_investments": len(investments),
        "winning_investments": len(winning_durations),
        "losing_investments": len(losing_durations),
        "duration_stats": {
            "all": {
                "mean": float(np.mean(all_durations)),
                "median": float(np.median(all_durations)),
                "max": float(np.max(all_durations)),
                "min": float(np.min(all_durations)),
                "std": float(np.std(all_durations)),
            },
            "winning": {
                "mean": float(np.mean(winning_durations)),
                "median": float(np.median(winning_durations)),
                "max": float(np.max(winning_durations)),
                "min": float(np.min(winning_durations)),
            },
            "losing": {
                "mean": float(np.mean(losing_durations)),
                "median": float(np.median(losing_durations)),
                "max": float(np.max(losing_durations)),
                "min": float(np.min(losing_durations)),
            }
        },
        "duration_distribution": {
            label: int(np.sum((all_durations >= duration_bins[i]) & (all_durations < duration_bins[i+1])) if i < len(duration_bins) - 2 else np.sum(all_durations >= duration_bins[i]))
            for i, label in enumerate(duration_labels)
        },
        "optimal_duration_analysis": [
            {
                "label": item["label"],
                "count": int(item["count"]),
                "avg_duration": float(item["avg_duration"]),
                "avg_roi": float(item["avg_roi"]),
                "annualized_return": float(item["annualized_return"])
            }
            for item in optimal_duration_analysis
        ],
        "time_stop_impact": {
            f"{days}天": float((np.sum(all_durations >= days) / len(all_durations)) * 100)
            for days in time_stop_levels
        }
    }
    
    output_path = Path(__file__).parent / "v11_duration_analysis.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_summary, f, ensure_ascii=False, indent=4)
    print(f"\n💾 分析结果已保存到: {output_path}")
    
    print("\n💡 投资时长优化建议:")
    print("1. 时间止损策略:")
    print(f"   - 当前平均投资时长{np.mean(all_durations):.0f}天，建议设置180-240天时间止损")
    print("   - 避免资金长期占用，提高资金周转效率")
    print("2. 最优投资窗口:")
    if optimal_duration_analysis:
        best_duration = optimal_duration_analysis[0]
        print(f"   - 最佳时长区间: {best_duration['label']}")
        print(f"   - 年化收益率: {best_duration['annualized_return']:.1f}%")
    print("3. 风险控制:")
    print(f"   - 失败案例平均时长{np.mean(losing_durations):.0f}天，建议及时止损")
    print("   - 超过300天的投资需要特别关注，考虑强制退出")


if __name__ == "__main__":
    analyze_investment_duration()
