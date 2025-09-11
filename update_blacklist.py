#!/usr/bin/env python3
"""
扫描524版本模拟结果，整理黑名单并替换settings，然后对比结果
"""

import json
import os
import statistics
from collections import defaultdict
import re

def analyze_stock_performance():
    """分析股票表现，生成黑名单"""
    session_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup"
    
    print("=" * 80)
    print("📊 扫描524版本模拟结果，分析股票表现")
    print("=" * 80)
    print()
    
    # 股票表现统计
    stock_performance = {}
    
    # 分析文件
    json_files = [f for f in os.listdir(session_dir) if f.endswith('.json') and f != 'session_summary.json']
    
    print(f"📁 分析文件数量: {len(json_files)}")
    print()
    
    total_stocks = 0
    stocks_with_investments = 0
    
    for filename in json_files:
        if filename == 'session_summary.json':
            continue
            
        file_path = os.path.join(session_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stock_id = data['stock_info']['id']
            stock_name = data['stock_info']['name']
            investments = data['investments']
            
            total_stocks += 1
            
            if len(investments) > 0:
                stocks_with_investments += 1
                
                # 统计该股票的投资表现
                total_investments = len(investments)
                wins = 0
                losses = 0
                opens = 0
                total_profit = 0
                total_duration = 0
                profit_rates = []
                
                for investment in investments:
                    result = investment.get('result', '')
                    profit = investment.get('overall_profit', 0)
                    profit_rate = investment.get('overall_profit_rate', 0) * 100
                    duration = investment.get('invest_duration_days', 0)
                    
                    total_profit += profit
                    total_duration += duration
                    profit_rates.append(profit_rate)
                    
                    if result == 'win':
                        wins += 1
                    elif result == 'loss':
                        losses += 1
                    elif result == 'open':
                        opens += 1
                
                # 计算表现指标
                win_rate = (wins / total_investments) * 100 if total_investments > 0 else 0
                avg_profit = total_profit / total_investments if total_investments > 0 else 0
                avg_roi = statistics.mean(profit_rates) if profit_rates else 0
                avg_duration = total_duration / total_investments if total_investments > 0 else 0
                
                stock_performance[stock_id] = {
                    'name': stock_name,
                    'total_investments': total_investments,
                    'wins': wins,
                    'losses': losses,
                    'opens': opens,
                    'win_rate': win_rate,
                    'total_profit': total_profit,
                    'avg_profit': avg_profit,
                    'avg_roi': avg_roi,
                    'avg_duration': avg_duration,
                    'profit_rates': profit_rates
                }
        
        except Exception as e:
            print(f"❌ 读取文件 {filename} 失败: {e}")
            continue
    
    print(f"📊 统计结果:")
    print(f"  总股票数: {total_stocks}")
    print(f"  有投资记录的股票数: {stocks_with_investments}")
    print(f"  无投资记录的股票数: {total_stocks - stocks_with_investments}")
    print()
    
    return stock_performance

def generate_blacklist(stock_performance, criteria):
    """根据标准生成黑名单"""
    print("🎯 生成黑名单:")
    print("-" * 60)
    print(f"黑名单标准:")
    print(f"  - 最少投资次数: {criteria['min_investments']}")
    print(f"  - 最大胜率: {criteria['max_win_rate']}%")
    print(f"  - 最大平均收益: {criteria['max_avg_profit']}")
    print()
    
    blacklist = []
    
    for stock_id, perf in stock_performance.items():
        # 检查是否满足黑名单条件
        if (perf['total_investments'] >= criteria['min_investments'] and
            perf['win_rate'] <= criteria['max_win_rate'] and
            perf['avg_profit'] <= criteria['max_avg_profit']):
            
            blacklist.append(stock_id)
            print(f"  ❌ {stock_id} ({perf['name']})")
            print(f"      投资次数: {perf['total_investments']}, 胜率: {perf['win_rate']:.1f}%, 平均收益: {perf['avg_profit']:.2f}")
    
    print(f"\n📊 黑名单统计:")
    print(f"  黑名单股票数: {len(blacklist)}")
    print(f"  占总投资股票比例: {len(blacklist)/len(stock_performance)*100:.1f}%")
    print()
    
    return blacklist

def update_settings_blacklist(new_blacklist):
    """更新settings文件中的黑名单"""
    settings_file = "app/analyzer/strategy/historicLow/strategy_settings.py"
    
    print("📝 更新settings文件中的黑名单:")
    print("-" * 60)
    
    try:
        # 读取当前配置文件
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 构建新的黑名单配置
        blacklist_lines = []
        blacklist_lines.append('        "list": [')
        
        for i, stock in enumerate(new_blacklist):
            comma = "," if i < len(new_blacklist) - 1 else ""
            blacklist_lines.append(f'            "{stock}"{comma}')
        
        blacklist_lines.append('        ],')
        blacklist_lines.append(f'        "count": {len(new_blacklist)},  # 问题股票总数')
        blacklist_lines.append('        "description": "基于524版本模拟结果自动更新的黑名单"')
        
        new_blacklist_config = '\n'.join(blacklist_lines)
        
        # 替换黑名单配置
        pattern = r'"problematic_stocks":\s*\{[^}]*\}'
        replacement = f'"problematic_stocks": {{\n{new_blacklist_config}\n    }}'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 写回文件
        with open(settings_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 已更新配置文件中的黑名单")
        print(f"  新黑名单包含 {len(new_blacklist)} 只股票")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        return False

def compare_blacklists(old_blacklist, new_blacklist):
    """对比新旧黑名单"""
    print("📊 黑名单对比分析:")
    print("-" * 60)
    
    old_set = set(old_blacklist)
    new_set = set(new_blacklist)
    
    # 计算差异
    added = new_set - old_set
    removed = old_set - new_set
    kept = old_set & new_set
    
    print(f"原黑名单股票数: {len(old_blacklist)}")
    print(f"新黑名单股票数: {len(new_blacklist)}")
    print(f"新增股票数: {len(added)}")
    print(f"移除股票数: {len(removed)}")
    print(f"保留股票数: {len(kept)}")
    print()
    
    if added:
        print("🆕 新增到黑名单的股票:")
        for stock in sorted(added):
            print(f"  + {stock}")
        print()
    
    if removed:
        print("➖ 从黑名单移除的股票:")
        for stock in sorted(removed):
            print(f"  - {stock}")
        print()
    
    if kept:
        print("🔄 保留在黑名单的股票:")
        for stock in sorted(kept):
            print(f"  = {stock}")
        print()

def analyze_blacklist_impact(stock_performance, old_blacklist, new_blacklist):
    """分析黑名单更新的影响"""
    print("📈 黑名单更新影响分析:")
    print("-" * 60)
    
    # 计算原黑名单股票的表现
    old_blacklist_performance = []
    for stock_id in old_blacklist:
        if stock_id in stock_performance:
            old_blacklist_performance.append(stock_performance[stock_id])
    
    # 计算新黑名单股票的表现
    new_blacklist_performance = []
    for stock_id in new_blacklist:
        if stock_id in stock_performance:
            new_blacklist_performance.append(stock_performance[stock_id])
    
    # 计算非黑名单股票的表现
    non_blacklist_stocks = set(stock_performance.keys()) - set(new_blacklist)
    non_blacklist_performance = []
    for stock_id in non_blacklist_stocks:
        non_blacklist_performance.append(stock_performance[stock_id])
    
    def calculate_stats(performance_list):
        if not performance_list:
            return {
                'count': 0,
                'total_investments': 0,
                'avg_win_rate': 0,
                'avg_roi': 0,
                'total_profit': 0
            }
        
        total_investments = sum(p['total_investments'] for p in performance_list)
        avg_win_rate = statistics.mean(p['win_rate'] for p in performance_list)
        avg_roi = statistics.mean(p['avg_roi'] for p in performance_list)
        total_profit = sum(p['total_profit'] for p in performance_list)
        
        return {
            'count': len(performance_list),
            'total_investments': total_investments,
            'avg_win_rate': avg_win_rate,
            'avg_roi': avg_roi,
            'total_profit': total_profit
        }
    
    old_stats = calculate_stats(old_blacklist_performance)
    new_stats = calculate_stats(new_blacklist_performance)
    non_blacklist_stats = calculate_stats(non_blacklist_performance)
    
    print("原黑名单股票表现:")
    print(f"  股票数: {old_stats['count']}")
    print(f"  总投资次数: {old_stats['total_investments']}")
    print(f"  平均胜率: {old_stats['avg_win_rate']:.1f}%")
    print(f"  平均ROI: {old_stats['avg_roi']:.1f}%")
    print(f"  总收益: {old_stats['total_profit']:.2f}")
    print()
    
    print("新黑名单股票表现:")
    print(f"  股票数: {new_stats['count']}")
    print(f"  总投资次数: {new_stats['total_investments']}")
    print(f"  平均胜率: {new_stats['avg_win_rate']:.1f}%")
    print(f"  平均ROI: {new_stats['avg_roi']:.1f}%")
    print(f"  总收益: {new_stats['total_profit']:.2f}")
    print()
    
    print("非黑名单股票表现:")
    print(f"  股票数: {non_blacklist_stats['count']}")
    print(f"  总投资次数: {non_blacklist_stats['total_investments']}")
    print(f"  平均胜率: {non_blacklist_stats['avg_win_rate']:.1f}%")
    print(f"  平均ROI: {non_blacklist_stats['avg_roi']:.1f}%")
    print(f"  总收益: {non_blacklist_stats['total_profit']:.2f}")
    print()
    
    # 计算改善情况
    if old_stats['count'] > 0 and new_stats['count'] > 0:
        win_rate_improvement = new_stats['avg_win_rate'] - old_stats['avg_win_rate']
        roi_improvement = new_stats['avg_roi'] - old_stats['avg_roi']
        
        print("黑名单更新效果:")
        print(f"  平均胜率变化: {win_rate_improvement:+.1f}%")
        print(f"  平均ROI变化: {roi_improvement:+.1f}%")
        print()

def main():
    # 分析股票表现
    stock_performance = analyze_stock_performance()
    
    if not stock_performance:
        print("❌ 没有找到股票表现数据")
        return
    
    # 读取当前黑名单
    try:
        with open("app/analyzer/strategy/historicLow/strategy_settings.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取当前黑名单
        import ast
        import re
        
        # 找到problematic_stocks部分
        match = re.search(r'"problematic_stocks":\s*\{[^}]*"list":\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            list_content = match.group(1)
            # 提取股票ID
            old_blacklist = re.findall(r'"([^"]+)"', list_content)
        else:
            old_blacklist = []
        
        print(f"📋 当前黑名单: {len(old_blacklist)} 只股票")
        print()
        
    except Exception as e:
        print(f"❌ 读取当前黑名单失败: {e}")
        old_blacklist = []
    
    # 定义黑名单标准
    criteria = {
        'min_investments': 3,      # 最少3次投资
        'max_win_rate': 30.0,      # 胜率低于30%
        'max_avg_profit': -5.0     # 平均收益低于-5%
    }
    
    # 生成新黑名单
    new_blacklist = generate_blacklist(stock_performance, criteria)
    
    # 对比黑名单
    compare_blacklists(old_blacklist, new_blacklist)
    
    # 分析黑名单更新影响
    analyze_blacklist_impact(stock_performance, old_blacklist, new_blacklist)
    
    # 更新settings文件
    if new_blacklist:
        success = update_settings_blacklist(new_blacklist)
        if success:
            print("✅ 黑名单更新完成！")
        else:
            print("❌ 黑名单更新失败！")
    else:
        print("ℹ️ 没有股票满足黑名单条件，无需更新")
    
    print()
    print("=" * 80)
    print("✅ 黑名单分析和更新完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
