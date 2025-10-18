#!/usr/bin/env python3
"""
V18.2平衡策略：分层财务筛选 + 优化技术条件
目标：在V17质量基础上增加投资机会
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def analyze_v17_vs_v18_1():
    """分析V17 vs V18.1的差异"""
    print("📊 V17 vs V18.1 策略对比分析")
    print("=" * 60)
    
    print("\n📈 关键指标对比:")
    print("V17策略:")
    print("  胜率: 57.8%")
    print("  平均ROI: 8.9%")
    print("  年化收益: ~24.0%")
    print("  投资次数: 1,751次")
    print("  特点: 高质量，机会较少")
    
    print("\nV18.1策略:")
    print("  胜率: 51.2% (-6.6%)")
    print("  平均ROI: 6.2% (-2.7%)")
    print("  年化收益: 18.1% (-5.9%)")
    print("  投资次数: 16,000次 (+814%)")
    print("  特点: 低质量，机会很多")
    
    print("\n🎯 V18.2目标:")
    print("  胜率: 55-58% (接近V17)")
    print("  平均ROI: 7-9% (接近V17)")
    print("  年化收益: 20-25% (接近V17)")
    print("  投资次数: 3,000-5,000次 (比V17多2-3倍)")

def design_v18_2_strategy():
    """设计V18.2平衡策略"""
    print("\n🚀 V18.2平衡策略设计")
    print("=" * 60)
    
    print("\n💡 核心思路:")
    print("1. 分层财务筛选：不同市值使用不同标准")
    print("2. 适度放宽技术条件：在质量基础上增加机会")
    print("3. 质量优先：宁可机会少一些，也要保证质量")
    
    print("\n📋 V18.2策略配置:")
    
    print("\n1️⃣ 分层财务筛选:")
    print("  大盘股 (>100亿):")
    print("    市值: >100亿")
    print("    PE: 8-80 (相对宽松)")
    print("    PB: 0.5-8")
    print("    PS: 0.5-15")
    print("    理由: 大盘股相对稳定，可以适当放宽")
    
    print("\n  中盘股 (30-100亿):")
    print("    市值: 30-100亿")
    print("    PE: 10-100 (适度宽松)")
    print("    PB: 0.3-10")
    print("    PS: 0.3-20")
    print("    理由: 中盘股成长性好，但风险适中")
    
    print("\n  小盘股 (<30亿):")
    print("    市值: <30亿")
    print("    PE: 5-150 (相对宽松)")
    print("    PB: 0.2-15")
    print("    PS: 0.2-25")
    print("    理由: 小盘股成长潜力大，但风险较高")
    
    print("\n2️⃣ 优化技术条件:")
    print("  MA收敛度: <0.18 (从0.20适度收紧)")
    print("  历史分位数: <0.45 (从0.50适度收紧)")
    print("  RSI: <72 (从75适度收紧)")
    print("  成交量确认: >0.65 (从0.60适度收紧)")
    print("  理由: 在保证机会的基础上提升质量")
    
    print("\n3️⃣ 预期效果:")
    print("  投资机会: 3,000-5,000次 (比V17多2-3倍)")
    print("  胜率: 55-58% (接近V17水平)")
    print("  平均ROI: 7-9% (接近V17水平)")
    print("  年化收益: 20-25% (接近V17水平)")

def implementation_plan():
    """实施计划"""
    print("\n🗺️ V18.2实施计划")
    print("=" * 60)
    
    print("\n阶段1: 实现分层财务筛选")
    print("1. 修改_check_financial_conditions方法")
    print("2. 根据市值分层应用不同筛选标准")
    print("3. 测试分层筛选效果")
    
    print("\n阶段2: 优化技术条件")
    print("1. 适度收紧技术条件阈值")
    print("2. 平衡质量与数量")
    print("3. 测试优化效果")
    
    print("\n阶段3: 验证V18.2效果")
    print("1. 运行完整模拟")
    print("2. 对比V17、V18.1、V18.2表现")
    print("3. 确认达到目标指标")
    
    print("\n🎯 成功标准:")
    print("- 胜率: ≥55% (接近V17的57.8%)")
    print("- ROI: ≥7% (接近V17的8.9%)")
    print("- 投资机会: ≥3,000次 (比V17多2倍以上)")
    print("- 年化收益: ≥20% (接近V17的24%)")

def create_v18_2_config():
    """创建V18.2配置"""
    config = {
        "strategy_version": "V18.2_Balanced",
        "tiered_financial_screening": {
            "large_cap": {
                "market_cap_min": 1000000,  # 100亿
                "pe_range": [8, 80],
                "pb_range": [0.5, 8],
                "ps_range": [0.5, 15]
            },
            "mid_cap": {
                "market_cap_min": 300000,   # 30亿
                "market_cap_max": 1000000,  # 100亿
                "pe_range": [10, 100],
                "pb_range": [0.3, 10],
                "ps_range": [0.3, 20]
            },
            "small_cap": {
                "market_cap_max": 300000,   # 30亿
                "pe_range": [5, 150],
                "pb_range": [0.2, 15],
                "ps_range": [0.2, 25]
            }
        },
        "optimized_technical_conditions": {
            "ma_convergence": 0.18,      # 从0.20收紧
            "historical_percentile": 0.45,  # 从0.50收紧
            "rsi_signal": 72,            # 从75收紧
            "volume_confirmation": 0.65,    # 从0.60收紧
            "oscillation_position": 0.55,   # 从0.60收紧
        }
    }
    
    print(f"\n🔧 V18.2配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    return config

if __name__ == "__main__":
    analyze_v17_vs_v18_1()
    design_v18_2_strategy()
    implementation_plan()
    create_v18_2_config()
    
    print("\n🎉 V18.2平衡策略规划完成！")
    print("目标：在V17质量基础上，将投资机会增加2-3倍")
