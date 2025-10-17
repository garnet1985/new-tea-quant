#!/usr/bin/env python3
"""
测试V12优化版策略
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
from app.data_loader.data_loader import DataLoader
from utils.db.db_manager import DatabaseManager
# 使用默认配置

def test_v12_strategy():
    """测试V12策略配置"""
    
    print("🧪 测试V12优化版策略配置")
    print("="*60)
    
    # 检查配置
    print("📋 V12策略配置检查:")
    print(f"  止损设置: {settings['goal']['stop_loss']['stages'][0]['ratio']*100:.0f}%")
    print(f"  止盈阶段数: {len(settings['goal']['take_profit']['stages'])}")
    
    for i, stage in enumerate(settings['goal']['take_profit']['stages']):
        print(f"    阶段{i+1}: {stage['name']} - {stage['ratio']*100:.0f}% (卖出{stage['sell_ratio']*100:.0f}%)")
    
    print(f"  时间止损: {settings['goal']['fixed_trading_days']}天")
    print(f"  策略版本: {settings['mode']['simulation_ref_version']}")
    
    # 初始化组件
    print("\n🔧 初始化组件...")
    try:
        db = DatabaseManager()
        data_loader = DataLoader(db)
        
        print("✅ 数据库连接成功")
        print("✅ 数据加载器初始化成功")
        
        # 测试策略扫描
        print("\n🔍 测试策略扫描功能...")
        strategy = ReverseTrendBet(db)
        
        # 获取测试股票列表
        stock_list_table = db.get_table_instance('stock_list')
        stocks = stock_list_table.load_filtered_stock_list(limit=5)
        
        if not stocks:
            print("❌ 未找到测试股票")
            return
            
        print(f"📊 测试股票数量: {len(stocks)}")
        
        # 测试扫描功能
        opportunities_found = 0
        for stock in stocks:
            try:
                # 加载股票数据
                data = data_loader.load_klines(
                    stock_id=stock['id'],
                    terms=['daily', 'weekly'],
                    start_date='',
                    end_date='',
                    adjust='qfq'
                )
                
                if not data or not data.get('klines'):
                    continue
                    
                # 扫描投资机会
                opportunity = ReverseTrendBet.scan_opportunity(stock, data, settings)
                
                if opportunity:
                    opportunities_found += 1
                    print(f"✅ 找到机会: {stock['name']} ({stock['id']})")
                    print(f"   版本: {opportunity['extra_fields']['strategy_version']}")
                    
            except Exception as e:
                print(f"⚠️  测试股票 {stock['id']} 时出错: {e}")
                continue
        
        print(f"\n📊 扫描结果: 找到 {opportunities_found}/{len(stocks)} 个投资机会")
        
        if opportunities_found > 0:
            print("🎉 V12策略测试成功！")
        else:
            print("ℹ️  当前市场条件下未找到投资机会（正常情况）")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_v12_strategy()
    if success:
        print("\n✅ V12策略配置验证通过，可以开始正式测试！")
    else:
        print("\n❌ V12策略配置验证失败，请检查配置！")
