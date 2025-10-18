#!/usr/bin/env python3
"""
V18财务指标深度分析：找出正确的财务筛选参数组合
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def analyze_financial_impact():
    """分析财务指标对策略表现的影响"""
    print("🔍 V18财务指标深度分析")
    print("=" * 60)
    
    print("\n📊 问题分析:")
    print("1. 财务筛选降低了胜率：58.9% → 47.9% (-11%)")
    print("2. 财务筛选降低了ROI：9.6% → 5.0% (-4.6%)")
    print("3. 说明当前财务筛选条件过滤掉了优质机会")
    
    print("\n🎯 优化方向:")
    print("1. 动态财务筛选：根据行业/市场环境调整阈值")
    print("2. 分层筛选：不同市值使用不同标准")
    print("3. 相对筛选：基于历史分位数而非绝对值")
    print("4. 组合筛选：财务+技术综合评分")
    
    print("\n💡 具体优化方案:")
    
    print("\n方案A: 分层市值筛选")
    print("- 大盘股(>100亿): 严格财务筛选")
    print("- 中盘股(30-100亿): 适度财务筛选") 
    print("- 小盘股(<30亿): 宽松财务筛选或跳过")
    
    print("\n方案B: 动态阈值筛选")
    print("- PE筛选: 基于行业PE中位数±2倍标准差")
    print("- PB筛选: 基于历史PB分位数(20%-80%)")
    print("- 市值筛选: 基于市场整体估值调整")
    
    print("\n方案C: 相对筛选")
    print("- 行业相对估值: PE/PB相对行业均值")
    print("- 历史相对估值: 相对自身历史分位数")
    print("- 市场相对估值: 相对市场整体水平")
    
    print("\n方案D: 综合评分筛选")
    print("- 技术面评分: 基于现有技术指标")
    print("- 财务面评分: 基于财务健康度")
    print("- 综合评分: 技术60% + 财务40%")
    
    print("\n🔬 实验建议:")
    print("1. 先测试完全移除财务筛选的V18.1")
    print("2. 测试分层筛选的V18.2") 
    print("3. 测试动态阈值的V18.3")
    print("4. 测试综合评分的V18.4")
    
    print("\n📈 预期效果:")
    print("- V18.1: 胜率恢复到55%+, ROI恢复到8%+")
    print("- V18.2: 在保持质量的同时增加机会")
    print("- V18.3: 适应不同市场环境")
    print("- V18.4: 找到技术与财务的最佳平衡")

def create_v18_1_no_financial():
    """创建V18.1：完全移除财务筛选"""
    print("\n🚀 创建V18.1策略：移除财务筛选")
    print("目标：验证财务筛选是否必要")
    
    config = {
        "strategy_version": "V18.1_No_Financial",
        "changes": [
            "完全移除财务指标筛选",
            "保持V18.5的技术条件优化",
            "预期：胜率55%+, ROI 8%+"
        ],
        "technical_conditions": {
            "ma_convergence": "< 0.20",
            "ma20_slope": "> -0.10", 
            "ma60_slope": "> -0.10",
            "volume_trend": "> -0.5",
            "amount_ratio": "> 0.6",
            "historical_percentile": "< 0.5",
            "oscillation_position": "< 0.6",
            "volume_confirmation": "> 0.6",
            "rsi_signal": "< 75"
        }
    }
    
    print(f"V18.1配置: {config}")
    return config

def create_v18_2_tiered_screening():
    """创建V18.2：分层市值筛选"""
    print("\n🚀 创建V18.2策略：分层市值筛选")
    print("目标：不同市值使用不同筛选标准")
    
    config = {
        "strategy_version": "V18.2_Tiered_Screening",
        "tiered_financial_conditions": {
            "large_cap": {  # >100亿
                "market_cap_min": 1000000,
                "pe_range": [10, 150],
                "pb_range": [0.5, 8],
                "ps_range": [0.5, 15]
            },
            "mid_cap": {  # 30-100亿
                "market_cap_min": 300000,
                "market_cap_max": 1000000,
                "pe_range": [5, 200],
                "pb_range": [0.3, 10],
                "ps_range": [0.3, 20]
            },
            "small_cap": {  # <30亿
                "market_cap_max": 300000,
                "pe_range": [0, 500],  # 几乎不筛选
                "pb_range": [0.1, 50],
                "ps_range": [0.1, 100]
            }
        }
    }
    
    print(f"V18.2配置: {config}")
    return config

def create_v18_3_dynamic_screening():
    """创建V18.3：动态阈值筛选"""
    print("\n🚀 创建V18.3策略：动态阈值筛选")
    print("目标：基于市场环境动态调整筛选标准")
    
    config = {
        "strategy_version": "V18.3_Dynamic_Screening",
        "dynamic_conditions": {
            "market_cap_min": 200000,  # 基础市值要求
            "pe_screening": "基于行业PE中位数±2倍标准差",
            "pb_screening": "基于历史PB分位数(20%-80%)",
            "adaptive_thresholds": True
        }
    }
    
    print(f"V18.3配置: {config}")
    return config

def create_v18_4_composite_scoring():
    """创建V18.4：综合评分筛选"""
    print("\n🚀 创建V18.4策略：综合评分筛选")
    print("目标：技术与财务综合评分")
    
    config = {
        "strategy_version": "V18.4_Composite_Scoring",
        "scoring_weights": {
            "technical_score": 0.6,  # 技术面权重60%
            "financial_score": 0.4   # 财务面权重40%
        },
        "composite_threshold": 0.7,  # 综合评分阈值
        "scoring_components": {
            "technical": [
                "ma_convergence", "ma_slopes", "volume_trend",
                "historical_percentile", "rsi_signal"
            ],
            "financial": [
                "market_cap_rank", "pe_industry_rank", 
                "pb_historical_rank", "ps_market_rank"
            ]
        }
    }
    
    print(f"V18.4配置: {config}")
    return config

def implementation_roadmap():
    """实施路线图"""
    print("\n🗺️ 实施路线图:")
    print("=" * 60)
    
    print("\n阶段1: 验证假设 (V18.1)")
    print("- 完全移除财务筛选")
    print("- 测试：胜率是否恢复到55%+")
    print("- 预期：确认财务筛选的影响")
    
    print("\n阶段2: 分层优化 (V18.2)")
    print("- 实现分层市值筛选")
    print("- 测试：不同市值的表现差异")
    print("- 预期：在质量与机会间找到平衡")
    
    print("\n阶段3: 动态优化 (V18.3)")
    print("- 实现动态阈值筛选")
    print("- 测试：适应不同市场环境")
    print("- 预期：提升策略的适应性")
    
    print("\n阶段4: 综合优化 (V18.4)")
    print("- 实现综合评分筛选")
    print("- 测试：技术与财务的最佳组合")
    print("- 预期：找到最优的平衡点")

if __name__ == "__main__":
    analyze_financial_impact()
    create_v18_1_no_financial()
    create_v18_2_tiered_screening()
    create_v18_3_dynamic_screening()
    create_v18_4_composite_scoring()
    implementation_roadmap()
    
    print("\n🎉 V18财务指标深度分析完成！")
    print("建议：从V18.1开始，逐步验证和优化")
