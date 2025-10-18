#!/usr/bin/env python3
"""
测试V18.2策略 - 分层财务筛选+优化技术条件
"""
import sys
import os
from typing import Dict, Any, List

# 将项目根目录添加到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader
from loguru import logger

def test_v18_2_strategy():
    """
    测试V18.2策略的扫描功能
    """
    logger.info("🚀 测试V18.2平衡策略")
    
    # 初始化数据库管理器
    db_manager = DatabaseManager()
    
    # 创建策略实例
    strategy = ReverseTrendBet(db_manager, settings)
    
    # 获取股票列表（前100只）
    stock_list_table = db_manager.get_table_instance('stock_list')
    stock_list = stock_list_table.load_filtered_stock_list(order_by='id')[:100]
    
    logger.info(f"📊 开始扫描投资机会... (股票数量: {len(stock_list)})")
    
    opportunities = []
    financial_stats = {
        'large_cap': 0,
        'mid_cap': 0,
        'small_cap': 0,
        'total_checked': 0
    }
    
    for stock in stock_list:
        # 模拟DataLoader的行为
        required_data = DataLoader().prepare_data(stock, settings)
        opportunity = strategy.scan_opportunity(stock, required_data, settings)
        
        if opportunity:
            opportunities.append(opportunity)
            # 统计财务分层情况
            financial_indicators = opportunity['extra_fields'].get('financial_indicators', {})
            market_cap = financial_indicators.get('market_cap', 0)
            if market_cap >= 1000000:
                financial_stats['large_cap'] += 1
            elif market_cap >= 300000:
                financial_stats['mid_cap'] += 1
            else:
                financial_stats['small_cap'] += 1
        
        financial_stats['total_checked'] += 1
    
    logger.info(f"\n📈 V18.2策略扫描结果:")
    logger.info(f"扫描股票数量: {len(stock_list)}")
    logger.info(f"发现投资机会: {len(opportunities)}")
    
    # 显示财务分层统计
    logger.info(f"\n💰 财务分层统计:")
    logger.info(f"大盘股 (≥100亿): {financial_stats['large_cap']} 个")
    logger.info(f"中盘股 (30-100亿): {financial_stats['mid_cap']} 个")
    logger.info(f"小盘股 (<30亿): {financial_stats['small_cap']} 个")
    
    if opportunities:
        logger.info(f"\n📋 投资机会详情:")
        strategy.report(opportunities[:3])  # 显示前3个机会
    else:
        logger.info("❌ V18.2策略未发现投资机会")
        logger.info("可能原因:")
        logger.info("1. 分层财务筛选条件过于严格")
        logger.info("2. 技术条件需要进一步调整")
        logger.info("3. 当前市场环境不适合")
    
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
        print(f"  RSI信号: {conditions.get('rsi_signal', 0):.1f}")
        print(f"  成交量确认: {conditions.get('volume_confirmation', 0):.3f}")
        
        # 显示财务指标
        financial = opp['extra_fields'].get('financial_indicators', {})
        market_cap = financial.get('market_cap', 0)
        pe_ratio = financial.get('pe_ratio', 0)
        pb_ratio = financial.get('pb_ratio', 0)
        ps_ratio = financial.get('ps_ratio', 0)
        
        if market_cap >= 1000000:
            cap_type = "大盘股"
        elif market_cap >= 300000:
            cap_type = "中盘股"
        else:
            cap_type = "小盘股"
            
        print(f"  市值: {market_cap/10000:.1f}亿 ({cap_type})")
        print(f"  PE: {pe_ratio:.1f}")
        print(f"  PB: {pb_ratio:.2f}")
        print(f"  PS: {ps_ratio:.2f}")
    
    logger.info("\n🎯 V18.2策略测试完成")
    logger.info(f"预期目标: 胜率55-58%, ROI 7-9%, 年化收益20-25%")

if __name__ == "__main__":
    test_v18_2_strategy()
