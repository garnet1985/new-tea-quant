#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.data_source.providers.akshare.main import AKShare
from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.main import Tushare
from loguru import logger
import pandas as pd
import random

def compare_raw_data():
    """对比本地数据库和AKShare的裸数据"""
    
    # 初始化
    db = get_sync_db_manager()
    ak = AKShare(db, is_verbose=True)
    tu = Tushare(db, is_verbose=True)
    ak.inject_dependency(tu)
    
    # 测试日期列表
    test_dates = [
        '2019-09-26', '2018-08-16', '2021-07-08', '2022-12-12', 
        '2017-09-06', '2019-10-14', '2020-02-03', '2020-04-30',
        '2017-05-15', '2024-08-26', '2024-09-25'
    ]
    
    print("=== 本地数据库 vs AKShare 裸数据对比 ===")
    print("股票: 平安银行 (000001.SZ)")
    print()
    
    results = []
    
    for test_date in test_dates:
        print(f"--- {test_date} ---")
        
        # 从本地数据库获取裸数据
        local_raw_close = ak.storage.get_close_price('000001.SZ', test_date.replace('-', ''))
        
        # 从AKShare获取裸数据
        try:
            akshare_data = ak.api(
                symbol='000001',
                period="daily",
                start_date=test_date.replace('-', ''),
                end_date=test_date.replace('-', ''),
                adjust=""
            )
            
            if not akshare_data.empty:
                akshare_raw_close = float(akshare_data.iloc[0]['收盘'])
            else:
                akshare_raw_close = None
                
        except Exception as e:
            print(f"AKShare获取数据失败: {e}")
            akshare_raw_close = None
        
        # 计算差异
        if local_raw_close is not None and akshare_raw_close is not None:
            diff = abs(local_raw_close - akshare_raw_close)
            diff_percent = (diff / local_raw_close) * 100
            
            print(f"本地数据库: {local_raw_close:.2f}")
            print(f"AKShare数据: {akshare_raw_close:.2f}")
            print(f"差异: {diff:.2f} ({diff_percent:.2f}%)")
            
            is_same = diff_percent < 0.1  # 差异小于0.1%认为相同
            status = "✅" if is_same else "❌"
            print(f"{status} 数据一致性: {'相同' if is_same else '不同'}")
            
            results.append({
                'date': test_date,
                'local_close': local_raw_close,
                'akshare_close': akshare_raw_close,
                'diff': diff,
                'diff_percent': diff_percent,
                'is_same': is_same
            })
        else:
            print(f"本地数据库: {local_raw_close}")
            print(f"AKShare数据: {akshare_raw_close}")
            print("❌ 数据获取失败")
        
        print()
    
    # 统计结果
    if results:
        same_count = sum(1 for r in results if r['is_same'])
        total_count = len(results)
        same_rate = (same_count / total_count) * 100
        
        print("=== 数据一致性统计 ===")
        print(f"总测试日期: {total_count}")
        print(f"数据相同: {same_count}")
        print(f"数据不同: {total_count - same_count}")
        print(f"一致性: {same_rate:.1f}%")
        
        if same_rate >= 90:
            print("🎉 本地数据库和AKShare数据高度一致！")
        elif same_rate >= 80:
            print("✅ 本地数据库和AKShare数据基本一致")
        elif same_rate >= 70:
            print("⚠️  本地数据库和AKShare数据部分一致")
        else:
            print("❌ 本地数据库和AKShare数据差异较大")
        
        # 显示差异较大的数据
        large_diff_results = [r for r in results if r['diff_percent'] > 1.0]
        if large_diff_results:
            print("\n=== 差异较大的数据 (>1%) ===")
            for result in large_diff_results:
                print(f"{result['date']}: 本地{result['local_close']:.2f} vs AKShare{result['akshare_close']:.2f} (差异: {result['diff_percent']:.2f}%)")

if __name__ == "__main__":
    compare_raw_data() 