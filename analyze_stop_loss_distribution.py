#!/usr/bin/env python3
"""
统计触发-20%止损的股票占比
分析第一个session结果中的止损情况
"""
import os
import json
from collections import defaultdict

def analyze_stop_loss_distribution():
    """分析止损分布情况"""
    base_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_04-314"
    
    # 统计变量
    total_stocks = 0
    stocks_with_20_percent_loss = 0
    stocks_with_any_loss = 0
    loss_distribution = defaultdict(int)  # 按止损比例统计
    stock_loss_details = []  # 每只股票的止损详情
    
    # 遍历所有JSON文件
    for filename in os.listdir(base_dir):
        if filename.endswith('.json') and filename != 'session_summary.json':
            filepath = os.path.join(base_dir, filename)
            stock_id = filename.replace('.json', '')
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                results = data.get('results', [])
                total_stocks += 1
                
                stock_has_loss = False
                stock_has_20_percent_loss = False
                stock_loss_rates = []
                
                for result in results:
                    targets = result.get('investment', {}).get('targets', [])
                    
                    # 统计这只股票的止损情况
                    for target in targets:
                        target_win_ratio = target.get('target_win_ratio')
                        is_achieved = target.get('is_achieved', False)
                        profit_rate = target.get('profit_rate', 0)
                        
                        # 检查是否是止损（负收益）
                        if is_achieved and profit_rate < 0:
                            stock_has_loss = True
                            stock_loss_rates.append(profit_rate)
                            
                            # 检查是否是-20%止损
                            if profit_rate <= -0.20:
                                stock_has_20_percent_loss = True
                            
                            # 统计止损分布
                            loss_range = f"{int(profit_rate*100)}%"
                            loss_distribution[loss_range] += 1
                
                # 记录这只股票的止损情况
                if stock_has_loss:
                    stocks_with_any_loss += 1
                    stock_loss_details.append({
                        'stock_id': stock_id,
                        'has_20_percent_loss': stock_has_20_percent_loss,
                        'loss_rates': stock_loss_rates
                    })
                
                if stock_has_20_percent_loss:
                    stocks_with_20_percent_loss += 1
                        
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
    
    # 输出分析结果
    print("=== 止损分布分析 ===")
    print(f"总股票数: {total_stocks}")
    print(f"有止损的股票数: {stocks_with_any_loss}")
    print(f"触发-20%止损的股票数: {stocks_with_20_percent_loss}")
    print()
    
    print("止损比例:")
    print(f"有止损股票占比: {stocks_with_any_loss/total_stocks*100:.2f}%")
    print(f"-20%止损股票占比: {stocks_with_20_percent_loss/total_stocks*100:.2f}%")
    print()
    
    print("止损档位分布:")
    print("档位 | 次数")
    print("-" * 15)
    for loss_range in sorted(loss_distribution.keys()):
        count = loss_distribution[loss_range]
        print(f"{loss_range:6s} | {count:4d}")
    
    print()
    print("触发-20%止损的股票:")
    for stock in stock_loss_details:
        if stock['has_20_percent_loss']:
            loss_str = ", ".join([f"{rate*100:.1f}%" for rate in stock['loss_rates']])
            print(f"{stock['stock_id']}: {loss_str}")

if __name__ == "__main__":
    analyze_stop_loss_distribution()
