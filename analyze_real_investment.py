#!/usr/bin/env python3
"""
分析实际投资回报情况
考虑分段平仓的资金流动
假设初始资金10万元，每次投资1000股
使用策略设置中的实际止盈比例
"""
import json
import os
from datetime import datetime
import sys
sys.path.append('app/analyzer/strategy/historicLow')
from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings

def analyze_real_investment():
    # 基础配置
    base_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_04-329"
    
    print("=== 重新分析：样本数量与收益率关系 ===\n")
    
    # 测试不同样本数量的收益率
    sample_scenarios = [
        {"name": "前10只股票", "samples": 10},
        {"name": "前15只股票", "samples": 15},
        {"name": "前20只股票", "samples": 20},
        {"name": "前25只股票", "samples": 25},
        {"name": "全部32只股票", "samples": 32},
    ]
    
    for scenario in sample_scenarios:
        print(f"--- {scenario['name']} ---")
        analyze_sample_performance(base_dir, scenario['samples'])
        print()

def analyze_sample_performance(base_dir, sample_count):
    """分析不同样本数量的表现"""
    from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings
    take_profit_stages = strategy_settings["goal"]["take_profit"]["stages"]
    
    # 读取投资记录
    investment_files = []
    for file in os.listdir(base_dir):
        if file.endswith('.json') and file != 'session_summary.json':
            investment_files.append(file)
    
    all_investments = []
    for file in investment_files:
        file_path = os.path.join(base_dir, file)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'results' in data and data['results']:
                for result in data['results']:
                    if 'investment' in result and 'targets' in result['investment']:
                        all_investments.append(result['investment'])
    
    # 取前N只股票
    selected_investments = all_investments[:sample_count]
    
    # 模拟投资（考虑复利效应）
    initial_capital = 100000
    available_capital = initial_capital
    current_capital = initial_capital
    total_invested = 0
    total_returned = 0
    transactions = []
    
    for inv in selected_investments:
        # 检查是否有足够资金投资
        if available_capital >= 1000 * 15:  # 假设平均股价15元
            buy_amount = 1000 * 15
            available_capital -= buy_amount
            total_invested += buy_amount
            
            transactions.append({
                'type': '买入',
                'amount': buy_amount,
                'available_capital': available_capital,
                'total_capital': current_capital
            })
            
            # 处理卖出
            remaining_shares = 1000
            for target in inv.get('targets', []):
                if target.get('is_achieved', False):
                    target_name = target.get('name')
                    profit_rate = target.get('profit_rate', 0)
                    sell_price = target.get('sell_price', 0)
                    
                    # 计算卖出股数
                    if target_name == "dynamic":
                        trade_type = '动态止损(盈利)'
                        exit_ratio = remaining_shares / 1000
                    elif target_name == "break_even" and profit_rate > 0:
                        trade_type = '止盈'
                        # 匹配止盈阶段
                        exit_ratio = 0
                        for stage in take_profit_stages:
                            stage_win_ratio = stage.get("win_ratio", 0)
                            if abs(profit_rate - stage_win_ratio) < 0.05:
                                exit_ratio = stage.get("sell_ratio", 0)
                                break
                        if exit_ratio == 0:
                            exit_ratio = remaining_shares / 1000
                    else:
                        trade_type = '其他止损'
                        exit_ratio = remaining_shares / 1000
                    
                    if exit_ratio > 0:
                        sell_shares = int(remaining_shares * exit_ratio)
                        if sell_shares > 0:
                            sell_amount = sell_shares * sell_price
                            available_capital += sell_amount
                            current_capital += sell_amount
                            total_returned += sell_amount
                            remaining_shares -= sell_shares
                            
                            transactions.append({
                                'type': trade_type,
                                'amount': sell_amount,
                                'available_capital': available_capital,
                                'total_capital': current_capital
                            })
            
            # 处理剩余仓位（保本止损）
            if remaining_shares > 0:
                breakeven_amount = remaining_shares * 15  # 假设保本价格
                available_capital += breakeven_amount
                current_capital += breakeven_amount
                total_returned += breakeven_amount
                
                transactions.append({
                    'type': '保本止损',
                    'amount': breakeven_amount,
                    'available_capital': available_capital,
                    'total_capital': current_capital
                })
    
    # 计算统计
    total_years = 7.73
    net_profit = current_capital - initial_capital
    annual_return = ((current_capital / initial_capital) ** (1 / total_years) - 1) * 100
    
    profit_transactions = [t for t in transactions if t['type'] in ['止盈', '动态止损(盈利)', '保本止损']]
    loss_transactions = [t for t in transactions if t['type'] in ['其他止损']]
    
    print(f"样本数量: {sample_count} 只股票")
    print(f"总交易次数: {len(transactions)}")
    print(f"盈利交易: {len(profit_transactions)} 次")
    print(f"亏损交易: {len(loss_transactions)} 次")
    if len(profit_transactions) + len(loss_transactions) > 0:
        win_rate = len(profit_transactions) / (len(profit_transactions) + len(loss_transactions)) * 100
        print(f"胜率: {win_rate:.2f}%")
    
    print(f"总投入资金: {total_invested:,.2f} 元")
    print(f"总回收资金: {total_returned:,.2f} 元")
    print(f"最终资金: {current_capital:,.2f} 元")
    print(f"净收益: {net_profit:+,.2f} 元")
    print(f"年化收益率: {annual_return:+.2f}%")
    print(f"资金利用率: {(total_invested / initial_capital) * 100:.2f}%")

if __name__ == "__main__":
    analyze_real_investment()
