#!/usr/bin/env python3
"""
分析524版本策略在A股不同市场周期（牛市、熊市、震荡市）下的表现
"""

import json
import os
import statistics
from collections import defaultdict
from datetime import datetime

def parse_date(date_str):
    """解析日期字符串"""
    if not date_str:
        return None
    
    formats = ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def get_market_cycle(year, month):
    """
    根据A股历史判断市场周期
    基于上证指数和深证成指的历史表现
    """
    # 定义市场周期
    if year == 2015:
        if month <= 6:
            return "牛市"  # 2015年上半年牛市
        else:
            return "熊市"  # 2015年下半年股灾
    
    elif year == 2016:
        if month <= 2:
            return "熊市"  # 熔断
        else:
            return "震荡市"  # 2016年震荡修复
    
    elif year == 2017:
        return "震荡市"  # 2017年结构性行情
    
    elif year == 2018:
        return "熊市"  # 2018年贸易战熊市
    
    elif year == 2019:
        if month <= 4:
            return "牛市"  # 2019年春季行情
        else:
            return "震荡市"  # 2019年震荡
    
    elif year == 2020:
        if month <= 3:
            return "熊市"  # 疫情初期
        elif month <= 7:
            return "牛市"  # 疫情后反弹
        else:
            return "震荡市"  # 2020年下半年震荡
    
    elif year == 2021:
        if month <= 2:
            return "牛市"  # 2021年春季行情
        else:
            return "震荡市"  # 2021年震荡
    
    elif year == 2022:
        return "熊市"  # 2022年熊市
    
    elif year == 2023:
        return "震荡市"  # 2023年震荡
    
    elif year == 2024:
        if month <= 2:
            return "熊市"  # 2024年初下跌
        elif month <= 5:
            return "牛市"  # 2024年春季行情
        else:
            return "震荡市"  # 2024年下半年震荡
    
    elif year == 2025:
        return "震荡市"  # 2025年预测震荡
    
    else:
        return "未知"

