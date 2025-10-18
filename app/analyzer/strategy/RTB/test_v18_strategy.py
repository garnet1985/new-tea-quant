#!/usr/bin/env python3
"""
测试V18平衡策略
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

from utils.db.db_manager import DatabaseManager
from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings

def test_v18_strategy():
    """测试V18平衡策略"""
    print("🚀 测试V18平衡策略")
    print("=" * 50)
    
    # 初始化数据库管理器
    db_manager = DatabaseManager()
    
    # 创建策略实例
    strategy = ReverseTrendBet(db_manager, settings)
    
    # 设置扫描范围：前50只股票
    strategy.set_scan_range(50, 0)
    
    # 执行扫描
    print("📊 开始扫描投资机会...")
    opportunities = strategy.scan()
    
    print(f"\n📈 V18策略扫描结果:")
    print(f"扫描股票数量: 50")
    print(f"发现投资机会: {len(opportunities)}")
    
    if opportunities:
        print(f"投资机会比例: {len(opportunities)/50*100:.1f}%")
        print(f"\n✅ V18策略成功发现投资机会！")
        
        # 显示前3个机会的详细信息
        print(f"\n📋 前3个投资机会详情:")
        for i, opp in enumerate(opportunities[:3]):
            print(f"\n机会 {i+1}:")
            print(f"  股票: {opp['stock']['id']} - {opp['stock']['name']}")
            print(f"  价格: {opp['record_of_today']['close']:.2f}")
            
            # 显示财务指标
            financial = opp['extra_fields'].get('financial_indicators', {})
            if financial:
                print(f"  市值: {financial.get('market_cap', 0):.0f}万")
                print(f"  PE: {financial.get('pe_ratio', 0):.1f}")
                print(f"  PB: {financial.get('pb_ratio', 0):.2f}")
                print(f"  PS: {financial.get('ps_ratio', 0):.2f}")
            
            # 显示技术指标
            conditions = opp['extra_fields'].get('signal_conditions', {})
            print(f"  MA收敛度: {conditions.get('ma_convergence', 0):.4f}")
            print(f"  历史分位数: {conditions.get('historical_percentile', 0):.3f}")
            print(f"  RSI: {conditions.get('rsi_signal', 0):.1f}")
    else:
        print(f"\n❌ V18策略未发现投资机会")
        print(f"可能原因:")
        print(f"1. 财务筛选条件过于严格")
        print(f"2. 技术条件仍需要进一步放松")
        print(f"3. 当前市场环境不适合")
    
    print(f"\n🎯 V18策略测试完成")

if __name__ == "__main__":
    test_v18_strategy()
