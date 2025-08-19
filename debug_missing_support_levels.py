#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
深入调试遗漏支撑位的脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService


def debug_missing_support_levels():
    """深入调试遗漏支撑位"""
    print("🔍 深入调试遗漏支撑位")
    print("=" * 60)
    
    # 定义关键支撑位
    key_levels = [
        {"name": "6.3-6.4元", "min": 6.3, "max": 6.4},
        {"name": "12.4-12.9元", "min": 12.4, "max": 12.9},
        {"name": "15.9元", "min": 15.85, "max": 15.95},
        {"name": "20.7元", "min": 20.65, "max": 20.75},
        {"name": "22.2元", "min": 22.15, "max": 22.25}
    ]
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager()
        db_manager.connect()
        
        stock_kline_table = db_manager.get_table_instance("stock_kline")
        adj_factor_table = db_manager.get_table_instance("adj_factor")
        
        # 获取000002.SZ的日线数据
        daily_data = stock_kline_table.load(
            condition="id = %s AND term = %s",
            params=("000002.SZ", "daily"),
            order_by="date ASC"
        )
        
        if not daily_data:
            print("❌ 未获取到K线数据")
            return
        
        print(f"✅ 获取到 {len(daily_data)} 条日线数据")
        
        # 应用前复权
        print("🔧 应用前复权处理...")
        qfq_factors = adj_factor_table.get_stock_factors("000002.SZ")
        daily_data = DataSourceService.to_qfq(daily_data, qfq_factors)
        print("✅ 前复权处理完成")
        
        # 过滤负价格数据
        daily_data = [d for d in daily_data if float(d['close']) > 0]
        print(f"✅ 过滤负价格后剩余 {len(daily_data)} 条数据")
        
        # 初始化策略服务
        strategy_service = HistoricLowService()
        
        # 1. 检查基础波谷检测
        print("\n📊 1. 检查基础波谷检测...")
        valleys = strategy_service.find_valleys(daily_data)
        print(f"   找到 {len(valleys)} 个基础波谷")
        
        # 检查每个关键支撑位的基础波谷
        for level in key_levels:
            print(f"\n   🔍 检查 {level['name']} 的基础波谷...")
            target_valleys = []
            for valley in valleys:
                if level['min'] <= valley['price'] <= level['max']:
                    target_valleys.append(valley)
            
            if target_valleys:
                print(f"      ✅ 找到 {len(target_valleys)} 个基础波谷:")
                for valley in target_valleys:
                    print(f"        - {valley['date']}: 价格 {valley['price']:.2f}, 跌幅 {valley['drop_rate']*100:.1f}%")
            else:
                print(f"      ❌ 未找到基础波谷")
                
                # 检查为什么没有找到波谷
                print(f"      🔍 分析原因...")
                # 查找该价格区间的所有记录
                price_records = []
                for record in daily_data:
                    close_price = float(record['close'])
                    if level['min'] <= close_price <= level['max']:
                        price_records.append(record)
                
                if price_records:
                    print(f"        该价格区间有 {len(price_records)} 条记录")
                    print(f"        前5条记录:")
                    for i, record in enumerate(price_records[:5]):
                        print(f"          {i+1}. {record['date']}: 收盘价 {float(record['close']):.2f}")
                    
                    # 检查这些记录是否满足波谷条件
                    print(f"        🔍 检查波谷检测参数...")
                    print(f"        当前波谷检测参数:")
                    print(f"        - min_drop_threshold: 0.10 (10%)")
                    print(f"        - local_range_days: 5")
                    print(f"        - lookback_days: 60")
        
        # 2. 检查高频触及检测
        print("\n📊 2. 检查高频触及检测...")
        frequent_valleys = strategy_service.find_frequently_touched_valleys(
            daily_data, price_tolerance=0.15, min_touch_count=2
        )
        print(f"   找到 {len(frequent_valleys)} 组高频触及波谷")
        
        # 检查每个关键支撑位的高频触及
        for level in key_levels:
            print(f"\n   🔍 检查 {level['name']} 的高频触及...")
            target_frequent = []
            for group in frequent_valleys:
                group_prices = [v['price'] for v in group['valleys']]
                if any(level['min'] <= p <= level['max'] for p in group_prices):
                    target_frequent.append(group)
            
            if target_frequent:
                print(f"      ✅ 找到 {len(target_frequent)} 组高频触及:")
                for group in target_frequent:
                    print(f"        - 触及次数: {group['touch_count']}, 价格区间: {group['price_range']['min']:.2f}-{group['price_range']['max']:.2f}")
                    for valley in group['valleys']:
                        if level['min'] <= valley['price'] <= level['max']:
                            print(f"          * {valley['date']}: 价格 {valley['price']:.2f}")
            else:
                print(f"      ❌ 未找到高频触及组")
                print(f"      🔍 分析原因...")
                print(f"        当前高频触及检测参数:")
                print(f"        - price_tolerance: 0.15 (15%)")
                print(f"        - min_touch_count: 2")
        
        # 3. 检查横盘确认检测
        print("\n📊 3. 检查横盘确认检测...")
        consolidation_valleys = strategy_service.find_consolidation_valleys(
            daily_data, consolidation_days=20, price_tolerance=0.10, min_touch_count=2
        )
        print(f"   找到 {len(consolidation_valleys)} 个横盘确认波谷")
        
        # 检查每个关键支撑位的横盘确认
        for level in key_levels:
            print(f"\n   🔍 检查 {level['name']} 的横盘确认...")
            target_consolidation = []
            for valley_info in consolidation_valleys:
                valley = valley_info['valley']
                if level['min'] <= valley['price'] <= level['max']:
                    target_consolidation.append(valley_info)
            
            if target_consolidation:
                print(f"      ✅ 找到 {len(target_consolidation)} 个横盘确认:")
                for valley_info in target_consolidation:
                    valley = valley_info['valley']
                    consolidation = valley_info['consolidation']
                    print(f"        - {valley['date']}: 价格 {valley['price']:.2f}, 横盘确认分数: {valley_info['consolidation_score']}")
                    print(f"          横盘期间: {consolidation['duration_days']}天, 触及次数: {consolidation['touch_count']}")
            else:
                print(f"      ❌ 未找到横盘确认")
                print(f"      🔍 分析原因...")
                print(f"        当前横盘确认检测参数:")
                print(f"        - consolidation_days: 20")
                print(f"        - price_tolerance: 0.10 (10%)")
                print(f"        - min_touch_count: 2")
        
        db_manager.disconnect()
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_missing_support_levels()
