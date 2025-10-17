#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试RTB V10 ML优化策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
from app.analyzer.analyzer_service import AnalyzerService
from utils.db.db_manager import DatabaseManager
from app.data_loader.data_loader import DataLoader

def test_v10_strategy():
    """测试V10 ML优化策略"""
    
    print("🚀 测试RTB V11实用版策略")
    print("="*60)
    
    # 创建数据库连接
    db = DatabaseManager()
    data_loader = DataLoader(db)
    
    # 创建RTB策略实例
    rtb_strategy = ReverseTrendBet(db, is_verbose=True)
    
    # 获取股票列表（测试前50只）
    stock_list_table = db.get_table_instance('stock_list')
    stocks = stock_list_table.load_filtered_stock_list()[:50]
    
    print(f"📊 测试股票数量: {len(stocks)}")
    print(f"📊 策略版本: V11实用版")
    print(f"📊 基于: V10分析结果调整，平衡严格性和实用性")
    
    opportunities = []
    
    for i, stock in enumerate(stocks):
        print(f"\n🔍 测试股票 {i+1}/{len(stocks)}: {stock['name']} ({stock['id']})")
        
        try:
            # 准备数据
            data = data_loader.prepare_data(stock, settings)
            
            # 扫描机会
            opportunity = ReverseTrendBet.scan_opportunity(stock, data, settings)
            
            if opportunity:
                opportunities.append(opportunity)
                print(f"✅ 发现机会: {stock['name']}")
            else:
                print(f"❌ 无机会: {stock['name']}")
                
        except Exception as e:
            print(f"⚠️ 错误: {stock['name']} - {e}")
    
    print(f"\n📊 扫描结果总结:")
    print(f"📊 测试股票: {len(stocks)}")
    print(f"📊 发现机会: {len(opportunities)}")
    print(f"📊 成功率: {len(opportunities)/len(stocks)*100:.1f}%")
    
    if opportunities:
        print(f"\n🎯 V11策略发现的投资机会:")
        ReverseTrendBet.report(opportunities)
    
    print(f"\n🎉 V11策略测试完成!")
    print("="*60)

if __name__ == "__main__":
    test_v10_strategy()
