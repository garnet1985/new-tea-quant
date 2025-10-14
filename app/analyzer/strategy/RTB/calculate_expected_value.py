#!/usr/bin/env python3
"""
计算不同策略的数学期望值
并分析动态追损的仓位问题
"""
import sys
import os
import json
import glob
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from datetime import datetime

def calculate_expected_value():
    """计算不同策略的数学期望值"""
    
    print("="*80)
    print("数学期望值分析")
    print("="*80)
    
    # 找到最新的两个tmp目录进行对比
    tmp_dirs = glob.glob("/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_*")
    if len(tmp_dirs) < 2:
        print("❌ 需要至少两个版本的数据进行对比")
        return
    
    # 获取最新的两个版本
    latest_dirs = sorted(tmp_dirs, key=os.path.getctime)[-2:]
    v7_4_dir = latest_dirs[0]  # v0.7.4 (V8)
    v9_dir = latest_dirs[1]    # V9
    
    print(f"📁 v0.7.4目录: {v7_4_dir}")
    print(f"📁 V9目录: {v9_dir}")
    
    # 分析两个版本
    versions = {
        'v0.7.4': v7_4_dir,
        'V9': v9_dir
    }
    
    results = {}
    
    for version_name, version_dir in versions.items():
        print(f"\n📊 分析版本: {version_name}")
        
        # 读取所有投资记录
        all_investments = []
        json_files = glob.glob(os.path.join(version_dir, "*.json"))
        
        for json_file in json_files:
            if json_file.endswith("session_summary.json"):
                continue
                
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if isinstance(data, list):
                all_investments.extend(data)
            elif isinstance(data, dict) and 'investments' in data:
                all_investments.extend(data['investments'])
        
        if not all_investments:
            print(f"❌ {version_name} 没有找到投资记录")
            continue
        
        # 分析投资结果
        df = pd.DataFrame(all_investments)
        
        # 重命名列以匹配我们的分析
        if 'overall_profit_rate' in df.columns:
            df['roi'] = df['overall_profit_rate']
        if 'duration_in_days' in df.columns:
            df['days'] = df['duration_in_days']
        
        # 计算基本统计
        total_investments = len(df)
        wins = len(df[df['roi'] > 0])
        losses = len(df[df['roi'] <= 0])
        
        win_rate = wins / total_investments if total_investments > 0 else 0
        loss_rate = losses / total_investments if total_investments > 0 else 0
        
        # 计算平均收益和损失
        winning_trades = df[df['roi'] > 0]
        losing_trades = df[df['roi'] <= 0]
        
        avg_win = winning_trades['roi'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['roi'].mean() if len(losing_trades) > 0 else 0
        
        # 计算数学期望值
        expected_value = (win_rate * avg_win) + (loss_rate * avg_loss)
        
        # 计算年化期望值
        avg_days = df['days'].mean()
        annualized_expected = expected_value * (365 / avg_days) if avg_days > 0 else 0
        
        # 计算Kelly准则
        if avg_loss != 0:
            kelly_fraction = (win_rate * avg_win - loss_rate * abs(avg_loss)) / abs(avg_loss)
        else:
            kelly_fraction = 0
        
        results[version_name] = {
            'total_investments': total_investments,
            'win_rate': win_rate,
            'loss_rate': loss_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expected_value': expected_value,
            'annualized_expected': annualized_expected,
            'kelly_fraction': kelly_fraction,
            'avg_days': avg_days
        }
        
        print(f"  总投资次数: {total_investments}")
        print(f"  胜率: {win_rate*100:.1f}%")
        print(f"  败率: {loss_rate*100:.1f}%")
        print(f"  平均盈利: {avg_win*100:.1f}%")
        print(f"  平均亏损: {avg_loss*100:.1f}%")
        print(f"  数学期望值: {expected_value*100:.2f}%")
        print(f"  年化期望值: {annualized_expected*100:.1f}%")
        print(f"  Kelly准则: {kelly_fraction*100:.1f}%")
        print(f"  平均投资时长: {avg_days:.0f}天")
    
    # 对比分析
    if len(results) >= 2:
        print(f"\n🔍 版本对比分析:")
        
        v7_4 = results['v0.7.4']
        v9 = results['V9']
        
        print(f"  数学期望值对比:")
        print(f"    v0.7.4: {v7_4['expected_value']*100:.2f}%")
        print(f"    V9: {v9['expected_value']*100:.2f}%")
        print(f"    差异: {(v9['expected_value'] - v7_4['expected_value'])*100:.2f}%")
        
        print(f"  年化期望值对比:")
        print(f"    v0.7.4: {v7_4['annualized_expected']*100:.1f}%")
        print(f"    V9: {v9['annualized_expected']*100:.1f}%")
        print(f"    差异: {(v9['annualized_expected'] - v7_4['annualized_expected'])*100:.1f}%")
        
        print(f"  Kelly准则对比:")
        print(f"    v0.7.4: {v7_4['kelly_fraction']*100:.1f}%")
        print(f"    V9: {v9['kelly_fraction']*100:.1f}%")
        print(f"    差异: {(v9['kelly_fraction'] - v7_4['kelly_fraction'])*100:.1f}%")
        
        # 分析动态追损的仓位问题
        print(f"\n🎯 动态追损仓位分析:")
        print(f"  当前v0.7.4策略:")
        print(f"    10%档平50% (剩余50%)")
        print(f"    20%档平30% (剩余20%)")
        print(f"    30%档平20% (剩余0%)")
        print(f"  ⚠️  问题: 30%档后没有剩余仓位给动态追损！")
        
        print(f"\n💡 建议修正:")
        print(f"  方案1: 调整平仓比例")
        print(f"    10%档平40% (剩余60%)")
        print(f"    20%档平30% (剩余30%)")
        print(f"    30%档平20% (剩余10%) ← 给动态追损")
        
        print(f"  方案2: 增加40%档")
        print(f"    10%档平40% (剩余60%)")
        print(f"    20%档平30% (剩余30%)")
        print(f"    30%档平20% (剩余10%)")
        print(f"    40%档平10% (剩余0%) ← 给动态追损")

if __name__ == "__main__":
    calculate_expected_value()
