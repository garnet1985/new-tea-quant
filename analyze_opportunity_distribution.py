#!/usr/bin/env python3
"""
分析524版本策略在不同市场周期下的投资机会分布
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
    """
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

def analyze_opportunity_distribution():
    session_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup"
    
    print("=" * 80)
    print("📊 524版本 HistoricLow 策略在不同市场周期下的投资机会分布分析")
    print("=" * 80)
    print()
    
    # 机会分布统计
    opportunity_stats = {
        "牛市": {
            'total_opportunities': 0,
            'successful_opportunities': 0,
            'failed_opportunities': 0,
            'open_opportunities': 0,
            'monthly_distribution': defaultdict(int),
            'yearly_distribution': defaultdict(int),
            'stock_distribution': defaultdict(int),
            'profit_distribution': [],
            'duration_distribution': []
        },
        "熊市": {
            'total_opportunities': 0,
            'successful_opportunities': 0,
            'failed_opportunities': 0,
            'open_opportunities': 0,
            'monthly_distribution': defaultdict(int),
            'yearly_distribution': defaultdict(int),
            'stock_distribution': defaultdict(int),
            'profit_distribution': [],
            'duration_distribution': []
        },
        "震荡市": {
            'total_opportunities': 0,
            'successful_opportunities': 0,
            'failed_opportunities': 0,
            'open_opportunities': 0,
            'monthly_distribution': defaultdict(int),
            'yearly_distribution': defaultdict(int),
            'stock_distribution': defaultdict(int),
            'profit_distribution': [],
            'duration_distribution': []
        }
    }
    
    # 分析文件
    json_files = [f for f in os.listdir(session_dir) if f.endswith('.json') and f != 'session_summary.json']
    
    print(f"📁 分析文件数量: {len(json_files)}")
    print(f"🔍 分析样本: 前 200 个股票文件")
    print()
    
    sample_size = min(200, len(json_files))
    total_opportunities = 0
    
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
                total_opportunities += 1
                
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
                    
                    if cycle in opportunity_stats:
                        # 统计机会分布
                        opportunity_stats[cycle]['total_opportunities'] += 1
                        opportunity_stats[cycle]['monthly_distribution'][f"{year}-{month:02d}"] += 1
                        opportunity_stats[cycle]['yearly_distribution'][year] += 1
                        opportunity_stats[cycle]['stock_distribution'][stock_id] += 1
                        opportunity_stats[cycle]['profit_distribution'].append(profit_rate)
                        opportunity_stats[cycle]['duration_distribution'].append(duration)
                        
                        if result == 'win':
                            opportunity_stats[cycle]['successful_opportunities'] += 1
                        elif result == 'loss':
                            opportunity_stats[cycle]['failed_opportunities'] += 1
                        elif result == 'open':
                            opportunity_stats[cycle]['open_opportunities'] += 1
        
        except Exception as e:
            print(f"❌ 读取文件 {filename} 失败: {e}")
            continue
    
    print(f"📊 总分析投资机会: {total_opportunities}")
    print()
    
    # 显示机会分布对比
    print("📊 不同市场周期下的投资机会分布对比:")
    print("-" * 80)
    print(f"{'市场周期':<10} {'总机会':<8} {'成功':<8} {'失败':<8} {'未结清':<8} {'成功率':<8} {'平均ROI':<10}")
    print("-" * 80)
    
    for cycle_name in ["牛市", "熊市", "震荡市"]:
        stats = opportunity_stats[cycle_name]
        if stats['total_opportunities'] > 0:
            success_rate = (stats['successful_opportunities'] / stats['total_opportunities']) * 100
            avg_roi = statistics.mean(stats['profit_distribution']) if stats['profit_distribution'] else 0
            
            print(f"{cycle_name:<10} {stats['total_opportunities']:<8} {stats['successful_opportunities']:<8} {stats['failed_opportunities']:<8} {stats['open_opportunities']:<8} {success_rate:<7.1f}% {avg_roi:<9.1f}%")
    
    print()
    
    # 详细分析每个市场周期的机会分布
    for cycle_name in ["牛市", "熊市", "震荡市"]:
        stats = opportunity_stats[cycle_name]
        if stats['total_opportunities'] > 0:
            print(f"📈 {cycle_name}投资机会详细分析:")
            print("-" * 60)
            
            # 基本统计
            success_rate = (stats['successful_opportunities'] / stats['total_opportunities']) * 100
            avg_roi = statistics.mean(stats['profit_distribution']) if stats['profit_distribution'] else 0
            median_roi = statistics.median(stats['profit_distribution']) if stats['profit_distribution'] else 0
            avg_duration = statistics.mean(stats['duration_distribution']) if stats['duration_distribution'] else 0
            
            print(f"基本统计:")
            print(f"  总机会数: {stats['total_opportunities']}")
            print(f"  成功机会: {stats['successful_opportunities']}")
            print(f"  失败机会: {stats['failed_opportunities']}")
            print(f"  未结清机会: {stats['open_opportunities']}")
            print(f"  成功率: {success_rate:.1f}%")
            print(f"  平均ROI: {avg_roi:.1f}%")
            print(f"  中位数ROI: {median_roi:.1f}%")
            print(f"  平均投资时长: {avg_duration:.1f}天")
            print()
            
            # 年度机会分布
            print(f"年度机会分布:")
            sorted_years = sorted(stats['yearly_distribution'].keys())
            for year in sorted_years:
                count = stats['yearly_distribution'][year]
                percentage = (count / stats['total_opportunities']) * 100
                print(f"  {year}年: {count} 次 ({percentage:.1f}%)")
            print()
            
            # 月度机会分布 (显示前10个月)
            print(f"月度机会分布 (前10个月):")
            sorted_months = sorted(stats['monthly_distribution'].items(), key=lambda x: x[1], reverse=True)
            for i, (month, count) in enumerate(sorted_months[:10]):
                percentage = (count / stats['total_opportunities']) * 100
                print(f"  {i+1:2d}. {month}: {count} 次 ({percentage:.1f}%)")
            print()
            
            # 股票机会分布 (显示前10只股票)
            print(f"股票机会分布 (前10只股票):")
            sorted_stocks = sorted(stats['stock_distribution'].items(), key=lambda x: x[1], reverse=True)
            for i, (stock_id, count) in enumerate(sorted_stocks[:10]):
                percentage = (count / stats['total_opportunities']) * 100
                print(f"  {i+1:2d}. {stock_id}: {count} 次 ({percentage:.1f}%)")
            print()
            
            # ROI分布分析
            if stats['profit_distribution']:
                print(f"ROI分布分析:")
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
                    count = sum(1 for roi in stats['profit_distribution'] if min_val <= roi < max_val)
                    percentage = (count / len(stats['profit_distribution'])) * 100
                    print(f"  {range_name:>12}: {count:>3} 次 ({percentage:>5.1f}%)")
                print()
            
            # 投资时长分布
            if stats['duration_distribution']:
                print(f"投资时长分布:")
                duration_ranges = [
                    ("<30天", 0, 30),
                    ("30-60天", 30, 60),
                    ("60-90天", 60, 90),
                    ("90-180天", 90, 180),
                    ("180-365天", 180, 365),
                    (">365天", 365, float('inf'))
                ]
                
                for range_name, min_val, max_val in duration_ranges:
                    count = sum(1 for duration in stats['duration_distribution'] if min_val <= duration < max_val)
                    percentage = (count / len(stats['duration_distribution'])) * 100
                    print(f"  {range_name:>10}: {count:>3} 次 ({percentage:>5.1f}%)")
                print()
    
    # 机会密度分析
    print("📊 机会密度分析:")
    print("-" * 60)
    
    # 计算每个市场周期的机会密度
    cycle_densities = {}
    for cycle_name, stats in opportunity_stats.items():
        if stats['total_opportunities'] > 0:
            # 计算涉及的年份数
            years_count = len(stats['yearly_distribution'])
            if years_count > 0:
                density = stats['total_opportunities'] / years_count
                cycle_densities[cycle_name] = density
    
    if cycle_densities:
        print("年度平均机会密度:")
        for cycle_name, density in sorted(cycle_densities.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cycle_name}: {density:.1f} 次/年")
        print()
    
    # 机会质量分析
    print("🎯 机会质量分析:")
    print("-" * 60)
    
    for cycle_name in ["牛市", "熊市", "震荡市"]:
        stats = opportunity_stats[cycle_name]
        if stats['total_opportunities'] > 0:
            success_rate = (stats['successful_opportunities'] / stats['total_opportunities']) * 100
            avg_roi = statistics.mean(stats['profit_distribution']) if stats['profit_distribution'] else 0
            
            # 计算机会质量分数 (成功率 * 平均ROI)
            quality_score = success_rate * avg_roi / 100
            
            if quality_score >= 5:
                quality_level = "优秀"
            elif quality_score >= 3:
                quality_level = "良好"
            elif quality_score >= 1:
                quality_level = "一般"
            else:
                quality_level = "较差"
            
            print(f"{cycle_name}:")
            print(f"  成功率: {success_rate:.1f}%")
            print(f"  平均ROI: {avg_roi:.1f}%")
            print(f"  质量分数: {quality_score:.2f}")
            print(f"  质量等级: {quality_level}")
            print()
    
    print("=" * 80)
    print("✅ 机会分布分析完成")
    print("=" * 80)

if __name__ == "__main__":
    analyze_opportunity_distribution()
