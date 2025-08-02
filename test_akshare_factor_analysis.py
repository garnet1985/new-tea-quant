#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data_source.providers.akshare.main_service import AKShareService
import pandas as pd
from loguru import logger

def analyze_factor_changes():
    service = AKShareService(is_verbose=True)
    
    print("=" * 60)
    print("详细分析复权因子变化")
    print("=" * 60)
    
    # 获取平安银行数据
    stock_code = '000001'
    start_date = '20080101'
    end_date = '20250802'
    
    print(f"\n1. 获取平安银行({stock_code})复权因子数据...")
    result = service.fetch_stock_factors(stock_code, start_date, end_date)
    
    if result is None or result.empty:
        print("获取数据失败！")
        return
    
    print(f"\n2. 数据概览:")
    print(f"总数据条数: {len(result)}")
    print(f"日期范围: {result['日期'].min()} 到 {result['日期'].max()}")
    
    # 分析后复权因子变化
    print(f"\n3. 后复权因子变化分析:")
    
    # 计算因子变化
    result['hfq_factor_diff'] = result['hfq_factor'].diff()
    result['hfq_factor_change'] = result['hfq_factor_diff'].abs() > 0.001
    
    # 找出真正有变化的日期
    significant_changes = result[result['hfq_factor_change']]
    
    print(f"总交易日数: {len(result)}")
    print(f"因子有变化的日期数: {len(significant_changes)}")
    print(f"变化比例: {len(significant_changes)/len(result)*100:.2f}%")
    
    # 显示前20个变化点
    print(f"\n4. 前20个因子变化点:")
    change_summary = significant_changes[['日期', 'hfq_factor', 'hfq_factor_diff']].head(20)
    for _, row in change_summary.iterrows():
        print(f"{row['日期']}: {row['hfq_factor']:.6f} (变化: {row['hfq_factor_diff']:+.6f})")
    
    # 分析变化幅度
    print(f"\n5. 变化幅度分析:")
    significant_changes['change_ratio'] = (significant_changes['hfq_factor_diff'] / 
                                          significant_changes['hfq_factor'].shift(1) * 100)
    
    print(f"最大变化幅度: {significant_changes['change_ratio'].max():.2f}%")
    print(f"最小变化幅度: {significant_changes['change_ratio'].min():.2f}%")
    print(f"平均变化幅度: {significant_changes['change_ratio'].mean():.2f}%")
    
    # 按年份统计变化次数
    print(f"\n6. 按年份统计因子变化次数:")
    significant_changes['year'] = pd.to_datetime(significant_changes['日期']).dt.year
    yearly_changes = significant_changes.groupby('year').size()
    
    for year, count in yearly_changes.items():
        print(f"{year}年: {count}次变化")
    
    # 检查是否有连续变化
    print(f"\n7. 连续变化分析:")
    result['consecutive_change'] = result['hfq_factor_change'] & result['hfq_factor_change'].shift(1)
    consecutive_changes = result[result['consecutive_change']]
    print(f"连续两天都有变化的次数: {len(consecutive_changes)}")
    
    if len(consecutive_changes) > 0:
        print("连续变化的日期:")
        for _, row in consecutive_changes.head(10).iterrows():
            print(f"  {row['日期']}: {row['hfq_factor']:.6f}")
    
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)

if __name__ == "__main__":
    analyze_factor_changes() 