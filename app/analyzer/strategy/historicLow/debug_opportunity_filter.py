#!/usr/bin/env python3
"""
调试投资机会过滤逻辑
分析000002.SZ在2024年7-9月期间为什么没有被发现投资机会
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.strategy.historicLow.strategy_settings import invest_settings
from app.utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService
from datetime import datetime
import math

def debug_opportunity_filter():
    """调试投资机会过滤逻辑"""
    print("🔍 开始调试000002.SZ投资机会过滤逻辑")
    
    # 初始化服务
    service = HistoricLowService()
    
    # 已知条件
    stock_id = "000002.SZ"
    historic_low_price = 6.40274655
    historic_low_date = "20151030"
    term = 96
    
    print(f"📊 已知条件:")
    print(f"  股票: {stock_id}")
    print(f"  历史低点: {historic_low_date}, 价格: {historic_low_price}")
    print(f"  期数: {term}")
    
    # 获取投资范围
    opportunity_range = invest_settings['goal']['opportunityRange']
    upper_bound = historic_low_price * (1 + opportunity_range)
    lower_bound = historic_low_price * (1 - opportunity_range)
    
    print(f"  投资范围: [{lower_bound:.4f}, {upper_bound:.4f}]")
    print(f"  机会范围: ±{opportunity_range * 100}%")
    
    # 初始化数据库
    try:
        db = DatabaseManager()
        stock_kline_table = db.get_table_instance("stock_kline")
        adj_factor_table = db.get_table_instance("adj_factor")
        
        print("\n📥 获取2024年7-9月日线数据...")
        
        # 获取2024年7-9月的日线数据
        start_date = "20240701"
        end_date = "20240930"
        
        # 构建日期范围查询
        daily_data = stock_kline_table.load(
            "id = %s AND term = 'daily' AND date >= %s AND date <= %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
        
        if not daily_data:
            print("❌ 未获取到日线数据")
            return
        
        print(f"✅ 获取到 {len(daily_data)} 条日线数据")
        
        # 获取复权因子
        qfq_factors = adj_factor_table.get_stock_factors(stock_id)
        
        # 转换为前复权数据
        qfq_daily_data = DataSourceService.to_qfq(daily_data, qfq_factors)
        
        print("\n🔍 分析每个交易日...")
        
        # 分析每个交易日
        for i, record in enumerate(qfq_daily_data):
            date = record['date']
            close_price = float(record['close'])
            
            print(f"\n📅 {date}: 收盘价 {close_price:.4f}")
            
            # 1. 检查是否在投资范围内
            in_range = lower_bound <= close_price <= upper_bound
            print(f"   投资范围检查: {'✅' if in_range else '❌'}")
            
            if not in_range:
                continue
            
            # 2. 检查趋势是否过于陡峭
            # 获取冻结窗口数据（从当前日期往前推N天）
            threshold_days = invest_settings['goal']['invest_reference_day_distance_threshold']
            
            # 获取冻结窗口的日线数据
            freeze_window_data = stock_kline_table.load(
                "id = %s AND term = 'daily' AND date <= %s",
                (stock_id, date),
                order_by="date DESC",
                limit=threshold_days
            )
            
            if freeze_window_data:
                # 转换为前复权数据
                qfq_freeze_window = DataSourceService.to_qfq(freeze_window_data, qfq_factors)
                
                # 检查趋势是否过于陡峭
                trend_too_steep = service.is_trend_too_steep(qfq_freeze_window)
                print(f"   趋势检查: {'❌ 过于陡峭' if trend_too_steep else '✅ 趋势合适'}")
                
                if not trend_too_steep:
                    print(f"   🎯 发现投资机会！")
                    print(f"      日期: {date}")
                    print(f"      价格: {close_price:.4f}")
                    print(f"      历史低点: {historic_low_price:.4f}")
                    print(f"      投资范围: [{lower_bound:.4f}, {upper_bound:.4f}]")
                    return
            else:
                print(f"   趋势检查: 数据不足")
        
        print("\n❌ 未发现符合条件的投资机会")
        
    except Exception as e:
        print(f"❌ 调试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_opportunity_filter()
