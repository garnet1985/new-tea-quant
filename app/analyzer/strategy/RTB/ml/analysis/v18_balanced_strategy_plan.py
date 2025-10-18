#!/usr/bin/env python3
"""
V18平衡策略规划：财务筛选 + 技术条件放松
目标：在优质股票池中增加投资机会
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def create_v18_balanced_strategy():
    """创建V18平衡策略：财务筛选 + 技术放松"""
    
    print("🚀 V18平衡策略规划：财务筛选 + 技术放松")
    print("=" * 60)
    
    print("\n📊 策略设计理念:")
    print("1. 财务指标筛选：确保股票质量（市值、PE、PB、PS）")
    print("2. 技术条件放松：在优质股票池中增加投资机会")
    print("3. 平衡目标：质量与数量的平衡")
    
    print("\n🎯 V18平衡策略目标:")
    print("- 胜率: 58.9% → 60%+ (适度提升)")
    print("- ROI: 9.6% → 11%+ (适度提升)")
    print("- 投资机会: 1751次 → 2000-2500次 (显著增加)")
    print("- 整体效果: 质量提升 + 机会增加")
    
    print("\n💡 V18核心策略设计:")
    
    print("\n1️⃣ 财务指标筛选（确保质量）:")
    print("   市值筛选: market_cap > 30亿 (从50亿放宽)")
    print("   理由: 适度放宽，保留更多中等市值股票")
    print("   PE筛选: 15 < pe_ratio < 150 (从25-125放宽)")
    print("   理由: 避免过度筛选，保留成长股")
    print("   PB筛选: 0.3 < pb_ratio < 8 (从0.5-5放宽)")
    print("   理由: 保留更多估值合理的股票")
    print("   PS筛选: 0.5 < ps_ratio < 15 (从1-10放宽)")
    print("   理由: 适度放宽，增加机会")
    
    print("\n2️⃣ 技术条件放松（增加机会）:")
    print("   MA收敛度: < 0.15 (从0.10放宽)")
    print("   理由: 在优质股票池中允许更宽松的收敛条件")
    print("   历史分位数: < 0.4 (从0.3放宽)")
    print("   理由: 增加买入机会")
    print("   RSI: < 70 (从65放宽)")
    print("   理由: 避免过度筛选")
    print("   成交量确认: > 0.7 (从0.8放宽)")
    print("   理由: 适度放松成交量要求")
    
    print("\n3️⃣ 预期效果分析:")
    print("   财务筛选效果:")
    print("   - 过滤掉约30-40%的低质量股票")
    print("   - 剩余股票池质量显著提升")
    print("   技术放松效果:")
    print("   - 在优质股票池中增加约40-60%的机会")
    print("   - 整体投资机会增加约20-40%")
    
    print("\n4️⃣ 策略逻辑:")
    print("   第一步: 财务筛选（质量门控）")
    print("   - 确保股票基本面健康")
    print("   - 排除异常估值股票")
    print("   第二步: 技术筛选（机会识别）")
    print("   - 在优质股票池中寻找技术机会")
    print("   - 适度放松条件以增加机会")
    
    # 生成V18平衡策略配置
    v18_balanced_config = {
        "strategy_version": "V18_Balanced_Optimized",
        "financial_filters": {
            "market_cap_min": 300000,  # 30亿（万元）
            "pe_ratio_min": 15,
            "pe_ratio_max": 150,
            "pb_ratio_min": 0.3,
            "pb_ratio_max": 8.0,
            "ps_ratio_min": 0.5,
            "ps_ratio_max": 15.0
        },
        "technical_conditions": {
            "ma_convergence": 0.15,  # 从0.10放宽到0.15
            "historical_percentile": 0.4,  # 从0.3放宽到0.4
            "rsi_signal": 70,  # 从65放宽到70
            "volume_confirmation": 0.7,  # 从0.8放宽到0.7
            "ma20_slope_min": -0.05,  # 保持
            "ma60_slope_min": -0.05,  # 保持
            "volume_trend_min": -0.3,  # 保持
            "amount_ratio_min": 0.7,  # 保持
            "oscillation_position": 0.5  # 保持
        }
    }
    
    print("\n🔧 V18平衡策略配置:")
    for key, value in v18_balanced_config.items():
        print(f"   {key}: {value}")
    
    return v18_balanced_config

def analyze_expected_impact():
    """分析预期影响"""
    print("\n📈 预期影响分析:")
    
    print("\n1️⃣ 财务筛选影响:")
    print("   市值筛选 (>30亿): 可能过滤20-25%的股票")
    print("   PE筛选 (15-150): 可能过滤10-15%的股票")
    print("   PB筛选 (0.3-8): 可能过滤5-10%的股票")
    print("   PS筛选 (0.5-15): 可能过滤5-10%的股票")
    print("   综合影响: 约30-40%的股票被过滤")
    
    print("\n2️⃣ 技术条件放松影响:")
    print("   MA收敛度放宽 (0.10→0.15): 增加约30-40%机会")
    print("   历史分位数放宽 (0.3→0.4): 增加约20-30%机会")
    print("   RSI放宽 (65→70): 增加约15-20%机会")
    print("   成交量确认放宽 (0.8→0.7): 增加约10-15%机会")
    print("   综合影响: 在筛选后股票池中增加约40-60%机会")
    
    print("\n3️⃣ 净效果:")
    print("   股票池减少: 30-40%")
    print("   单股机会增加: 40-60%")
    print("   净机会变化: +20% to +40%")
    print("   总机会: 1751 × 1.2-1.4 = 2100-2450次")
    
    print("\n4️⃣ 质量预期:")
    print("   胜率: 58.9% → 60-62% (适度提升)")
    print("   ROI: 9.6% → 10-12% (适度提升)")
    print("   原因: 财务筛选提升质量，技术放松适度降低质量")

def implement_v18_balanced():
    """实施V18平衡策略的具体步骤"""
    print("\n🛠️ 实施V18平衡策略步骤:")
    
    print("\n步骤1: 修改RTB.py")
    print("   1.1 添加_get_financial_indicators()方法")
    print("   1.2 在_check_optimized_conditions()中添加财务筛选")
    print("   1.3 调整技术条件阈值（放宽）")
    print("   1.4 更新strategy_version为'V18_Balanced_Optimized'")
    
    print("\n步骤2: 修改settings.py")
    print("   2.1 更新is_enabled注释为'V18平衡优化版启用'")
    print("   2.2 更新simulation_ref_version为'V18_Balanced_Optimized'")
    
    print("\n步骤3: 测试验证")
    print("   3.1 运行小规模测试（100只股票）")
    print("   3.2 验证财务筛选是否正常工作")
    print("   3.3 检查机会数量是否增加")
    print("   3.4 检查胜率和ROI是否保持或提升")
    
    print("\n步骤4: 完整模拟")
    print("   4.1 如果测试效果好，运行完整模拟")
    print("   4.2 对比V17和V18的表现差异")
    print("   4.3 记录优化效果")
    
    print("\n步骤5: 进一步优化")
    print("   5.1 如果机会还不够，继续适当放宽技术条件")
    print("   5.2 如果质量下降，适当收紧财务条件")
    print("   5.3 找到最佳平衡点")

if __name__ == "__main__":
    v18_config = create_v18_balanced_strategy()
    analyze_expected_impact()
    implement_v18_balanced()
    
    print("\n🎉 V18平衡策略规划完成！")
    print("核心理念：财务筛选确保质量，技术放松增加机会")
    print("预期结果：质量提升 + 机会增加 = 更好的整体表现")
