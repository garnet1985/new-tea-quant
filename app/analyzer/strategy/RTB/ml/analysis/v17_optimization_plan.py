#!/usr/bin/env python3
"""
V17优化策略规划
基于1797个投资记录的ML分析结果
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def create_v17_settings():
    """创建V17优化策略配置"""
    
    print("🚀 V17策略优化建议")
    print("=" * 50)
    
    print("\n📊 当前V16策略表现:")
    print("- 胜率: 57.8%")
    print("- ROI: 8.9%") 
    print("- 投资机会: 1925次")
    
    print("\n🎯 V17优化目标:")
    print("- 胜率: 60%+ (提升2.2%+)")
    print("- ROI: 10%+ (提升1.1%+)")
    print("- 投资机会: 增加更多")
    
    print("\n💡 基于ML分析的优化建议:")
    
    print("\n1️⃣ MA收敛度优化:")
    print("   当前阈值: 0.09")
    print("   建议阈值: 0.12")
    print("   理由: 中等收敛(0.08-0.12)成功率60.32%，ROI 11.93%")
    print("   预期效果: 增加投资机会，提升胜率和ROI")
    
    print("\n2️⃣ 历史分位数优化:")
    print("   当前阈值: 0.35")
    print("   建议阈值: 0.2")
    print("   理由: 很低分位(0-0.2)成功率59.94%，ROI 11.65%")
    print("   预期效果: 更精准的买入时机，提升胜率")
    
    print("\n3️⃣ RSI条件优化:")
    print("   当前阈值: 70")
    print("   建议阈值: 65")
    print("   理由: RSI重要性中等，适度收紧可提升信号质量")
    print("   预期效果: 提升胜率")
    
    print("\n4️⃣ 其他条件保持:")
    print("   - MA20/MA60斜率: 保持当前范围(-0.1, 0.1)")
    print("   - 成交量确认: 保持当前阈值0.8")
    print("   - 震荡位置: 保持当前阈值0.5")
    
    # 生成V17 settings配置
    v17_settings = {
        "ma_convergence_threshold": 0.12,  # 从0.09放宽到0.12
        "historical_percentile_threshold": 0.2,  # 从0.35收紧到0.2
        "rsi_threshold": 65,  # 从70收紧到65
        "ma_slope_range": (-0.1, 0.1),  # 保持
        "volume_confirmation_threshold": 0.8,  # 保持
        "oscillation_position_threshold": 0.5,  # 保持
    }
    
    print("\n🔧 V17策略参数:")
    for key, value in v17_settings.items():
        print(f"   {key}: {value}")
    
    print("\n📈 预期效果:")
    print("   胜率: 57.8% → 60%+")
    print("   ROI: 8.9% → 10%+")
    print("   投资机会: 1925次 → 增加")
    
    return v17_settings

def implement_v17_changes():
    """实施V17优化"""
    print("\n🛠️ 实施V17优化的步骤:")
    print("1. 更新RTB.py中的_check_optimized_conditions方法")
    print("2. 更新settings.py中的相关阈值")
    print("3. 运行测试验证效果")
    print("4. 如果效果好，进行完整模拟")

if __name__ == "__main__":
    v17_settings = create_v17_settings()
    implement_v17_changes()
