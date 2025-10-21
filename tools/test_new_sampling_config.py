#!/usr/bin/env python3
"""
测试新的采样配置结构
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.analyzer.strategy.RTB.sampling_examples import *
from app.analyzer.components.simulator.services.preprocess_service import PreprocessService

def test_sampling_configs():
    """测试不同的采样配置"""
    
    print("🧪 测试新的采样配置结构")
    print("=" * 60)
    
    # 模拟股票列表
    stock_list = []
    for i in range(1000):
        if i < 400:
            stock_id = f"000{i:03d}.SZ"  # 深市主板
        elif i < 700:
            stock_id = f"300{i-400:03d}.SZ"  # 深市创业板
        else:
            stock_id = f"600{i-700:03d}.SH"  # 沪市主板
        
        stock_list.append({
            'id': stock_id,
            'name': f'股票{i:04d}'
        })
    
    print(f"总股票数: {len(stock_list)}")
    print()
    
    # 测试各种配置
    configs = [
        ("均匀采样", UNIFORM_SAMPLING_CONFIG),
        ("分层采样", STRATIFIED_SAMPLING_CONFIG),
        ("随机采样", RANDOM_SAMPLING_CONFIG),
        ("连续采样", CONTINUOUS_SAMPLING_CONFIG),
    ]
    
    for config_name, config in configs:
        print(f"📊 测试 {config_name}:")
        print("-" * 40)
        
        try:
            # 使用PreprocessService进行采样
            sampled_stocks = PreprocessService.get_stock_list(config)
            
            # 分析分布
            distribution = {}
            for stock in sampled_stocks:
                prefix = stock['id'][:3]
                distribution[prefix] = distribution.get(prefix, 0) + 1
            
            print(f"采样数量: {len(sampled_stocks)}")
            print("分布情况:")
            for prefix, count in sorted(distribution.items()):
                market_name = {
                    '000': '深市主板',
                    '300': '深市创业板',
                    '600': '沪市主板'
                }.get(prefix, prefix)
                print(f"  {market_name}: {count}只")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        
        print()

def demonstrate_config_switching():
    """演示如何切换配置"""
    
    print("🔄 配置切换演示")
    print("=" * 60)
    
    print("1. 切换到分层采样:")
    print("   修改 settings.py 中的 sampling 配置:")
    print("   'sampling': {")
    print("       'strategy': 'stratified',")
    print("       'stratified': {")
    print("           'seed': 123  # 可以改为其他值")
    print("       }")
    print("   }")
    print()
    
    print("2. 切换到随机采样:")
    print("   'sampling': {")
    print("       'strategy': 'random',")
    print("       'random': {")
    print("           'seed': 456  # 可以改为其他值")
    print("       }")
    print("   }")
    print()
    
    print("3. 切换到连续采样:")
    print("   'sampling': {")
    print("       'strategy': 'continuous',")
    print("       'continuous': {")
    print("           'start_idx': 100  # 可以改为其他值")
    print("       }")
    print("   }")
    print()

if __name__ == "__main__":
    test_sampling_configs()
    demonstrate_config_switching()
