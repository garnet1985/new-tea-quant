#!/usr/bin/env python3
"""
RTB策略采样配置示例
展示如何使用不同的采样策略
"""

# 示例1: 均匀间隔采样（推荐用于生产环境）
UNIFORM_SAMPLING_CONFIG = {
    'mode': {
        "test_amount": 500,
        "simulation_ref_version": "V19.0_Uniform_Sampling",
    },
    'sampling': {
        "strategy": "uniform",
        "uniform": {
            "description": "均匀间隔采样，分布均匀，结果可重现"
        }
    }
}

# 示例2: 分层采样（推荐用于研究对比）
STRATIFIED_SAMPLING_CONFIG = {
    'mode': {
        "test_amount": 500,
        "simulation_ref_version": "V19.0_Stratified_Sampling",
    },
    'sampling': {
        "strategy": "stratified",
        "stratified": {
            "seed": 42,  # 可以改为其他值如123, 456等
            "description": "按市场分层采样，科学合理，依赖seed"
        }
    }
}

# 示例3: 随机采样（推荐用于快速测试）
RANDOM_SAMPLING_CONFIG = {
    'mode': {
        "test_amount": 500,
        "simulation_ref_version": "V19.0_Random_Sampling",
    },
    'sampling': {
        "strategy": "random",
        "random": {
            "seed": 42,  # 可以改为其他值如123, 456等
            "description": "完全随机采样，依赖seed保证可重现"
        }
    }
}

# 示例4: 连续采样（仅用于向后兼容，不推荐）
CONTINUOUS_SAMPLING_CONFIG = {
    'mode': {
        "test_amount": 500,
        "simulation_ref_version": "V19.0_Continuous_Sampling",
    },
    'sampling': {
        "strategy": "continuous",
        "continuous": {
            "start_idx": 0,  # 可以改为其他值如100, 200等
            "description": "连续采样，从start_idx开始取test_amount个"
        }
    }
}

# 示例5: 多种子对比研究配置
MULTI_SEED_RESEARCH_CONFIG = {
    'mode': {
        "test_amount": 500,
        "simulation_ref_version": "V19.0_Multi_Seed_Research",
    },
    'sampling': {
        "strategy": "stratified",
        "stratified": {
            "seed": 42,  # 研究时可以使用多个不同的seed值
            "description": "用于多种子对比研究，可以运行多次使用不同seed"
        }
    }
}

# 使用说明
USAGE_EXAMPLES = """
使用说明：

1. 生产环境推荐：
   - 使用 UNIFORM_SAMPLING_CONFIG
   - 结果稳定可重现，分布均匀

2. 研究对比推荐：
   - 使用 STRATIFIED_SAMPLING_CONFIG
   - 修改seed值（42, 123, 456等）进行多次实验
   - 对比不同样本的策略表现

3. 快速测试推荐：
   - 使用 RANDOM_SAMPLING_CONFIG
   - 简单直接，使用固定seed保证可重现

4. 向后兼容：
   - 使用 CONTINUOUS_SAMPLING_CONFIG
   - 不推荐，仅用于兼容旧版本

5. 多种子研究：
   - 使用 MULTI_SEED_RESEARCH_CONFIG
   - 修改seed值，运行多次实验
   - 分析不同样本的稳定性

配置方法：
1. 复制对应的配置到 settings.py
2. 根据需要调整 test_amount 和 seed 值
3. 运行模拟，观察采样分布和结果
"""
