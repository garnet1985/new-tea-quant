#!/usr/bin/env python3
"""
V18财务指标优化策略规划
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def create_v18_strategy():
    """创建V18财务指标优化策略"""
    
    print("🚀 V18财务指标优化策略规划")
    print("=" * 60)
    
    print("\n📊 基于264个投资记录的财务ML分析结果:")
    print("财务指标重要性排名:")
    print("1. 市值对数: 0.0191 (最重要)")
    print("2. PB比率: 0.0137")
    print("3. PS比率: 0.0134")
    print("4. 成交量比率: 0.0135")
    print("5. 换手率: 0.0111")
    print("6. PE比率: 0.0109")
    
    print("\n🎯 V18优化目标:")
    print("- 胜率: 58.9% → 62%+ (提升3%+)")
    print("- ROI: 9.6% → 12%+ (提升2.4%+)")
    print("- 投资机会: 保持1751次或适度增加")
    
    print("\n💡 V18核心优化策略:")
    
    print("\n1️⃣ 财务指标筛选（新增）:")
    print("   市值筛选: market_cap > 50亿")
    print("   理由: 高于50分位阈值的股票胜率62.12%，ROI 11.33%")
    print("   PE筛选: 25 < pe_ratio < 125")
    print("   理由: 此范围内股票胜率66.40%，ROI 12.08%")
    print("   PB筛选: 0.5 < pb_ratio < 5")
    print("   理由: 高于50分位阈值的股票胜率61.83%，ROI 11.74%")
    print("   PS筛选: 1 < ps_ratio < 10")
    print("   理由: 75分位阈值内股票胜率64.62%，ROI 13.95%")
    
    print("\n2️⃣ 技术指标保持V17设置:")
    print("   MA收敛度: < 0.10")
    print("   历史分位数: < 0.3")
    print("   RSI: < 65")
    print("   其他条件保持不变")
    
    print("\n3️⃣ 预期效果:")
    print("   胜率提升: 58.9% → 62%+")
    print("   ROI提升: 9.6% → 12%+")
    print("   投资机会: 可能减少20-30%（因为筛选更严格）")
    print("   整体质量: 显著提升")
    
    print("\n4️⃣ 实施步骤:")
    print("   1. 在RTB.py中添加财务指标获取函数")
    print("   2. 在_check_optimized_conditions中添加财务筛选条件")
    print("   3. 更新settings.py配置")
    print("   4. 运行测试验证效果")
    print("   5. 如果效果好，进行完整模拟")
    
    # 生成V18策略配置
    v18_config = {
        "strategy_version": "V18_Financial_Optimized",
        "financial_filters": {
            "market_cap_min": 500000,  # 50亿（万元）
            "pe_ratio_min": 25,
            "pe_ratio_max": 125,
            "pb_ratio_min": 0.5,
            "pb_ratio_max": 5.0,
            "ps_ratio_min": 1.0,
            "ps_ratio_max": 10.0
        },
        "technical_conditions": {
            "ma_convergence": 0.10,
            "historical_percentile": 0.3,
            "rsi_signal": 65
        }
    }
    
    print("\n🔧 V18策略配置:")
    for key, value in v18_config.items():
        print(f"   {key}: {value}")
    
    return v18_config

def implement_v18_changes():
    """实施V18优化的具体步骤"""
    print("\n🛠️ 实施V18优化的具体步骤:")
    
    print("\n步骤1: 修改RTB.py")
    print("   添加_get_financial_indicators()方法")
    print("   在_check_optimized_conditions()中添加财务筛选")
    print("   更新strategy_version为'V18_Financial_Optimized'")
    
    print("\n步骤2: 修改settings.py")
    print("   更新is_enabled注释为'V18财务指标优化版启用'")
    print("   更新simulation_ref_version为'V18_Financial_Optimized'")
    
    print("\n步骤3: 测试验证")
    print("   运行小规模测试（50只股票）")
    print("   验证财务筛选是否正常工作")
    print("   检查胜率和ROI是否有提升")
    
    print("\n步骤4: 完整模拟")
    print("   如果测试效果好，运行完整模拟")
    print("   对比V17和V18的表现差异")
    print("   记录优化效果")

if __name__ == "__main__":
    v18_config = create_v18_strategy()
    implement_v18_changes()
    
    print("\n🎉 V18策略规划完成！")
    print("建议立即开始实施财务指标筛选优化。")
