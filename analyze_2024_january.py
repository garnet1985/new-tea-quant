#!/usr/bin/env python3
"""
专门分析2024年1月的投资情况
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

def analyze_2024_january():
    session_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup"
    
    print("=" * 80)
    print("📅 2024年1月 HistoricLow 策略投资情况详细分析")
    print("=" * 80)
    print()
    
    # 2024年1月投资统计
    january_2024_investments = []
    january_2024_stats = {
        'total_investments': 0,
        'wins': 0,
        'losses': 0,
        'opens': 0,
        'total_profit': 0,
        'total_duration': 0,
        'profit_rates': [],
        'durations': [],
        'stocks': set(),
        'start_dates': [],
        'end_dates': []
    }
    
    # 分析文件
    json_files = [f for f in os.listdir(session_dir) if f.endswith('.json') and f != 'session_summary.json']
    
    print(f"📁 分析文件数量: {len(json_files)}")
    print(f"🔍 分析样本: 前 200 个股票文件")
    print()
    
    sample_size = min(200, len(json_files))
    
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
            
            for investment in investments:
                start_date_str = investment.get('start_date', '')
                end_date_str = investment.get('end_date', '')
                result = investment.get('result', '')
                profit = investment.get('overall_profit', 0)
                profit_rate = investment.get('overall_profit_rate', 0) * 100
                duration = investment.get('invest_duration_days', 0)
                
                # 解析开始日期
                start_date = parse_date(start_date_str)
                if start_date and start_date.year == 2024 and start_date.month == 1:
                    # 这是2024年1月的投资
                    january_2024_investments.append({
                        'stock_id': stock_id,
                        'stock_name': stock_name,
                        'start_date': start_date_str,
                        'end_date': end_date_str,
                        'result': result,
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'duration': duration,
                        'investment': investment
                    })
                    
                    # 统计
                    january_2024_stats['total_investments'] += 1
                    january_2024_stats['total_profit'] += profit
                    january_2024_stats['total_duration'] += duration
                    january_2024_stats['profit_rates'].append(profit_rate)
                    january_2024_stats['durations'].append(duration)
                    january_2024_stats['stocks'].add(stock_id)
                    january_2024_stats['start_dates'].append(start_date_str)
                    if end_date_str:
                        january_2024_stats['end_dates'].append(end_date_str)
                    
                    if result == 'win':
                        january_2024_stats['wins'] += 1
                    elif result == 'loss':
                        january_2024_stats['losses'] += 1
                    elif result == 'open':
                        january_2024_stats['opens'] += 1
        
        except Exception as e:
            print(f"❌ 读取文件 {filename} 失败: {e}")
            continue
    
    print(f"📊 2024年1月投资统计:")
    print(f"  总投资次数: {january_2024_stats['total_investments']}")
    print(f"  涉及股票数: {len(january_2024_stats['stocks'])}")
    print()
    
    if january_2024_stats['total_investments'] == 0:
        print("❌ 2024年1月没有找到投资记录")
        return
    
    # 基本统计
    win_rate = (january_2024_stats['wins'] / january_2024_stats['total_investments']) * 100
    avg_roi = statistics.mean(january_2024_stats['profit_rates']) if january_2024_stats['profit_rates'] else 0
    median_roi = statistics.median(january_2024_stats['profit_rates']) if january_2024_stats['profit_rates'] else 0
    avg_duration = statistics.mean(january_2024_stats['durations']) if january_2024_stats['durations'] else 0
    avg_profit = january_2024_stats['total_profit'] / january_2024_stats['total_investments']
    
    print("📈 2024年1月投资表现:")
    print("-" * 60)
    print(f"  总投资次数: {january_2024_stats['total_investments']}")
    print(f"  成功次数: {january_2024_stats['wins']}")
    print(f"  失败次数: {january_2024_stats['losses']}")
    print(f"  未结清次数: {january_2024_stats['opens']}")
    print(f"  胜率: {win_rate:.1f}%")
    print(f"  平均ROI: {avg_roi:.1f}%")
    print(f"  中位数ROI: {median_roi:.1f}%")
    print(f"  总收益: {january_2024_stats['total_profit']:.2f}")
    print(f"  平均每笔收益: {avg_profit:.2f}")
    print(f"  平均投资时长: {avg_duration:.1f}天")
    print()
    
    # 按结果分类显示投资详情
    print("📋 2024年1月投资详情:")
    print("-" * 80)
    
    # 按结果分组
    wins = [inv for inv in january_2024_investments if inv['result'] == 'win']
    losses = [inv for inv in january_2024_investments if inv['result'] == 'loss']
    opens = [inv for inv in january_2024_investments if inv['result'] == 'open']
    
    print(f"🟢 成功投资 ({len(wins)} 次):")
    if wins:
        # 按收益率排序
        wins.sort(key=lambda x: x['profit_rate'], reverse=True)
        for i, inv in enumerate(wins[:10]):  # 显示前10个
            print(f"  {i+1:2d}. {inv['stock_id']} ({inv['stock_name']})")
            print(f"      开始: {inv['start_date']}, 结束: {inv['end_date']}")
            print(f"      收益率: {inv['profit_rate']:+.1f}%, 收益: {inv['profit']:+.2f}, 时长: {inv['duration']}天")
        if len(wins) > 10:
            print(f"      ... 还有 {len(wins) - 10} 个成功投资")
    print()
    
    print(f"🔴 失败投资 ({len(losses)} 次):")
    if losses:
        # 按亏损率排序（从大到小）
        losses.sort(key=lambda x: x['profit_rate'])
        for i, inv in enumerate(losses[:10]):  # 显示前10个
            print(f"  {i+1:2d}. {inv['stock_id']} ({inv['stock_name']})")
            print(f"      开始: {inv['start_date']}, 结束: {inv['end_date']}")
            print(f"      收益率: {inv['profit_rate']:+.1f}%, 收益: {inv['profit']:+.2f}, 时长: {inv['duration']}天")
        if len(losses) > 10:
            print(f"      ... 还有 {len(losses) - 10} 个失败投资")
    print()
    
    print(f"🟡 未结清投资 ({len(opens)} 次):")
    if opens:
        # 按收益率排序
        opens.sort(key=lambda x: x['profit_rate'], reverse=True)
        for i, inv in enumerate(opens):
            print(f"  {i+1:2d}. {inv['stock_id']} ({inv['stock_name']})")
            print(f"      开始: {inv['start_date']}, 结束: {inv['end_date']}")
            print(f"      收益率: {inv['profit_rate']:+.1f}%, 收益: {inv['profit']:+.2f}, 时长: {inv['duration']}天")
    print()
    
    # 股票分布分析
    print("📊 股票分布分析:")
    print("-" * 60)
    
    stock_counts = defaultdict(int)
    stock_profits = defaultdict(list)
    
    for inv in january_2024_investments:
        stock_counts[inv['stock_id']] += 1
        stock_profits[inv['stock_id']].append(inv['profit_rate'])
    
    print("投资次数最多的股票:")
    sorted_stocks = sorted(stock_counts.items(), key=lambda x: x[1], reverse=True)
    for i, (stock_id, count) in enumerate(sorted_stocks[:10]):
        avg_profit_rate = statistics.mean(stock_profits[stock_id])
        print(f"  {i+1:2d}. {stock_id}: {count} 次, 平均收益率: {avg_profit_rate:+.1f}%")
    print()
    
    # 日期分布分析
    print("📅 投资日期分布:")
    print("-" * 60)
    
    date_counts = defaultdict(int)
    for start_date in january_2024_stats['start_dates']:
        if start_date:
            date_counts[start_date] += 1
    
    print("投资开始日期分布:")
    sorted_dates = sorted(date_counts.items())
    for date, count in sorted_dates:
        print(f"  {date}: {count} 次")
    print()
    
    # ROI分布分析
    print("📈 ROI分布分析:")
    print("-" * 60)
    
    roi_ranges = [
        ("<-20%", -float('inf'), -20),
        ("-20% ~ -10%", -20, -10),
        ("-10% ~ 0%", -10, 0),
        ("0% ~ 10%", 0, 10),
        ("10% ~ 20%", 10, 20),
        ("20% ~ 30%", 20, 30),
        ("30% ~ 50%", 30, 50),
        (">50%", 50, float('inf'))
    ]
    
    for range_name, min_val, max_val in roi_ranges:
        count = sum(1 for roi in january_2024_stats['profit_rates'] if min_val <= roi < max_val)
        percentage = (count / len(january_2024_stats['profit_rates'])) * 100
        print(f"  {range_name:>12}: {count:>2} 次 ({percentage:>5.1f}%)")
    print()
    
    # 投资时长分布
    print("⏱️ 投资时长分布:")
    print("-" * 60)
    
    duration_ranges = [
        ("<30天", 0, 30),
        ("30-60天", 30, 60),
        ("60-90天", 60, 90),
        ("90-180天", 90, 180),
        ("180-365天", 180, 365),
        (">365天", 365, float('inf'))
    ]
    
    for range_name, min_val, max_val in duration_ranges:
        count = sum(1 for duration in january_2024_stats['durations'] if min_val <= duration < max_val)
        percentage = (count / len(january_2024_stats['durations'])) * 100
        print(f"  {range_name:>10}: {count:>2} 次 ({percentage:>5.1f}%)")
    print()
    
    # 与整体表现对比
    print("📊 与整体表现对比:")
    print("-" * 60)
    
    # 从之前的分析中我们知道整体表现
    overall_win_rate = 71.0  # 整体胜率
    overall_avg_roi = 7.1    # 整体平均ROI
    overall_avg_duration = 134.2  # 整体平均投资时长
    
    print(f"2024年1月 vs 整体表现:")
    print(f"  胜率: {win_rate:.1f}% vs {overall_win_rate:.1f}% ({win_rate-overall_win_rate:+.1f}%)")
    print(f"  平均ROI: {avg_roi:.1f}% vs {overall_avg_roi:.1f}% ({avg_roi-overall_avg_roi:+.1f}%)")
    print(f"  平均投资时长: {avg_duration:.1f}天 vs {overall_avg_duration:.1f}天 ({avg_duration-overall_avg_duration:+.1f}天)")
    print()
    
    # 市场环境分析
    print("🌍 2024年1月市场环境分析:")
    print("-" * 60)
    print("2024年1月市场特征:")
    print("  - 年初市场调整期")
    print("  - 春节前资金面紧张")
    print("  - 市场情绪相对谨慎")
    print("  - 属于熊市周期（根据我们的市场周期定义）")
    print()
    
    # 策略表现评价
    print("🎯 2024年1月策略表现评价:")
    print("-" * 60)
    
    if win_rate >= 70:
        performance_level = "优秀"
    elif win_rate >= 60:
        performance_level = "良好"
    elif win_rate >= 50:
        performance_level = "一般"
    else:
        performance_level = "较差"
    
    print(f"表现等级: {performance_level}")
    print(f"主要特点:")
    print(f"  - 胜率: {win_rate:.1f}% ({'高于' if win_rate > overall_win_rate else '低于'}整体水平)")
    print(f"  - 平均ROI: {avg_roi:.1f}% ({'高于' if avg_roi > overall_avg_roi else '低于'}整体水平)")
    print(f"  - 投资时长: {avg_duration:.1f}天 ({'长于' if avg_duration > overall_avg_duration else '短于'}整体水平)")
    print(f"  - 涉及股票: {len(january_2024_stats['stocks'])} 只")
    print()
    
    print("=" * 80)
    print("✅ 2024年1月投资情况分析完成")
    print("=" * 80)

if __name__ == "__main__":
    analyze_2024_january()
