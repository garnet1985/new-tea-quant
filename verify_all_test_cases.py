#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.data_source.data_source_manager import DataSourceManager
from utils.db.db_manager import get_sync_db_manager

def verify_all_test_cases():
    # 初始化
    db = get_sync_db_manager()
    dsm = DataSourceManager(db, is_verbose=True)
    tu = dsm.sources['tushare']
    ak = dsm.sources['akshare']
    ak.inject_dependency(tu)
    
    print("=== 验证所有测试用例 ===")
    print("股票: 000001.SZ")
    print("规则: 复权事件日期使用旧因子，事件日期+1开始使用新因子")
    print()
    
    # 您的测试用例
    test_cases = [
        ('2019-09-26', 15.71, 13.47),
        ('2018-08-16', 8.78, 6.4),
        ('2021-07-08', 21.51, 19.67),
        ('2022-12-12', 13.11, 11.5),
        ('2017-09-06', 11.7, 9.18),
        ('2019-10-14', 17.47, 14.98),
        ('2020-02-03', 13.7, 11.75),
        ('2020-04-30', 13.63, 11.69),
        ('2017-05-15', 7.73, 6.18),
        ('2024-08-26', 11.53, 9.88),
        ('2024-09-25', 11.54, 9.89),
    ]
    
    print("=== 测试结果 ===")
    for date, raw_price, expected_qfq in test_cases:
        date_formatted = date.replace('-', '')
        
        # 直接计算该日期的因子
        factor = ak.calc_factors({'code': '000001', 'ts_code': '000001.SZ'}, date_formatted)
        
        if factor:
            calculated_qfq = raw_price * factor['qfq_factor']
            error = abs(calculated_qfq - expected_qfq)
            error_percent = (error / expected_qfq) * 100
            status = "✅" if error_percent < 1 else "❌"
            
            print(f"{status} {date}: 因子={factor['qfq_factor']:.6f}, 计算QFQ={calculated_qfq:.2f}, 期望={expected_qfq:.2f}, 误差={error_percent:.2f}%")
        else:
            print(f"❌ {date}: 无法计算因子")
    
    print("\n=== 总结 ===")
    print("如果大部分测试用例的误差都在1%以内，说明：")
    print("1. 我们的因子计算方法是正确的")
    print("2. 复权因子的生效时间理解是正确的")
    print("3. 我们可以直接使用AKShare动态计算因子")

if __name__ == "__main__":
    verify_all_test_cases() 