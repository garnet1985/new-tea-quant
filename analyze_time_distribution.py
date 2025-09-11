#!/usr/bin/env python3
"""
分析524版本的投资机会和收益的时间分布
"""

import json
import os
import statistics
from collections import defaultdict
from datetime import datetime

def parse_date(date_str):
    """解析日期字符串，支持多种格式"""
    if not date_str:
        return None
    
    # 尝试不同的日期格式
    formats = ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def analyze_time_distribution():
    session_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup"
    
    print("=" * 80)
    print("📅 524版本 HistoricLow 策略时间分布分析")
    print("=" * 80)
    print()
    
    # 时间分布统计
    yearly_stats = defaultdict(lambda: {
        'investments': 0,
        'wins': 0,
        'losses': 0,
        'opens': 0,
        'total_profit': 0,
        'total_duration': 0,
        'profit_rates': []
    })
    
    monthly_stats = defaultdict(lambda: {
        'investments': 0,
        'wins': 0,
        'losses': 0,
        'opens': 0,
        'total_profit': 0,
        'total_duration': 0,
        'profit_rates': []
    })
    
    quarterly_stats = defaultdict(lambda: {
        'investments': 0,
        'wins': 0,
        'losses': 0,
        'opens': 0,
        'total_profit': 0,
        'total_duration': 0,
        'profit_rates': []
    })
    
    # 投资开始时间分布
    start_time_distribution = defaultdict(int)
    # 投资结束时间分布
    end_time_distribution = defaultdict(int)
    
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
                end_date_str = investment.get('end_date', '')
                result = investment.get('result', '')
                profit = investment.get('overall_profit', 0)
                profit_rate = investment.get('overall_profit_rate', 0) * 100
                duration = investment.get('invest_duration_days', 0)
                
                # 解析开始日期
                start_date = parse_date(start_date_str)
                if start_date:
                    year = start_date.year
                    month = start_date.month
                    quarter = (month - 1) // 3 + 1
                    
                    # 年度统计
                    yearly_stats[year]['investments'] += 1
                    yearly_stats[year]['total_profit'] += profit
                    yearly_stats[year]['total_duration'] += duration
                    yearly_stats[year]['profit_rates'].append(profit_rate)
                    
                    if result == 'win':
                        yearly_stats[year]['wins'] += 1
                    elif result == 'loss':
                        yearly_stats[year]['losses'] += 1
                    elif result == 'open':
                        yearly_stats[year]['opens'] += 1
                    
                    # 月度统计
                    month_key = f"{year}-{month:02d}"
                    monthly_stats[month_key]['investments'] += 1
                    monthly_stats[month_key]['total_profit'] += profit
                    monthly_stats[month_key]['total_duration'] += duration
                    monthly_stats[month_key]['profit_rates'].append(profit_rate)
                    
                    if result == 'win':
                        monthly_stats[month_key]['wins'] += 1
                    elif result == 'loss':
                        monthly_stats[month_key]['losses'] += 1
                    elif result == 'open':
                        monthly_stats[month_key]['opens'] += 1
                    
                    # 季度统计
                    quarter_key = f"{year}Q{quarter}"
                    quarterly_stats[quarter_key]['investments'] += 1
                    quarterly_stats[quarter_key]['total_profit'] += profit
                    quarterly_stats[quarter_key]['total_duration'] += duration
                    quarterly_stats[quarter_key]['profit_rates'].append(profit_rate)
                    
                    if result == 'win':
                        quarterly_stats[quarter_key]['wins'] += 1
                    elif result == 'loss':
                        quarterly_stats[quarter_key]['losses'] += 1
                    elif result == 'open':
                        quarterly_stats[quarter_key]['opens'] += 1
                    
                    # 开始时间分布
                    start_time_distribution[year] += 1
                
                # 解析结束日期
                end_date = parse_date(end_date_str)
                if end_date:
                    end_time_distribution[end_date.year] += 1
        
        except Exception as e:
            print(f"❌ 读取文件 {filename} 失败: {e}")
            continue
    
    print(f"📊 总分析投资次数: {total_investments}")
    print()
    
    # 年度分析
    print("📅 年度投资分布分析:")
    print("-" * 80)
    print(f"{'年份':<8} {'投资次数':<8} {'胜率':<8} {'平均ROI':<10} {'总收益':<10} {'平均时长':<10}")
    print("-" * 80)
    
    sorted_years = sorted(yearly_stats.keys())
    for year in sorted_years:
        stats = yearly_stats[year]
        if stats['investments'] > 0:
            win_rate = (stats['wins'] / stats['investments']) * 100
            avg_roi = statistics.mean(stats['profit_rates']) if stats['profit_rates'] else 0
            avg_duration = stats['total_duration'] / stats['investments']
            
            print(f"{year:<8} {stats['investments']:<8} {win_rate:<7.1f}% {avg_roi:<9.1f}% {stats['total_profit']:<9.1f} {avg_duration:<9.1f}天")
    
    print()
    
    # 季度分析
    print("📊 季度投资分布分析:")
    print("-" * 80)
    print(f"{'季度':<8} {'投资次数':<8} {'胜率':<8} {'平均ROI':<10} {'总收益':<10} {'平均时长':<10}")
    print("-" * 80)
    
    sorted_quarters = sorted(quarterly_stats.keys())
    for quarter in sorted_quarters:
        stats = quarterly_stats[quarter]
        if stats['investments'] > 0:
            win_rate = (stats['wins'] / stats['investments']) * 100
            avg_roi = statistics.mean(stats['profit_rates']) if stats['profit_rates'] else 0
            avg_duration = stats['total_duration'] / stats['investments']
            
            print(f"{quarter:<8} {stats['investments']:<8} {win_rate:<7.1f}% {avg_roi:<9.1f}% {stats['total_profit']:<9.1f} {avg_duration:<9.1f}天")
    
    print()
    
    # 月度分析（显示前20个月）
    print("📈 月度投资分布分析 (前20个月):")
    print("-" * 80)
    print(f"{'月份':<10} {'投资次数':<8} {'胜率':<8} {'平均ROI':<10} {'总收益':<10} {'平均时长':<10}")
    print("-" * 80)
    
    sorted_months = sorted(monthly_stats.keys())
    for month in sorted_months[:20]:  # 只显示前20个月
        stats = monthly_stats[month]
        if stats['investments'] > 0:
            win_rate = (stats['wins'] / stats['investments']) * 100
            avg_roi = statistics.mean(stats['profit_rates']) if stats['profit_rates'] else 0
            avg_duration = stats['total_duration'] / stats['investments']
            
            print(f"{month:<10} {stats['investments']:<8} {win_rate:<7.1f}% {avg_roi:<9.1f}% {stats['total_profit']:<9.1f} {avg_duration:<9.1f}天")
    
    print()
    
    # 时间分布统计
    print("⏰ 投资时间分布统计:")
    print("-" * 50)
    
    # 投资开始年份分布
    print("📅 投资开始年份分布:")
    for year in sorted(start_time_distribution.keys()):
        count = start_time_distribution[year]
        percentage = (count / total_investments) * 100
        print(f"  {year}: {count:,} 次 ({percentage:.1f}%)")
    
    print()
    
    # 投资结束年份分布
    print("📅 投资结束年份分布:")
    for year in sorted(end_time_distribution.keys()):
        count = end_time_distribution[year]
        percentage = (count / total_investments) * 100
        print(f"  {year}: {count:,} 次 ({percentage:.1f}%)")
    
    print()
    
    # 最佳表现时间段
    print("🏆 最佳表现时间段分析:")
    print("-" * 50)
    
    # 按胜率排序的年度表现
    year_performance = []
    for year, stats in yearly_stats.items():
        if stats['investments'] >= 10:  # 至少10次投资
            win_rate = (stats['wins'] / stats['investments']) * 100
            avg_roi = statistics.mean(stats['profit_rates']) if stats['profit_rates'] else 0
            year_performance.append((year, win_rate, avg_roi, stats['investments']))
    
    year_performance.sort(key=lambda x: x[1], reverse=True)  # 按胜率排序
    
    print("📈 年度胜率排名 (至少10次投资):")
    for i, (year, win_rate, avg_roi, count) in enumerate(year_performance[:5]):
        print(f"  {i+1}. {year}年: 胜率 {win_rate:.1f}%, 平均ROI {avg_roi:.1f}%, 投资 {count} 次")
    
    print()
    
    # 按平均ROI排序的年度表现
    year_performance.sort(key=lambda x: x[2], reverse=True)  # 按平均ROI排序
    
    print("💰 年度平均ROI排名 (至少10次投资):")
    for i, (year, win_rate, avg_roi, count) in enumerate(year_performance[:5]):
        print(f"  {i+1}. {year}年: 平均ROI {avg_roi:.1f}%, 胜率 {win_rate:.1f}%, 投资 {count} 次")
    
    print()
    
    # 季度表现分析
    quarter_performance = []
    for quarter, stats in quarterly_stats.items():
        if stats['investments'] >= 5:  # 至少5次投资
            win_rate = (stats['wins'] / stats['investments']) * 100
            avg_roi = statistics.mean(stats['profit_rates']) if stats['profit_rates'] else 0
            quarter_performance.append((quarter, win_rate, avg_roi, stats['investments']))
    
    quarter_performance.sort(key=lambda x: x[1], reverse=True)  # 按胜率排序
    
    print("📊 季度胜率排名 (至少5次投资):")
    for i, (quarter, win_rate, avg_roi, count) in enumerate(quarter_performance[:5]):
        print(f"  {i+1}. {quarter}: 胜率 {win_rate:.1f}%, 平均ROI {avg_roi:.1f}%, 投资 {count} 次")
    
    print()
    
    # 时间趋势分析
    print("📈 时间趋势分析:")
    print("-" * 50)
    
    if len(sorted_years) >= 2:
        first_year = sorted_years[0]
        last_year = sorted_years[-1]
        
        first_stats = yearly_stats[first_year]
        last_stats = yearly_stats[last_year]
        
        if first_stats['investments'] > 0 and last_stats['investments'] > 0:
            first_win_rate = (first_stats['wins'] / first_stats['investments']) * 100
            last_win_rate = (last_stats['wins'] / last_stats['investments']) * 100
            
            first_avg_roi = statistics.mean(first_stats['profit_rates']) if first_stats['profit_rates'] else 0
            last_avg_roi = statistics.mean(last_stats['profit_rates']) if last_stats['profit_rates'] else 0
            
            print(f"📅 {first_year}年 vs {last_year}年:")
            print(f"  胜率变化: {first_win_rate:.1f}% → {last_win_rate:.1f}% ({last_win_rate-first_win_rate:+.1f}%)")
            print(f"  平均ROI变化: {first_avg_roi:.1f}% → {last_avg_roi:.1f}% ({last_avg_roi-first_avg_roi:+.1f}%)")
            print(f"  投资次数变化: {first_stats['investments']} → {last_stats['investments']} ({last_stats['investments']-first_stats['investments']:+d})")
    
    print()
    print("=" * 80)
    print("✅ 时间分布分析完成")
    print("=" * 80)

if __name__ == "__main__":
    analyze_time_distribution()
