#!/usr/bin/env python3
"""
测试RTB V14策略
V14核心改进：
1. 信号检测：基于周线数据（长期趋势判断）
2. 买入卖出：基于日线数据（精确执行）
3. 时间止损：确保180个交易日正确执行
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
from utils.db.db_manager import DatabaseManager
from app.data_loader.data_loader import DataLoader

def test_v14_strategy():
    """测试V14策略配置"""
    print("🚀 测试RTB V14策略配置...")
    
    # 检查设置
    print(f"✅ 策略启用状态: {settings['is_enabled']}")
    print(f"✅ 模拟版本: {settings['mode']['simulation_ref_version']}")
    print(f"✅ 基础周期: {settings['klines']['base_term']}")
    print(f"✅ 数据周期: {settings['klines']['terms']}")
    print(f"✅ 时间止损: {settings['goal']['fixed_trading_days']}个交易日")
    
    # 初始化数据库和策略
    try:
        db = DatabaseManager()
        strategy = ReverseTrendBet(db, is_verbose=True)
        print("✅ V14策略初始化成功")
        
        # 测试机会扫描
        print("\n🔍 测试机会扫描功能...")
        strategy.set_scan_range(5, 0)  # 测试前5只股票
        opportunities = strategy.scan()
        
        if opportunities:
            print(f"✅ 找到 {len(opportunities)} 个投资机会")
            strategy.report(opportunities)
        else:
            print("⚠️ 未找到投资机会")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_v14_strategy()
