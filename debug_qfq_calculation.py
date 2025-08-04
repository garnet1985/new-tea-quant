#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.data_source.providers.akshare.main import AKShare
from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.main import Tushare
from loguru import logger
import pandas as pd

def debug_qfq_calculation():
    """调试前复权计算逻辑"""
    
    # 初始化
    db = get_sync_db_manager()
    ak = AKShare(db, is_verbose=True)
    tu = Tushare(db, is_verbose=True)
    ak.inject_dependency(tu)
    
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
    
    print("=== 前复权计算详细调试 ===")
    print("股票: 平安银行 (000001.SZ)")
    print()
    
    for test_date, expected_qfq_price in test_cases:
        print(f"--- {test_date} ---")
        print(f"期望前复权价格: {expected_qfq_price}")
        
        # 1. 获取裸数据
        raw_close = ak.storage.get_close_price('000001.SZ', test_date.replace('-', ''))
        print(f"裸数据收盘价: {raw_close}")
        
        # 2. 从AKShare获取前复权数据
        try:
            qfq_data = ak.api(
                symbol='000001',
                period="daily",
                start_date=test_date.replace('-', ''),
                end_date=test_date.replace('-', ''),
                adjust="qfq"
            )
            
            if not qfq_data.empty:
                akshare_qfq_close = float(qfq_data.iloc[0]['收盘'])
                print(f"AKShare前复权价格: {akshare_qfq_close}")
                
                # 3. 计算复权因子
                calculated_factor = akshare_qfq_close / raw_close
                print(f"计算得到的复权因子: {calculated_factor:.6f}")
                
                # 4. 验证计算
                calculated_qfq_price = raw_close * calculated_factor
                print(f"验证计算的前复权价格: {calculated_qfq_price:.2f}")
                
                # 5. 与期望值比较
                error_vs_expected = abs(calculated_qfq_price - expected_qfq_price)
                error_percent_vs_expected = (error_vs_expected / expected_qfq_price) * 100
                
                error_vs_akshare = abs(calculated_qfq_price - akshare_qfq_close)
                error_percent_vs_akshare = (error_vs_akshare / akshare_qfq_close) * 100
                
                print(f"与期望值误差: {error_vs_expected:.2f} ({error_percent_vs_expected:.2f}%)")
                print(f"与AKShare误差: {error_vs_akshare:.2f} ({error_percent_vs_akshare:.2f}%)")
                
                # 6. 分析
                if error_percent_vs_akshare < 0.1:
                    print("✅ 复权因子计算正确")
                else:
                    print("❌ 复权因子计算有问题")
                
                if error_percent_vs_expected < 5:
                    print("✅ 与期望值基本一致")
                else:
                    print("❌ 与期望值差异较大")
                    
            else:
                print("❌ AKShare返回空数据")
                
        except Exception as e:
            print(f"❌ AKShare获取数据失败: {e}")
        
        print()

if __name__ == "__main__":
    debug_qfq_calculation() 