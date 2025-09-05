#!/usr/bin/env python3
"""
分析模拟结果，统计直接止损(-0.2)的股票占比
"""
import os
import json
from typing import Dict, List, Any

def analyze_direct_stop_loss():
    """分析直接止损的情况"""
    base_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_04-319"
    
    direct_stop_loss_count = 0
    total_loss_count = 0
    total_investments = 0
    
    # 遍历所有JSON文件
    for filename in os.listdir(base_dir):
        if filename.endswith('.json') and filename != 'session_summary.json':
            filepath = os.path.join(base_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                results = data.get('results', [])
                for result in results:
                    total_investments += 1
                    
                    if result.get('status') == 'loss':
                        total_loss_count += 1
                        
                        # 检查是否是直接止损
                        targets = result.get('investment', {}).get('targets', [])
                        for target in targets:
                            target_name = target.get('name')
                            if isinstance(target_name, str) and target_name == "-20%":
                                direct_stop_loss_count += 1
                                print(f"直接止损: {filename} - target_name: {target_name}")
                                break
                                
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
    
    print(f"\n=== 直接止损分析结果 ===")
    print(f"总投资次数: {total_investments}")
    print(f"总亏损次数: {total_loss_count}")
    print(f"直接止损次数: {direct_stop_loss_count}")
    print(f"直接止损占亏损比例: {direct_stop_loss_count/total_loss_count*100:.2f}%" if total_loss_count > 0 else "0%")
    print(f"直接止损占总投资比例: {direct_stop_loss_count/total_investments*100:.2f}%")

def analyze_annual_return_trend():
    """分析年化收益率趋势"""
    print(f"\n=== 年化收益率趋势分析 ===")
    
    # 查看不同数据量的模拟结果
    sessions = [
        "2025_09_04-314",  # 大量数据(修复后)
        "2025_09_04-319",  # 最新数据(新增字段)
    ]
    
    for session in sessions:
        summary_file = f"app/analyzer/strategy/historicLow/tmp/{session}/session_summary.json"
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            total_investments = data.get('total_investments', 0)
            annual_return = data.get('annual_return', 0)
            win_rate = data.get('win_rate', 0)
            avg_roi = data.get('avg_roi', 0)
            
            print(f"{session}: 投资次数={total_investments}, 年化收益率={annual_return:.2f}%, 胜率={win_rate:.2f}%, 平均ROI={avg_roi:.2f}%")
            
        except Exception as e:
            print(f"无法读取 {session}: {e}")

if __name__ == "__main__":
    analyze_direct_stop_loss()
    analyze_annual_return_trend()
