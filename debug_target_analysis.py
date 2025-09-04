#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings

def debug_target_analysis():
    """调试target_win_ratio分析"""
    base_dir = "app/analyzer/strategy/historicLow/tmp/2025_09_04-326"
    
    # 读取第一个JSON文件
    json_files = [f for f in os.listdir(base_dir) if f.endswith('.json')]
    if not json_files:
        print("没有找到JSON文件")
        return
    
    first_file = os.path.join(base_dir, json_files[0])
    with open(first_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"分析文件: {json_files[0]}")
    print("=" * 50)
    
    # 分析第一个投资记录
    if 'results' in data and len(data['results']) > 0:
        first_result = data['results'][0]
        print(f"股票: {first_result.get('stock_info', {}).get('id', 'Unknown')}")
        print(f"投资状态: {first_result.get('status', 'Unknown')}")
        print(f"总收益: {first_result.get('profit', 0):.4f}")
        print(f"收益率: {first_result.get('overall_profit_rate', 0)*100:.2f}%")
        
        # 分析targets
        targets = first_result.get('investment', {}).get('targets', [])
        print(f"\n共有 {len(targets)} 个targets:")
        
        for i, target in enumerate(targets):
            if target.get('is_achieved', False):
                target_win_ratio = target.get('target_win_ratio', 0)
                profit_rate = target.get('profit_rate', 0)
                profit_weight = target.get('profit_weight', 0)
                sell_price = target.get('sell_price', 0)
                
                print(f"\nTarget {i+1}:")
                print(f"  target_win_ratio: {target_win_ratio} (类型: {type(target_win_ratio)})")
                print(f"  profit_rate: {profit_rate:.6f}")
                print(f"  profit_weight: {profit_weight:.6f}")
                print(f"  sell_price: {sell_price:.4f}")
                
                # 判断交易类型
                trade_type = "未知"
                if target_win_ratio == -0.2:
                    trade_type = "止损"
                elif target_win_ratio == 0:
                    trade_type = "止损"
                elif target_win_ratio == 'dynamic':
                    trade_type = "动态止损"
                elif isinstance(target_win_ratio, (int, float)) and target_win_ratio > 0:
                    # 检查是否是动态止损
                    is_dynamic = False
                    for stage in strategy_settings["goal"]["stop_loss"]["stages"]:
                        if stage.get("is_dynamic_loss", False) and abs(stage.get("win_ratio", 0) - target_win_ratio) < 0.001:
                            is_dynamic = True
                            break
                    if is_dynamic:
                        trade_type = "动态止损"
                    else:
                        trade_type = f"{target_win_ratio*100:.0f}%止盈"
                
                print(f"  判断的交易类型: {trade_type}")
                
                # 检查策略设置
                if isinstance(target_win_ratio, (int, float)) and target_win_ratio > 0:
                    print("  检查策略设置:")
                    for stage in strategy_settings["goal"]["take_profit"]["stages"]:
                        if abs(stage.get("win_ratio", 0) - target_win_ratio) < 0.001:
                            print(f"    找到匹配的止盈阶段: {stage.get('win_ratio')*100:.0f}% -> {stage.get('sell_ratio')*100:.0f}%")
                            break
                    else:
                        print(f"    未找到匹配的止盈阶段")
                    
                    for stage in strategy_settings["goal"]["stop_loss"]["stages"]:
                        if stage.get("is_dynamic_loss", False) and abs(stage.get("win_ratio", 0) - target_win_ratio) < 0.001:
                            print(f"    找到匹配的动态止损阶段: {stage.get('win_ratio')*100:.0f}% -> {stage.get('loss_ratio')*100:.0f}%")
                            break

if __name__ == "__main__":
    debug_target_analysis()
