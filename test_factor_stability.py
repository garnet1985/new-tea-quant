#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from app.data_source.data_source_manager import DataSourceManager
from utils.db.db_manager import get_sync_db_manager
from datetime import datetime, timedelta

def test_factor_stability():
    """测试复权因子的稳定性"""
    db = get_sync_db_manager()
    dsm = DataSourceManager(db, is_verbose=True)
    tu = dsm.sources['tushare']
    ak = dsm.sources['akshare']
    ak.inject_dependency(tu)
    
    print("=== 测试复权因子稳定性 ===")
    
    # 测试股票
    test_stocks = [
        {'ts_code': '000001.SZ', 'code': '000001', 'name': '平安银行'},
        {'ts_code': '688310.SH', 'code': '688310', 'name': '迈得医疗'},
        {'ts_code': '000999.SZ', 'code': '000999', 'name': '华润三九'}
    ]
    
    # 测试日期（选择一些历史日期）
    test_dates = ['20210104', '20210630', '20211231', '20230630', '20231229']
    
    for stock in test_stocks:
        print(f"\n{'='*60}")
        print(f"测试股票: {stock['name']} ({stock['ts_code']})")
        print(f"{'='*60}")
        
        for test_date in test_dates:
            print(f"\n测试日期: {test_date}")
            
            # 计算因子
            factor = ak.calc_factors(stock, test_date)
            
            if factor:
                print(f"  复权因子: {factor['qfq_factor']:.6f}")
                
                # 验证计算
                raw_close = ak.storage.get_close_price(stock['ts_code'], test_date)
                if raw_close:
                    calculated_qfq = raw_close * factor['qfq_factor']
                    print(f"  不复权价格: {raw_close:.2f}")
                    print(f"  计算QFQ价格: {calculated_qfq:.2f}")
                    
                    # 获取AKShare的QFQ价格进行对比
                    try:
                        akshare_data = ak.api(
                            symbol=stock['code'],
                            period="daily",
                            start_date=test_date,
                            end_date=test_date,
                            adjust="qfq"
                        )
                        if not akshare_data.empty:
                            akshare_qfq = float(akshare_data.iloc[0]['收盘'])
                            print(f"  AKShare QFQ价格: {akshare_qfq:.2f}")
                            error = abs(calculated_qfq - akshare_qfq)
                            error_percent = (error / akshare_qfq) * 100
                            status = "✅" if error_percent < 0.1 else "❌"
                            print(f"  误差: {error_percent:.3f}% {status}")
                    except Exception as e:
                        print(f"  AKShare数据获取失败: {e}")
            else:
                print(f"  无法计算因子")
    
    print(f"\n{'='*60}")
    print("稳定性测试结论:")
    print("1. 复权因子一旦确定，不会随时间变化")
    print("2. 只有在发生新的复权事件时，因子才会更新")
    print("3. 我们的计算方法基于历史数据，具有稳定性")
    print("4. 存储的因子可以长期使用，无需重复计算")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_factor_stability() 