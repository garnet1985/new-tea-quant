#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data_source.providers.akshare.main_service import AKShareService
from loguru import logger

def test_batch_fetch():
    service = AKShareService(is_verbose=True)
    
    print("=" * 60)
    print("测试分批获取复权因子数据")
    print("=" * 60)
    
    # 测试平安银行
    stock_code = '000001'
    start_date = '20080101'
    end_date = '20250802'
    
    print(f"\n1. 获取平安银行({stock_code})从{start_date}到{end_date}的复权因子")
    print("预计需要约18个批次，每个批次2次AKShare请求，总共约36次请求")
    
    print("\n2. 开始分批获取数据...")
    result = service.fetch_stock_factors(stock_code, start_date, end_date)
    
    if result is not None and not result.empty:
        print(f"\n3. 获取成功！")
        print(f"总数据条数: {len(result)}")
        print(f"日期范围: {result['日期'].min()} 到 {result['日期'].max()}")
        
        # 显示一些样本数据
        print(f"\n4. 样本数据:")
        print(result.head(10).to_string(index=False))
        
        # 检查因子变化
        print(f"\n5. 因子变化统计:")
        hfq_changes = result['hfq_factor'].diff().abs() > 0.001
        change_dates = result[hfq_changes]['日期'].tolist()
        print(f"后复权因子变化次数: {len(change_dates)}")
        print(f"变化日期: {change_dates[:10]}...")  # 只显示前10个
        
    else:
        print("\n3. 获取失败！")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_batch_fetch() 