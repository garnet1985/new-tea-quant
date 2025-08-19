#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专门调试2017年12.56元的脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService


def debug_2017_12_56():
    """专门调试2017年12.56元"""
    print("🔍 专门调试2017年12.56元")
    print("=" * 60)
    
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
        
        # 查找2017年的波谷
        valleys_2017 = []
        for valley in valleys:
            if valley['date'].startswith('2017'):
                valleys_2017.append(valley)
        
        print(f"   2017年找到 {len(valleys_2017)} 个基础波谷:")
        for valley in valleys_2017:
            print(f"   - {valley['date']}: 价格 {valley['price']:.2f}, 跌幅 {valley['drop_rate']*100:.1f}%")
        
        # 2. 检查高频触及检测
        print("\n📊 2. 检查高频触及检测...")
        frequent_valleys = strategy_service.find_frequently_touched_valleys(
            daily_data, price_tolerance=0.15, min_touch_count=2
        )
        
        # 查找包含2017年波谷的高频触及组
        target_frequent_2017 = []
        for group in frequent_valleys:
            group_dates = [v['date'] for v in group['valleys']]
            if any(date.startswith('2017') for date in group_dates):
                target_frequent_2017.append(group)
        
        print(f"   包含2017年波谷的高频触及组: {len(target_frequent_2017)} 个")
        for group in target_frequent_2017:
            print(f"   - 触及次数: {group['touch_count']}, 价格区间: {group['price_range']['min']:.2f}-{group['price_range']['max']:.2f}")
            for valley in group['valleys']:
                if valley['date'].startswith('2017'):
                    print(f"     * 2017年: {valley['date']} 价格:{valley['price']:.2f} 跌幅:{valley['drop_rate']*100:.1f}%")
        
        # 3. 检查横盘确认检测
        print("\n📊 3. 检查横盘确认检测...")
        consolidation_valleys = strategy_service.find_consolidation_valleys(
            daily_data, consolidation_days=20, price_tolerance=0.10, min_touch_count=2
        )
        
        # 查找2017年的横盘确认
        target_consolidation_2017 = []
        for valley_info in consolidation_valleys:
            valley = valley_info['valley']
            if valley['date'].startswith('2017'):
                target_consolidation_2017.append(valley_info)
        
        print(f"   2017年找到 {len(target_consolidation_2017)} 个横盘确认波谷:")
        for valley_info in target_consolidation_2017:
            valley = valley_info['valley']
            consolidation = valley_info['consolidation']
            print(f"   - {valley['date']}: 价格 {valley['price']:.2f}, 横盘确认分数: {valley_info['consolidation_score']}")
            print(f"     横盘期间: {consolidation['duration_days']}天, 触及次数: {consolidation['touch_count']}")
            
            # 检查touches结构
            if consolidation['touches']:
                first_touch = consolidation['touches'][0]
                print(f"     第一个触及记录: {first_touch}")
        
        # 4. 手动检查2017年12.56元附近的数据
        print("\n📊 4. 手动检查2017年12.56元附近的数据...")
        data_2017 = [d for d in daily_data if d['date'].startswith('2017')]
        
        # 查找12.5-12.8元区间的记录
        target_records_2017 = []
        for record in data_2017:
            close_price = float(record['close'])
            if 12.5 <= close_price <= 12.8:
                target_records_2017.append(record)
        
        print(f"   2017年12.5-12.8元区间找到 {len(target_records_2017)} 条记录:")
        for record in target_records_2017:
            print(f"   - {record['date']}: 收盘价 {float(record['close']):.2f}")
        
        db_manager.disconnect()
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_2017_12_56()
