#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data_source.providers.akshare.main_service import AKShareService
import pandas as pd
import akshare as ak
from loguru import logger

def verify_factor_calculation():
    print("=" * 60)
    print("验证复权因子计算逻辑")
    print("=" * 60)
    
    # 获取平安银行最近一周的数据进行验证
    stock_code = '000001'
    start_date = '20250801'
    end_date = '20250802'
    
    print(f"\n1. 获取原始数据...")
    
    # 获取不复权数据
    raw_data = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust=""
    )
    
    # 获取后复权数据
    hfq_data = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="hfq"
    )
    
    print(f"不复权数据:")
    print(raw_data.to_string())
    print(f"\n后复权数据:")
    print(hfq_data.to_string())
    
    # 验证计算
    print(f"\n2. 验证因子计算:")
    merged_data = pd.merge(raw_data, hfq_data, on='日期', suffixes=('_raw', '_hfq'))
    
    for _, row in merged_data.iterrows():
        date = row['日期']
        raw_close = row['收盘_raw']
        hfq_close = row['收盘_hfq']
        
        # 计算因子
        calculated_factor = hfq_close / raw_close
        
        print(f"\n日期: {date}")
        print(f"  不复权收盘价: {raw_close}")
        print(f"  后复权收盘价: {hfq_close}")
        print(f"  计算得到的因子: {calculated_factor:.6f}")
        
        # 验证：用因子乘以不复权价格是否等于后复权价格
        verified_price = raw_close * calculated_factor
        print(f"  验证: {raw_close} × {calculated_factor:.6f} = {verified_price:.6f}")
        print(f"  误差: {abs(verified_price - hfq_close):.6f}")
    
    # 检查是否有其他复权类型
    print(f"\n3. 检查其他复权类型...")
    
    # 获取前复权数据
    qfq_data = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    
    print(f"前复权数据:")
    print(qfq_data.to_string())
    
    # 比较三种价格
    print(f"\n4. 三种价格对比:")
    all_data = pd.merge(raw_data, hfq_data, on='日期', suffixes=('_raw', '_hfq'))
    all_data = pd.merge(all_data, qfq_data, on='日期', suffixes=('', '_qfq'))
    
    for _, row in all_data.iterrows():
        date = row['日期']
        print(f"\n日期: {date}")
        print(f"  不复权: {row['收盘_raw']:.4f}")
        print(f"  前复权: {row['收盘_qfq']:.4f}")
        print(f"  后复权: {row['收盘_hfq']:.4f}")
        
        # 计算前复权因子
        qfq_factor = row['收盘_qfq'] / row['收盘_raw']
        print(f"  前复权因子: {qfq_factor:.6f}")
        
        # 计算后复权因子
        hfq_factor = row['收盘_hfq'] / row['收盘_raw']
        print(f"  后复权因子: {hfq_factor:.6f}")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

if __name__ == "__main__":
    verify_factor_calculation() 