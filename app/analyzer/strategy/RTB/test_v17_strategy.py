#!/usr/bin/env python3
"""
测试V17策略优化效果
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

def test_v17_strategy():
    print("🚀 测试V17策略优化效果...")
    
    # 初始化
    db = DatabaseManager()
    db.initialize()
    strategy = ReverseTrendBet(db, is_verbose=True)
    loader = DataLoader(db)
    
    # 获取股票列表
    stock_list = loader.load_stock_list(filtered=True)
    if not stock_list:
        print("❌ 没有股票数据")
        return
    
    print(f"📊 配置信息:")
    print(f"策略版本: V17_ML_Optimized")
    print(f"测试股票数量: {settings['mode']['test_amount']}")
    
    # 设置扫描范围
    strategy.set_scan_range(settings['mode']['test_amount'], settings['mode']['start_idx'])
    
    # 扫描投资机会
    opportunities = strategy.scan()
    
    print(f"\n🎯 扫描结果:")
    print(f"找到投资机会: {len(opportunities)}个")
    
    if opportunities:
        print("\n📈 投资机会详情:")
        for i, opp in enumerate(opportunities[:3]):  # 显示前3个
            stock = opp['stock']
            features = opp['extra_fields'].get('features', {})
            signal_conditions = opp['extra_fields'].get('signal_conditions', {})
            
            print(f"\n--- 机会 {i+1}: {stock['name']} ({stock['id']}) ---")
            print(f"MA收敛度: {signal_conditions.get('ma_convergence', 0):.4f} (阈值: <0.12)")
            print(f"历史分位数: {signal_conditions.get('historical_percentile', 0):.3f} (阈值: <0.2)")
            print(f"RSI: {signal_conditions.get('rsi_signal', 0):.1f} (阈值: <65)")
            print(f"MA20斜率: {signal_conditions.get('ma20_slope', 0):.4f}")
            print(f"MA60斜率: {signal_conditions.get('ma60_slope', 0):.4f}")
    else:
        print("❌ 未找到投资机会")
    
    # 清理
    if db.is_sync_connected:
        db.disconnect()
    
    print("\n🎉 V17策略测试完成！")

if __name__ == "__main__":
    test_v17_strategy()
