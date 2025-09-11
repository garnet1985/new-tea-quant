#!/usr/bin/env python3
"""
生成详细的黑名单分析报告
"""

import json
import os
import statistics
from collections import defaultdict

def generate_blacklist_report():
    session_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_11-524-backup"
    
    print("=" * 80)
    print("📋 HistoricLow 策略黑名单分析报告")
    print("=" * 80)
    print()
    
    # 分析所有股票表现
    stock_performance = {}
    json_files = [f for f in os.listdir(session_dir) if f.endswith('.json') and f != 'session_summary.json']
    
    print(f"📊 分析股票数量: {len(json_files)}")
    print()
    
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
            
            if len(investments) > 0:
                total_investments = len(investments)
                wins = 0
                losses = 0
                opens = 0
                total_profit = 0
                profit_rates = []
                
                for investment in investments:
                    result = investment.get('result', '')
                    profit = investment.get('overall_profit', 0)
                    profit_rate = investment.get('overall_profit_rate', 0) * 100
                    
                    total_profit += profit
                    profit_rates.append(profit_rate)
                    
                    if result == 'win':
                        wins += 1
                    elif result == 'loss':
                        losses += 1
                    elif result == 'open':
                        opens += 1
                
                win_rate = (wins / total_investments) * 100 if total_investments > 0 else 0
                avg_profit = total_profit / total_investments if total_investments > 0 else 0
                avg_roi = statistics.mean(profit_rates) if profit_rates else 0
                
                stock_performance[stock_id] = {
                    'name': stock_name,
                    'total_investments': total_investments,
                    'wins': wins,
                    'losses': losses,
                    'opens': opens,
                    'win_rate': win_rate,
                    'total_profit': total_profit,
                    'avg_profit': avg_profit,
                    'avg_roi': avg_roi
                }
        
        except Exception as e:
            continue
    
    # 定义不同的黑名单标准
    criteria_sets = [
        {
            'name': '当前标准',
            'min_investments': 3,
            'max_win_rate': 30.0,
            'max_avg_profit': -5.0
        },
        {
            'name': '严格标准',
            'min_investments': 5,
            'max_win_rate': 25.0,
            'max_avg_profit': -8.0
        },
        {
            'name': '宽松标准',
            'min_investments': 2,
            'max_win_rate': 35.0,
            'max_avg_profit': -3.0
        }
    ]
    
    print("🎯 不同黑名单标准对比:")
    print("-" * 80)
    
    for criteria in criteria_sets:
        blacklist = []
        for stock_id, perf in stock_performance.items():
            if (perf['total_investments'] >= criteria['min_investments'] and
                perf['win_rate'] <= criteria['max_win_rate'] and
                perf['avg_profit'] <= criteria['max_avg_profit']):
                blacklist.append(stock_id)
        
        print(f"\n📋 {criteria['name']}:")
        print(f"  标准: 投资≥{criteria['min_investments']}次, 胜率≤{criteria['max_win_rate']}%, 收益≤{criteria['max_avg_profit']}")
        print(f"  黑名单股票数: {len(blacklist)}")
        print(f"  占总投资股票比例: {len(blacklist)/len(stock_performance)*100:.1f}%")
        
        if blacklist:
            # 计算黑名单股票的表现
            blacklist_performance = [stock_performance[stock_id] for stock_id in blacklist]
            total_investments = sum(p['total_investments'] for p in blacklist_performance)
            avg_win_rate = statistics.mean(p['win_rate'] for p in blacklist_performance)
            avg_roi = statistics.mean(p['avg_roi'] for p in blacklist_performance)
            total_profit = sum(p['total_profit'] for p in blacklist_performance)
            
            print(f"  黑名单股票表现:")
            print(f"    总投资次数: {total_investments}")
            print(f"    平均胜率: {avg_win_rate:.1f}%")
            print(f"    平均ROI: {avg_roi:.1f}%")
            print(f"    总收益: {total_profit:.2f}")
            
            # 显示前5个最差的股票
            worst_stocks = sorted(blacklist_performance, key=lambda x: x['win_rate'])[:5]
            print(f"    最差表现股票:")
            for i, stock in enumerate(worst_stocks):
                stock_id = [k for k, v in stock_performance.items() if v == stock][0]
                print(f"      {i+1}. {stock_id} ({stock['name']}): 胜率{stock['win_rate']:.1f}%, ROI{stock['avg_roi']:.1f}%")
    
    print()
    
    # 分析当前黑名单股票
    print("📊 当前黑名单股票详细分析:")
    print("-" * 80)
    
    current_blacklist = ["000568.SZ"]  # 当前黑名单
    
    for stock_id in current_blacklist:
        if stock_id in stock_performance:
            perf = stock_performance[stock_id]
            print(f"🔍 {stock_id} ({perf['name']}):")
            print(f"  投资次数: {perf['total_investments']}")
            print(f"  成功次数: {perf['wins']}")
            print(f"  失败次数: {perf['losses']}")
            print(f"  未结清次数: {perf['opens']}")
            print(f"  胜率: {perf['win_rate']:.1f}%")
            print(f"  平均ROI: {perf['avg_roi']:.1f}%")
            print(f"  总收益: {perf['total_profit']:.2f}")
            print(f"  平均每笔收益: {perf['avg_profit']:.2f}")
            print()
    
    # 分析接近黑名单标准的股票
    print("⚠️ 接近黑名单标准的股票:")
    print("-" * 80)
    
    near_blacklist = []
    for stock_id, perf in stock_performance.items():
        # 检查是否接近黑名单标准
        if (perf['total_investments'] >= 2 and
            (perf['win_rate'] <= 35.0 or perf['avg_profit'] <= -3.0)):
            near_blacklist.append((stock_id, perf))
    
    # 按胜率排序
    near_blacklist.sort(key=lambda x: x[1]['win_rate'])
    
    print("胜率较低且投资次数较多的股票:")
    for i, (stock_id, perf) in enumerate(near_blacklist[:10]):
        print(f"  {i+1:2d}. {stock_id} ({perf['name']})")
        print(f"      投资次数: {perf['total_investments']}, 胜率: {perf['win_rate']:.1f}%, 平均收益: {perf['avg_profit']:.2f}")
    
    print()
    
    # 策略建议
    print("💡 策略优化建议:")
    print("-" * 80)
    
    print("1. 黑名单管理:")
    print("   - 当前黑名单过于严格，只包含1只股票")
    print("   - 建议采用更平衡的标准，如严格标准")
    print("   - 定期更新黑名单，建议每季度一次")
    print()
    
    print("2. 风险控制:")
    print("   - 对接近黑名单标准的股票加强监控")
    print("   - 考虑设置动态黑名单机制")
    print("   - 增加最大连续亏损次数限制")
    print()
    
    print("3. 策略改进:")
    print("   - 分析黑名单股票的共同特征")
    print("   - 优化投资机会筛选条件")
    print("   - 考虑增加行业或市值过滤")
    print()
    
    print("=" * 80)
    print("✅ 黑名单分析报告完成")
    print("=" * 80)

if __name__ == "__main__":
    generate_blacklist_report()
