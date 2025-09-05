#!/usr/bin/env python3
"""
分析模拟结果中股票的止盈分布情况
统计各个止盈档位的触发次数和分布
"""
import os
import json
from collections import defaultdict
from typing import Dict, List, Any

def analyze_take_profit_distribution():
    """分析平仓分布情况（包括动态止损）"""
    base_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_04-326"
    
    # 统计变量
    total_investments = 0
    total_exits = 0
    exit_distribution = defaultdict(int)  # 按平仓类型统计
    stock_exit_summary = []  # 每只股票的平仓汇总
    dynamic_stop_details = []  # 动态止损详情
    
    # 遍历所有JSON文件
    for filename in os.listdir(base_dir):
        if filename.endswith('.json') and filename != 'session_summary.json':
            filepath = os.path.join(base_dir, filename)
            stock_id = filename.replace('.json', '')
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                results = data.get('results', [])
                stock_exit_count = 0
                stock_exit_details = []
                
                for result in results:
                    total_investments += 1
                    targets = result.get('investment', {}).get('targets', [])
                    
                    # 统计这只股票的平仓情况
                    for target in targets:
                        target_win_ratio = target.get('target_win_ratio')
                        is_achieved = target.get('is_achieved', False)
                        profit_weight = target.get('profit_weight', 0)
                        profit_rate = target.get('profit_rate', 0)
                        
                        # 统计所有已实现的平仓
                        if is_achieved and profit_weight != 0:
                            total_exits += 1
                            stock_exit_count += 1
                            
                            # 分类平仓类型
                            if target_win_ratio == "dynamic":
                                exit_type = "动态止损"
                                dynamic_stop_details.append({
                                    'stock_id': stock_id,
                                    'profit_rate': profit_rate,
                                    'profit_weight': profit_weight,
                                    'sell_price': target.get('sell_price', 0)
                                })
                            elif target_win_ratio == 0.0:
                                # 检查profit_rate来判断是否是止盈
                                if profit_rate > 0.05:  # 如果收益率大于5%，认为是止盈
                                    exit_type = f"{profit_rate*100:.1f}%止盈"
                                else:
                                    exit_type = "止损"
                            elif target_win_ratio in [0.1, 0.2, 0.3, 0.4]:
                                exit_type = f"{target_win_ratio*100:.0f}%止盈"
                            elif isinstance(target_win_ratio, (int, float)) and target_win_ratio > 0:
                                exit_type = f"{target_win_ratio*100:.1f}%止盈"
                            else:
                                exit_type = f"其他({target_win_ratio})"
                            
                            exit_distribution[exit_type] += 1
                            
                            stock_exit_details.append({
                                'type': exit_type,
                                'win_ratio': target_win_ratio,
                                'profit_weight': profit_weight,
                                'sell_price': target.get('sell_price', 0),
                                'profit': target.get('profit', 0),
                                'profit_rate': profit_rate
                            })
                
                # 记录这只股票的平仓汇总
                if stock_exit_count > 0:
                    stock_exit_summary.append({
                        'stock_id': stock_id,
                        'exit_count': stock_exit_count,
                        'details': stock_exit_details
                    })
                        
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
    
    # 输出分析结果
    print("=== 平仓分布分析（包括动态止损）===")
    print(f"总投资次数: {total_investments}")
    print(f"总平仓次数: {total_exits}")
    print(f"平均每投资平仓次数: {total_exits/total_investments:.2f}")
    print()
    
    print("平仓类型分布:")
    print("类型 | 次数 | 占比")
    print("-" * 25)
    for exit_type in sorted(exit_distribution.keys()):
        count = exit_distribution[exit_type]
        percentage = count / total_exits * 100 if total_exits > 0 else 0
        print(f"{exit_type:8s} | {count:4d} | {percentage:5.1f}%")
    
    print()
    print("动态止损详细分析:")
    print("股票代码 | 收益率 | 权重 | 卖出价格")
    print("-" * 50)
    
    # 按收益率排序
    dynamic_stop_details.sort(key=lambda x: x['profit_rate'], reverse=True)
    
    for detail in dynamic_stop_details:
        print(f"{detail['stock_id']} | {detail['profit_rate']*100:6.1f}% | {detail['profit_weight']:6.3f} | {detail['sell_price']:8.2f}")
    
    print()
    print("动态止损统计:")
    if dynamic_stop_details:
        profit_rates = [d['profit_rate'] for d in dynamic_stop_details]
        avg_profit_rate = sum(profit_rates) / len(profit_rates)
        max_profit_rate = max(profit_rates)
        min_profit_rate = min(profit_rates)
        
        print(f"动态止损次数: {len(dynamic_stop_details)}")
        print(f"平均收益率: {avg_profit_rate*100:.2f}%")
        print(f"最高收益率: {max_profit_rate*100:.2f}%")
        print(f"最低收益率: {min_profit_rate*100:.2f}%")
        
        # 统计正收益和负收益
        positive_count = len([r for r in profit_rates if r > 0])
        negative_count = len([r for r in profit_rates if r < 0])
        print(f"正收益次数: {positive_count}")
        print(f"负收益次数: {negative_count}")
        print(f"正收益比例: {positive_count/len(profit_rates)*100:.1f}%")

if __name__ == "__main__":
    analyze_take_profit_distribution()