def analyze_market_cycles():
    session_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup"
    
    print("=" * 80)
    print("📈 524版本 HistoricLow 策略在不同市场周期下的表现分析")
    print("=" * 80)
    print()
    
    # 市场周期统计
    cycle_stats = {
        "牛市": defaultdict(lambda: {
            'investments': 0,
            'wins': 0,
            'losses': 0,
            'opens': 0,
            'total_profit': 0,
            'total_duration': 0,
            'profit_rates': []
        }),
        "熊市": defaultdict(lambda: {
            'investments': 0,
            'wins': 0,
            'losses': 0,
            'opens': 0,
            'total_profit': 0,
            'total_duration': 0,
            'profit_rates': []
        }),
        "震荡市": defaultdict(lambda: {
            'investments': 0,
            'wins': 0,
            'losses': 0,
            'opens': 0,
            'total_profit': 0,
            'total_duration': 0,
            'profit_rates': []
        })
    }
    
    # 分析文件
    json_files = [f for f in os.listdir(session_dir) if f.endswith('.json') and f != 'session_summary.json']
    
    print(f"📁 分析文件数量: {len(json_files)}")
    print(f"🔍 分析样本: 前 200 个股票文件")
    print()
    
    sample_size = min(200, len(json_files))
    total_investments = 0
    
    for i, filename in enumerate(json_files[:sample_size]):
        if filename == 'session_summary.json':
            continue
            
        file_path = os.path.join(session_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            investments = data['investments']
            
            for investment in investments:
                total_investments += 1
                
                start_date_str = investment.get('start_date', '')
                result = investment.get('result', '')
                profit = investment.get('overall_profit', 0)
                profit_rate = investment.get('overall_profit_rate', 0) * 100
                duration = investment.get('invest_duration_days', 0)
                
                # 解析开始日期
                start_date = parse_date(start_date_str)
                if start_date:
                    year = start_date.year
                    month = start_date.month
                    
                    # 判断市场周期
                    cycle = get_market_cycle(year, month)
                    
                    if cycle in cycle_stats:
                        # 统计该周期下的表现
                        cycle_stats[cycle][f"{year}年{month}月"]['investments'] += 1
                        cycle_stats[cycle][f"{year}年{month}月"]['total_profit'] += profit
                        cycle_stats[cycle][f"{year}年{month}月"]['total_duration'] += duration
                        cycle_stats[cycle][f"{year}年{month}月"]['profit_rates'].append(profit_rate)
                        
                        if result == 'win':
                            cycle_stats[cycle][f"{year}年{month}月"]['wins'] += 1
                        elif result == 'loss':
                            cycle_stats[cycle][f"{year}年{month}月"]['losses'] += 1
                        elif result == 'open':
                            cycle_stats[cycle][f"{year}年{month}月"]['opens'] += 1
        
        except Exception as e:
            print(f"❌ 读取文件 {filename} 失败: {e}")
            continue
    
    print(f"📊 总分析投资次数: {total_investments}")
    print()
    
    # 按市场周期汇总统计
    cycle_summary = {}
    
    for cycle_name, cycle_data in cycle_stats.items():
        total_inv = sum(stats['investments'] for stats in cycle_data.values())
        total_wins = sum(stats['wins'] for stats in cycle_data.values())
        total_losses = sum(stats['losses'] for stats in cycle_data.values())
        total_opens = sum(stats['opens'] for stats in cycle_data.values())
        total_profit = sum(stats['total_profit'] for stats in cycle_data.values())
        total_duration = sum(stats['total_duration'] for stats in cycle_data.values())
        
        all_profit_rates = []
        for stats in cycle_data.values():
            all_profit_rates.extend(stats['profit_rates'])
        
        if total_inv > 0:
            win_rate = (total_wins / total_inv) * 100
            avg_roi = statistics.mean(all_profit_rates) if all_profit_rates else 0
            avg_duration = total_duration / total_inv
            avg_profit = total_profit / total_inv
            
            cycle_summary[cycle_name] = {
                'investments': total_inv,
                'wins': total_wins,
                'losses': total_losses,
                'opens': total_opens,
                'win_rate': win_rate,
                'avg_roi': avg_roi,
                'avg_duration': avg_duration,
                'total_profit': total_profit,
                'avg_profit': avg_profit
            }
    
    # 显示市场周期表现对比
    print("📊 不同市场周期下的策略表现对比:")
    print("-" * 80)
    print(f"{'市场周期':<10} {'投资次数':<8} {'胜率':<8} {'平均ROI':<10} {'总收益':<10} {'平均收益':<10} {'平均时长':<10}")
    print("-" * 80)
    
    for cycle_name in ["牛市", "熊市", "震荡市"]:
        if cycle_name in cycle_summary:
            stats = cycle_summary[cycle_name]
            print(f"{cycle_name:<10} {stats['investments']:<8} {stats['win_rate']:<7.1f}% {stats['avg_roi']:<9.1f}% {stats['total_profit']:<9.1f} {stats['avg_profit']:<9.2f} {stats['avg_duration']:<9.1f}天")
    
    print()
    
    # 详细分析每个市场周期
    for cycle_name in ["牛市", "熊市", "震荡市"]:
        if cycle_name in cycle_stats and cycle_summary.get(cycle_name, {}).get('investments', 0) > 0:
            print(f"📈 {cycle_name}详细分析:")
            print("-" * 60)
            
            cycle_data = cycle_stats[cycle_name]
            summary = cycle_summary[cycle_name]
            
            print(f"总体表现:")
            print(f"  投资次数: {summary['investments']}")
            print(f"  胜率: {summary['win_rate']:.1f}%")
            print(f"  平均ROI: {summary['avg_roi']:.1f}%")
            print(f"  总收益: {summary['total_profit']:.1f}")
            print(f"  平均每笔收益: {summary['avg_profit']:.2f}")
            print(f"  平均投资时长: {summary['avg_duration']:.1f}天")
            print()
            
            # 显示该周期下的最佳表现月份
            best_months = []
            for month_key, stats in cycle_data.items():
                if stats['investments'] >= 3:  # 至少3次投资
                    win_rate = (stats['wins'] / stats['investments']) * 100
                    avg_roi = statistics.mean(stats['profit_rates']) if stats['profit_rates'] else 0
                    best_months.append((month_key, win_rate, avg_roi, stats['investments']))
            
            best_months.sort(key=lambda x: x[1], reverse=True)  # 按胜率排序
            
            if best_months:
                print(f"最佳表现月份 (至少3次投资):")
                for i, (month, win_rate, avg_roi, count) in enumerate(best_months[:5]):
                    print(f"  {i+1}. {month}: 胜率 {win_rate:.1f}%, 平均ROI {avg_roi:.1f}%, 投资 {count} 次")
            
            print()
    
    # 市场周期适应性分析
    print("🎯 市场周期适应性分析:")
    print("-" * 60)
    
    if len(cycle_summary) >= 2:
        # 找出最佳和最差表现的市场周期
        best_cycle = max(cycle_summary.items(), key=lambda x: x[1]['win_rate'])
        worst_cycle = min(cycle_summary.items(), key=lambda x: x[1]['win_rate'])
        
        print(f"最佳表现周期: {best_cycle[0]}")
        print(f"  胜率: {best_cycle[1]['win_rate']:.1f}%")
        print(f"  平均ROI: {best_cycle[1]['avg_roi']:.1f}%")
        print(f"  投资次数: {best_cycle[1]['investments']}")
        print()
        
        print(f"最差表现周期: {worst_cycle[0]}")
        print(f"  胜率: {worst_cycle[1]['win_rate']:.1f}%")
        print(f"  平均ROI: {worst_cycle[1]['avg_roi']:.1f}%")
        print(f"  投资次数: {worst_cycle[1]['investments']}")
        print()
        
        # 计算周期间的差异
        if best_cycle[0] != worst_cycle[0]:
            win_rate_diff = best_cycle[1]['win_rate'] - worst_cycle[1]['win_rate']
            roi_diff = best_cycle[1]['avg_roi'] - worst_cycle[1]['avg_roi']
            
            print(f"周期表现差异:")
            print(f"  胜率差异: {win_rate_diff:+.1f} 百分点")
            print(f"  平均ROI差异: {roi_diff:+.1f} 百分点")
            print()
    
    # 策略建议
    print("💡 策略建议:")
    print("-" * 60)
    
    for cycle_name, stats in cycle_summary.items():
        if stats['investments'] > 0:
            if stats['win_rate'] >= 70:
                recommendation = "✅ 表现优秀，适合加大投资"
            elif stats['win_rate'] >= 60:
                recommendation = "🟡 表现良好，可以正常投资"
            elif stats['win_rate'] >= 50:
                recommendation = "⚠️ 表现一般，需要谨慎投资"
            else:
                recommendation = "❌ 表现较差，建议减少投资"
            
            print(f"{cycle_name}: {recommendation}")
            print(f"  理由: 胜率 {stats['win_rate']:.1f}%, 平均ROI {stats['avg_roi']:.1f}%")
    
    print()
    print("=" * 80)
    print("✅ 市场周期分析完成")
    print("=" * 80)

if __name__ == "__main__":
    analyze_market_cycles()
