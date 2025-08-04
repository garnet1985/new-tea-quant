#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from app.data_source.data_source_manager import DataSourceManager
from utils.db.db_manager import get_sync_db_manager
from datetime import datetime

def test_factor_change_mechanism():
    """测试复权事件发生时因子的变化机制"""
    db = get_sync_db_manager()
    dsm = DataSourceManager(db, is_verbose=True)
    tu = dsm.sources['tushare']
    ak = dsm.sources['akshare']
    ak.inject_dependency(tu)
    
    print("=== 复权因子变化机制测试 ===")
    
    # 测试股票
    stock = {'ts_code': '000001.SZ', 'code': '000001', 'name': '平安银行'}
    
    print(f"测试股票: {stock['name']} ({stock['ts_code']})")
    
    # 获取Tushare的复权因子变化历史
    print("\n1. 获取Tushare的复权因子变化历史...")
    try:
        factors = tu.api.adj_factor(ts_code=stock['ts_code'], start_date='20210101', end_date='20241231')
        
        # 找出因子变化的日期
        factors_sorted = factors.sort_values('trade_date')
        prev_factor = None
        change_dates = []
        
        for _, row in factors_sorted.iterrows():
            current_factor = float(row['adj_factor'])
            trade_date = str(row['trade_date'])
            
            if prev_factor is not None and current_factor != prev_factor:
                change_dates.append({
                    'date': trade_date,
                    'old_factor': prev_factor,
                    'new_factor': current_factor
                })
            prev_factor = current_factor
        
        print(f"发现 {len(change_dates)} 次复权因子变化:")
        for i, change in enumerate(change_dates[:5]):  # 只显示前5次
            print(f"  {i+1}. {change['date']}: {change['old_factor']:.6f} -> {change['new_factor']:.6f}")
        
        if len(change_dates) > 5:
            print(f"  ... 还有 {len(change_dates) - 5} 次变化")
        
    except Exception as e:
        print(f"获取Tushare因子历史失败: {e}")
        return
    
    # 测试特定日期的因子计算
    print("\n2. 测试特定日期的因子计算...")
    test_dates = ['20210104', '20210630', '20211231']
    
    for test_date in test_dates:
        print(f"\n测试日期: {test_date}")
        
        # 计算该日期的因子
        factor = ak.calc_factors(stock, test_date)
        
        if factor:
            print(f"  计算得到的因子: {factor['qfq_factor']:.6f}")
            
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
    print("复权因子变化机制总结:")
    print("1. 复权事件发生时，会在事件日期添加新的因子值")
    print("2. 历史因子值保持不变，不会被修改")
    print("3. 每个因子值对应一个时间段（从该日期到下一个复权事件）")
    print("4. 查询某日期的因子时，使用该日期之前最近的因子值")
    print("5. 这种机制确保了历史数据的一致性和稳定性")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_factor_change_mechanism() 