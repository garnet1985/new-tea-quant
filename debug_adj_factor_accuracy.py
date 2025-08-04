#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.data_source.providers.akshare.main import AKShare
from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.main import Tushare
from loguru import logger
import pandas as pd

def debug_adj_factor_accuracy():
    """详细调试复权因子准确性"""
    
    # 初始化
    db = get_sync_db_manager()
    ak = AKShare(db, is_verbose=True)
    tu = Tushare(db, is_verbose=True)
    ak.inject_dependency(tu)
    
    # 复权因子数据（从日志中获取）
    adj_factors = [
        {'date': '20081030', 'qfq_factor': 0.0017683465959328027},
        {'date': '20121018', 'qfq_factor': 0.13101406365655072},
        {'date': '20130619', 'qfq_factor': 0.20166320166320167},
        {'date': '20140611', 'qfq_factor': 0.3225806451612903},
        {'date': '20150410', 'qfq_factor': 0.5464646464646464},
        {'date': '20160615', 'qfq_factor': 0.5651340996168583},
        {'date': '20170720', 'qfq_factor': 0.755697356426618},
        {'date': '20180711', 'qfq_factor': 0.7129840546697039},
        {'date': '20180815', 'qfq_factor': 0.7292377701934016},
        {'date': '20180827', 'qfq_factor': 0.7718120805369129},
        {'date': '20190625', 'qfq_factor': 0.8227848101265823},
        {'date': '20191231', 'qfq_factor': 0.8638297872340427},
        {'date': '20200527', 'qfq_factor': 0.8276923076923077},
        {'date': '20210106', 'qfq_factor': 0.8967280163599182},
        {'date': '20210513', 'qfq_factor': 0.9124403987863026},
        {'date': '20220721', 'qfq_factor': 0.8585703305149884},
        {'date': '20230531', 'qfq_factor': 0.8612068965517242},
        {'date': '20230613', 'qfq_factor': 0.8632115548003398},
        {'date': '20240613', 'qfq_factor': 0.8768518518518519},
        {'date': '20240624', 'qfq_factor': 0.9388777555110219},
        {'date': '20240625', 'qfq_factor': 0.9394841269841271},
        {'date': '20241009', 'qfq_factor': 0.9477739726027398},
        {'date': '20250611', 'qfq_factor': 0.969620253164557}
    ]
    
    # 按日期排序
    adj_factors.sort(key=lambda x: x['date'])
    
    print("=== 复权因子详细分析 ===")
    print("复权因子列表（按日期排序）:")
    for factor in adj_factors:
        print(f"  {factor['date']}: {factor['qfq_factor']:.6f}")
    print()
    
    # 测试用例
    test_cases = [
        ('2019-09-26', 13.47),
        ('2018-08-16', 6.4),
        ('2021-07-08', 19.67),
        ('2022-12-12', 11.5),
        ('2017-09-06', 9.18),
        ('2019-10-14', 14.98),
        ('2020-02-03', 11.75),
        ('2020-04-30', 11.69),
        ('2017-05-15', 6.18),
        ('2024-08-26', 9.88),
        ('2024-09-25', 9.89)
    ]
    
    print("=== 详细测试结果 ===")
    
    for test_date, expected_qfq_price in test_cases:
        print(f"\n--- {test_date} ---")
        
        # 获取不复权收盘价
        raw_close = ak.storage.get_close_price('000001.SZ', test_date.replace('-', ''))
        print(f"不复权收盘价: {raw_close}")
        
        if raw_close is None:
            print("❌ 数据库中未找到不复权数据")
            continue
        
        # 查找适用的复权因子
        target_date_str = test_date.replace('-', '')
        applicable_factors = []
        
        for factor in adj_factors:
            if factor['date'] <= target_date_str:
                applicable_factors.append(factor)
        
        print(f"适用的复权因子数量: {len(applicable_factors)}")
        
        if applicable_factors:
            # 使用最新的因子
            latest_factor = applicable_factors[-1]
            print(f"使用的复权因子: {latest_factor['date']} -> {latest_factor['qfq_factor']:.6f}")
            
            # 计算复权价格
            calculated_qfq_price = raw_close * latest_factor['qfq_factor']
            error = abs(calculated_qfq_price - expected_qfq_price)
            error_percent = (error / expected_qfq_price) * 100
            
            print(f"计算复权价: {calculated_qfq_price:.2f}")
            print(f"期望复权价: {expected_qfq_price:.2f}")
            print(f"误差: {error:.2f} ({error_percent:.2f}%)")
            
            # 尝试其他因子
            print("尝试其他因子:")
            for factor in applicable_factors[-3:]:  # 显示最近3个因子
                test_price = raw_close * factor['qfq_factor']
                test_error = abs(test_price - expected_qfq_price)
                test_error_percent = (test_error / expected_qfq_price) * 100
                print(f"  {factor['date']}: {test_price:.2f} (误差: {test_error_percent:.2f}%)")
        else:
            print("❌ 未找到适用的复权因子")

if __name__ == "__main__":
    debug_adj_factor_accuracy() 