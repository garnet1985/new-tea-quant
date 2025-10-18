#!/usr/bin/env python3
"""
测试V18.1策略：完全移除财务筛选
目标：验证财务筛选是否必要
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

from utils.db.db_manager import DatabaseManager
from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings

def test_v18_1_strategy():
    """测试V18.1策略：验证财务筛选的必要性"""
    print("🚀 测试V18.1策略：完全移除财务筛选")
    print("=" * 60)
    print("🎯 目标：验证财务筛选是否必要")
    print("📊 预期：胜率恢复到55%+, ROI恢复到8%+")
    print("")
    
    # 初始化数据库管理器
    db_manager = DatabaseManager()
    
    # 创建策略实例
    strategy = ReverseTrendBet(db_manager, settings)
    
    # 设置扫描范围：前100只股票
    strategy.set_scan_range(100, 0)
    
    # 执行扫描
    print("📊 开始扫描投资机会...")
    opportunities = strategy.scan()
    
    print(f"\n📈 V18.1策略扫描结果:")
    print(f"扫描股票数量: 100")
    print(f"发现投资机会: {len(opportunities)}")
    
    if opportunities:
        print(f"投资机会比例: {len(opportunities)/100*100:.1f}%")
        print(f"\n✅ V18.1策略成功发现投资机会！")
        
        # 显示前3个机会的详细信息
        print(f"\n📋 前3个投资机会详情:")
        for i, opp in enumerate(opportunities[:3]):
            print(f"\n机会 {i+1}:")
            print(f"  股票: {opp['stock']['id']} - {opp['stock']['name']}")
            print(f"  价格: {opp.get('record_of_today', {}).get('close', 'N/A')}")
            
            # 显示技术指标
            conditions = opp['extra_fields'].get('signal_conditions', {})
            print(f"  MA收敛度: {conditions.get('ma_convergence', 0):.4f}")
            print(f"  历史分位数: {conditions.get('historical_percentile', 0):.3f}")
            print(f"  RSI: {conditions.get('rsi_signal', 0):.1f}")
            print(f"  成交量确认: {conditions.get('volume_confirmation', 0):.3f}")
    else:
        print(f"\n❌ V18.1策略未发现投资机会")
        print(f"可能原因:")
        print(f"1. 技术条件仍然过于严格")
        print(f"2. 当前市场环境不适合")
    
    print(f"\n🎯 V18.1策略测试完成")
    print(f"💡 下一步：运行完整模拟验证胜率和ROI")

if __name__ == "__main__":
    test_v18_1_strategy()
