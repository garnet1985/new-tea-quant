#!/usr/bin/env python3
"""
分析524版本的盈利分布情况
"""

import json
import os
import statistics
from collections import defaultdict

def analyze_profit_distribution():
    # 读取session summary
    session_file = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup/session_summary.json"
    
    with open(session_file, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    print("=" * 60)
    print("📊 524版本 HistoricLow 策略盈利分布分析")
    print("=" * 60)
    
    # 基本统计信息
    print(f"📈 总体表现:")
    print(f"  总投资次数: {session_data['total_investments']:,}")
    print(f"  胜率: {session_data['win_rate']:.1f}%")
    print(f"  平均ROI: {session_data['avg_roi']:.1f}%")
    print(f"  年化收益率: {session_data['annual_return']:.1f}%")
    print(f"  平均投资时长: {session_data['avg_duration_days']:.1f} 天")
    print()
    
    # 结果分布
    print(f"🎯 结果分布:")
    print(f"  🟢 盈利 (≥20%): {session_data['green_dot_count']:,} ({session_data['green_dot_rate']:.1f}%)")
    print(f"  🟡 微盈 (<20%): {session_data['yellow_dot_count']:,} ({session_data['yellow_dot_rate']:.1f}%)")
    print(f"  🔴 亏损: {session_data['red_dot_count']:,} ({session_data['red_dot_rate']:.1f}%)")
    print()
    
    # 详细分析每只股票的投资记录
    session_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup"
    
    all_profits = []
    all_profit_rates = []
    all_durations = []
    
    win_profits = []
    loss_profits = []
    open_profits = []
    
    win_profit_rates = []
    loss_profit_rates = []
    open_profit_rates = []
    
    stock_performance = {}
    
    # 统计文件数量
    json_files = [f for f in os.listdir(session_dir) if f.endswith('.json') and f != 'session_summary.json']
    print(f"📁 分析文件数量: {len(json_files)}")
    print()
    
    # 分析前100个文件作为样本
    sample_size = min(100, len(json_files))
    print(f"🔍 分析样本: 前 {sample_size} 个股票文件")
    print()
    
    for i, filename in enumerate(json_files[:sample_size]):
        if filename == 'session_summary.json':
            continue
            
        file_path = os.path.join(session_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stock_id = data['stock_info']['id']
            stock_name = data['stock_info']['name']
            investments = data['investments']
            
            stock_win_count = 0
            stock_loss_count = 0
            stock_open_count = 0
            stock_total_profit = 0
            stock_profit_rates = []
            
            for investment in investments:
                result = investment.get('result', '')
                profit = investment.get('overall_profit', 0)
                profit_rate = investment.get('overall_profit_rate', 0) * 100
                duration = investment.get('invest_duration_days', 0)
                
                all_profits.append(profit)
                all_profit_rates.append(profit_rate)
                all_durations.append(duration)
                stock_profit_rates.append(profit_rate)
                stock_total_profit += profit
                
                if result == 'win':
                    stock_win_count += 1
                    win_profits.append(profit)
                    win_profit_rates.append(profit_rate)
                elif result == 'loss':
                    stock_loss_count += 1
                    loss_profits.append(profit)
                    loss_profit_rates.append(profit_rate)
                elif result == 'open':
                    stock_open_count += 1
                    open_profits.append(profit)
                    open_profit_rates.append(profit_rate)
            
            # 记录股票表现
            total_investments = len(investments)
            if total_investments > 0:
                win_rate = (stock_win_count / total_investments) * 100
                avg_profit_rate = statistics.mean(stock_profit_rates) if stock_profit_rates else 0
                
                stock_performance[stock_id] = {
                    'name': stock_name,
                    'total_investments': total_investments,
                    'win_count': stock_win_count,
                    'loss_count': stock_loss_count,
                    'open_count': stock_open_count,
                    'win_rate': win_rate,
                    'total_profit': stock_total_profit,
                    'avg_profit_rate': avg_profit_rate
                }
        
        except Exception as e:
            print(f"❌ 读取文件 {filename} 失败: {e}")
            continue
    
    # 盈利分布分析
    print("📊 盈利分布详细分析:")
    print()
    
    if win_profits:
        print(f"🟢 盈利投资 ({len(win_profits)} 次):")
        print(f"  平均盈利: {statistics.mean(win_profits):.2f}")
        print(f"  中位数盈利: {statistics.median(win_profits):.2f}")
        print(f"  最大盈利: {max(win_profits):.2f}")
        print(f"  最小盈利: {min(win_profits):.2f}")
        print(f"  平均收益率: {statistics.mean(win_profit_rates):.1f}%")
        print(f"  收益率中位数: {statistics.median(win_profit_rates):.1f}%")
        print()
    
    if loss_profits:
        print(f"🔴 亏损投资 ({len(loss_profits)} 次):")
        print(f"  平均亏损: {statistics.mean(loss_profits):.2f}")
        print(f"  中位数亏损: {statistics.median(loss_profits):.2f}")
        print(f"  最大亏损: {max(loss_profits):.2f}")
        print(f"  最小亏损: {min(loss_profits):.2f}")
        print(f"  平均亏损率: {statistics.mean(loss_profit_rates):.1f}%")
        print(f"  亏损率中位数: {statistics.median(loss_profit_rates):.1f}%")
        print()
    
    if open_profits:
        print(f"🟡 未结清投资 ({len(open_profits)} 次):")
        print(f"  平均未实现收益: {statistics.mean(open_profits):.2f}")
        print(f"  中位数未实现收益: {statistics.median(open_profits):.2f}")
        print(f"  最大未实现收益: {max(open_profits):.2f}")
        print(f"  最小未实现收益: {min(open_profits):.2f}")
        print(f"  平均未实现收益率: {statistics.mean(open_profit_rates):.1f}%")
        print(f"  未实现收益率中位数: {statistics.median(open_profit_rates):.1f}%")
        print()
    
    # 收益率区间分析
    print("📈 收益率区间分布:")
    ranges = [
        ("<-20%", -float('inf'), -20),
        ("-20% ~ -10%", -20, -10),
        ("-10% ~ 0%", -10, 0),
        ("0% ~ 10%", 0, 10),
        ("10% ~ 20%", 10, 20),
        ("20% ~ 30%", 20, 30),
        ("30% ~ 50%", 30, 50),
        (">50%", 50, float('inf'))
    ]
    
    for range_name, min_val, max_val in ranges:
        count = sum(1 for rate in all_profit_rates if min_val <= rate < max_val)
        percentage = (count / len(all_profit_rates)) * 100 if all_profit_rates else 0
        print(f"  {range_name:>12}: {count:>4} 次 ({percentage:>5.1f}%)")
    print()
    
    # 最佳表现股票
    print("🏆 最佳表现股票 (按胜率排序):")
    sorted_stocks = sorted(stock_performance.items(), 
                          key=lambda x: (x[1]['win_rate'], x[1]['avg_profit_rate']), 
                          reverse=True)
    
    for i, (stock_id, perf) in enumerate(sorted_stocks[:10]):
        print(f"  {i+1:2d}. {stock_id} ({perf['name']})")
        print(f"      投资次数: {perf['total_investments']}, 胜率: {perf['win_rate']:.1f}%, 平均收益率: {perf['avg_profit_rate']:.1f}%")
    print()
    
    # 最差表现股票
    print("📉 最差表现股票 (按胜率排序):")
    for i, (stock_id, perf) in enumerate(sorted_stocks[-10:]):
        print(f"  {i+1:2d}. {stock_id} ({perf['name']})")
        print(f"      投资次数: {perf['total_investments']}, 胜率: {perf['win_rate']:.1f}%, 平均收益率: {perf['avg_profit_rate']:.1f}%")
    print()
    
    # 投资时长分析
    print("⏱️ 投资时长分析:")
    print(f"  平均投资时长: {statistics.mean(all_durations):.1f} 天")
    print(f"  中位数投资时长: {statistics.median(all_durations):.1f} 天")
    print(f"  最长投资: {max(all_durations)} 天")
    print(f"  最短投资: {min(all_durations)} 天")
    
    # 时长区间分布
    duration_ranges = [
        ("<30天", 0, 30),
        ("30-60天", 30, 60),
        ("60-90天", 60, 90),
        ("90-180天", 90, 180),
        ("180-365天", 180, 365),
        (">365天", 365, float('inf'))
    ]
    
    print("\n  投资时长分布:")
    for range_name, min_val, max_val in duration_ranges:
        count = sum(1 for duration in all_durations if min_val <= duration < max_val)
        percentage = (count / len(all_durations)) * 100 if all_durations else 0
        print(f"    {range_name:>10}: {count:>4} 次 ({percentage:>5.1f}%)")
    
    print("\n" + "=" * 60)
    print("✅ 分析完成")
    print("=" * 60)

if __name__ == "__main__":
    analyze_profit_distribution()
