#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专门检查关键支撑位的脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService


def debug_key_support_levels():
    """专门检查关键支撑位"""
    print("🔍 专门检查关键支撑位")
    print("=" * 60)
    
    # 定义关键支撑位
    key_levels = [
        {"name": "6.3-6.4元", "min": 6.3, "max": 6.4},
        {"name": "12.7-12.9元", "min": 12.4, "max": 12.9},
        {"name": "15.9元", "min": 15.00, "max": 15.95},
        {"name": "20.7元", "min": 20.4, "max": 21}
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
        
        # 获取最终整合结果
        print("\n📊 获取最终整合结果...")
        merged_lows = strategy_service.find_merged_historic_lows(daily_data)
        
        print(f"✅ 共找到 {len(merged_lows)} 个历史低点")
        
        # 检查每个关键支撑位
        for level in key_levels:
            print(f"\n🔍 检查 {level['name']} 支撑位...")
            
            # 在最终结果中查找
            found_in_results = []
            for low_point in merged_lows:
                if level['min'] <= low_point['price'] <= level['max']:
                    found_in_results.append(low_point)
            
            if found_in_results:
                print(f"   ✅ 在最终结果中找到 {len(found_in_results)} 个:")
                for low_point in found_in_results:
                    sources_str = ", ".join(low_point['conclusion_from'])
                    print(f"      - {low_point['date']}: 价格 {low_point['price']:.2f}, 来源: [{sources_str}]")
            else:
                print(f"   ❌ 在最终结果中未找到")
            
            # 在原始数据中查找
            found_in_raw = []
            for record in daily_data:
                close_price = float(record['close'])
                if level['min'] <= close_price <= level['max']:
                    found_in_raw.append(record)
            
            print(f"   📊 在原始数据中找到 {len(found_in_raw)} 条记录")
            if found_in_raw:
                print("      前10条记录:")
                for i, record in enumerate(found_in_raw[:10]):
                    print(f"        {i+1}. {record['date']}: 收盘价 {float(record['close']):.2f}")
        
        # 检查这些关键支撑位的排名
        print(f"\n🏆 检查关键支撑位在最终结果中的排名...")
        for level in key_levels:
            found_rankings = []
            for i, low_point in enumerate(merged_lows):
                if level['min'] <= low_point['price'] <= level['max']:
                    found_rankings.append({
                        'rank': i + 1,
                        'low_point': low_point
                    })
            
            if found_rankings:
                print(f"   {level['name']}:")
                for ranking in found_rankings:
                    sources_str = ", ".join(ranking['low_point']['conclusion_from'])
                    print(f"     排名第{ranking['rank']}: {ranking['low_point']['date']} 价格:{ranking['low_point']['price']:.2f} 来源:[{sources_str}]")
            else:
                print(f"   {level['name']}: 未在最终结果中找到")
        
        # 显示前20名的完整列表
        print(f"\n📋 最终结果前20名完整列表:")
        for i, low_point in enumerate(merged_lows[:20]):
            sources_str = ", ".join(low_point['conclusion_from'])
            print(f"   {i+1}. {low_point['date']} - 价格: {low_point['price']:.2f}, 来源: [{sources_str}]")
        
        db_manager.disconnect()
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_key_support_levels()
