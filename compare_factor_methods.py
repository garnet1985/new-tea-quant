#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.data_source.providers.akshare.main import AKShare
from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.main import Tushare
from loguru import logger
import pandas as pd

def compare_factor_methods():
    """对比两种复权因子获取方法"""
    
    # 初始化
    db = get_sync_db_manager()
    ak = AKShare(db, is_verbose=True)
    tu = Tushare(db, is_verbose=True)
    ak.inject_dependency(tu)
    
    # 日志中的复权因子（第一次测试使用）
    log_factors = [
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
    log_factors.sort(key=lambda x: x['date'])
    
    def get_log_factor(target_date):
        """从日志因子中找到适用的因子"""
        target_date_str = target_date.replace('-', '')
        max_factor_date = None
        max_factor = None
        
        for factor in log_factors:
            factor_date = factor['date']
            if factor_date <= target_date_str:
                if max_factor_date is None or factor_date > max_factor_date:
                    max_factor_date = factor_date
                    max_factor = factor['qfq_factor']
        
        return max_factor
    
    def get_realtime_factor(target_date):
        """实时计算复权因子"""
        try:
            # 获取裸数据
            raw_close = ak.storage.get_close_price('000001.SZ', target_date.replace('-', ''))
            
            # 获取前复权数据
            qfq_data = ak.api(
                symbol='000001',
                period="daily",
                start_date=target_date.replace('-', ''),
                end_date=target_date.replace('-', ''),
                adjust="qfq"
            )
            
            if not qfq_data.empty and raw_close is not None:
                qfq_close = float(qfq_data.iloc[0]['收盘'])
                return qfq_close / raw_close
            else:
                return None
        except Exception as e:
            print(f"实时计算失败: {e}")
            return None
    
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
    
    print("=== 两种复权因子方法对比 ===")
    print("方法1: 使用日志中的历史因子")
    print("方法2: 实时计算因子")
    print()
    
    results = []
    
    for test_date, expected_price in test_cases:
        print(f"--- {test_date} ---")
        
        # 获取裸数据
        raw_close = ak.storage.get_close_price('000001.SZ', test_date.replace('-', ''))
        print(f"裸数据收盘价: {raw_close}")
        print(f"期望前复权价格: {expected_price}")
        
        # 方法1: 日志因子
        log_factor = get_log_factor(test_date)
        if log_factor:
            log_calculated_price = raw_close * log_factor
            log_error = abs(log_calculated_price - expected_price)
            log_error_percent = (log_error / expected_price) * 100
            print(f"方法1 - 日志因子: {log_factor:.6f}")
            print(f"方法1 - 计算价格: {log_calculated_price:.2f}")
            print(f"方法1 - 误差: {log_error:.2f} ({log_error_percent:.2f}%)")
        else:
            print("方法1 - 未找到适用因子")
            log_error_percent = float('inf')
        
        # 方法2: 实时因子
        realtime_factor = get_realtime_factor(test_date)
        if realtime_factor:
            realtime_calculated_price = raw_close * realtime_factor
            realtime_error = abs(realtime_calculated_price - expected_price)
            realtime_error_percent = (realtime_error / expected_price) * 100
            print(f"方法2 - 实时因子: {realtime_factor:.6f}")
            print(f"方法2 - 计算价格: {realtime_calculated_price:.2f}")
            print(f"方法2 - 误差: {realtime_error:.2f} ({realtime_error_percent:.2f}%)")
        else:
            print("方法2 - 计算失败")
            realtime_error_percent = float('inf')
        
        # 对比
        if log_error_percent < realtime_error_percent:
            print("✅ 方法1更准确")
        elif realtime_error_percent < log_error_percent:
            print("✅ 方法2更准确")
        else:
            print("⚠️  两种方法准确度相同")
        
        results.append({
            'date': test_date,
            'log_factor': log_factor,
            'log_error_percent': log_error_percent,
            'realtime_factor': realtime_factor,
            'realtime_error_percent': realtime_error_percent
        })
        
        print()
    
    # 统计结果
    log_accurate = sum(1 for r in results if r['log_error_percent'] < 5)
    realtime_accurate = sum(1 for r in results if r['realtime_error_percent'] < 5)
    total = len(results)
    
    print("=== 统计结果 ===")
    print(f"方法1 (日志因子) 准确率: {log_accurate}/{total} ({log_accurate/total*100:.1f}%)")
    print(f"方法2 (实时因子) 准确率: {realtime_accurate}/{total} ({realtime_accurate/total*100:.1f}%)")
    
    if realtime_accurate > log_accurate:
        print("🎉 方法2 (实时因子) 更准确！")
    elif log_accurate > realtime_accurate:
        print("🎉 方法1 (日志因子) 更准确！")
    else:
        print("⚠️  两种方法准确度相同")

if __name__ == "__main__":
    compare_factor_methods() 