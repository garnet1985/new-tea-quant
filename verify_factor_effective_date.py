#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.data_source.data_source_manager import DataSourceManager
from utils.db.db_manager import get_sync_db_manager
from datetime import datetime, timedelta

def verify_factor_effective_date():
    # 初始化
    db = get_sync_db_manager()
    dsm = DataSourceManager(db, is_verbose=True)
    tu = dsm.sources['tushare']
    ak = dsm.sources['akshare']
    ak.inject_dependency(tu)
    
    print("=== 验证复权因子的生效时间 ===")
    print("股票: 000001.SZ")
    print()
    
    # 选择一个具体的复权事件来分析
    event_date = '20180815'  # Tushare记录的复权事件日期
    
    print(f"分析复权事件日期: {event_date}")
    print()
    
    # 分析事件日期前后几天的因子变化
    event_dt = datetime.strptime(event_date, '%Y%m%d')
    
    print("=== 事件日期前后的因子变化 ===")
    
    # 分析事件日期前后3天
    for days_offset in range(-3, 4):
        test_date = event_dt + timedelta(days=days_offset)
        test_date_str = test_date.strftime('%Y%m%d')
        
        # 计算该日期的因子
        factor = ak.calc_factors({'code': '000001', 'ts_code': '000001.SZ'}, test_date_str)
        
        if factor:
            marker = "🔥" if days_offset == 0 else "  "  # 标记事件日期
            print(f"{marker} {test_date.strftime('%Y-%m-%d')}: 因子={factor['qfq_factor']:.6f}")
        else:
            marker = "🔥" if days_offset == 0 else "  "
            print(f"{marker} {test_date.strftime('%Y-%m-%d')}: 无法计算")
    
    print("\n=== 验证您的测试用例 ===")
    
    # 您的测试用例
    test_cases = [
        ('2018-08-16', 8.78, 6.4),  # 事件日期后一天
    ]
    
    for date, raw_price, expected_qfq in test_cases:
        date_formatted = date.replace('-', '')
        
        # 计算该日期的因子
        factor = ak.calc_factors({'code': '000001', 'ts_code': '000001.SZ'}, date_formatted)
        
        if factor:
            calculated_qfq = raw_price * factor['qfq_factor']
            error = abs(calculated_qfq - expected_qfq)
            error_percent = (error / expected_qfq) * 100
            status = "✅" if error_percent < 1 else "❌"
            
            print(f"{status} {date}: 因子={factor['qfq_factor']:.6f}, 计算QFQ={calculated_qfq:.2f}, 期望={expected_qfq:.2f}, 误差={error_percent:.2f}%")
        else:
            print(f"❌ {date}: 无法计算因子")
    
    print("\n=== 分析 ===")
    print("如果2018-08-16的因子与2018-08-15相同，说明：")
    print("1. 新因子从2018-08-16开始生效")
    print("2. 事件日期当天使用新因子")
    print("\n如果2018-08-16的因子与2018-08-15不同，说明：")
    print("1. 新因子从2018-08-17开始生效")
    print("2. 事件日期当天仍使用旧因子")

if __name__ == "__main__":
    verify_factor_effective_date() 