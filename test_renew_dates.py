#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from app.data_source.data_source_manager import DataSourceManager
from utils.db.db_manager import get_sync_db_manager

def test_renew_dates():
    """测试get_renew_dates函数"""
    db = get_sync_db_manager()
    dsm = DataSourceManager(db, is_verbose=True)
    tu = dsm.sources['tushare']
    ak = dsm.sources['akshare']
    ak.inject_dependency(tu)
    
    print("=== 测试get_renew_dates函数 ===")
    
    # 测试股票
    stock = {'ts_code': '000001.SZ', 'code': '000001', 'name': '平安银行'}
    
    print(f"测试股票: {stock['name']} ({stock['ts_code']})")
    
    # 获取Tushare的因子数据
    print("\n1. 获取Tushare的因子数据...")
    try:
        factors = tu.api.adj_factor(ts_code=stock['ts_code'], start_date='20210101', end_date='20241231')
        print(f"Tushare因子数据行数: {len(factors)}")
        
        # 获取所有因子变化日期
        all_changing_dates = ak.service.get_factor_changing_dates(factors)
        print(f"所有因子变化日期数量: {len(all_changing_dates)}")
        print("前5个因子变化日期:", all_changing_dates[:5])
        
        # 测试不同的数据库最新日期
        test_cases = [
            '20210101',  # 很早的日期，应该返回大部分日期
            '20210630',  # 中间的日期
            '20231231',  # 很晚的日期，应该返回很少或没有日期
            '20250101'   # 未来的日期，应该返回空列表
        ]
        
        for latest_db_date in test_cases:
            print(f"\n2. 测试数据库最新日期: {latest_db_date}")
            
            renew_dates = ak.service.get_renew_dates(latest_db_date, factors)
            print(f"需要更新的日期数量: {len(renew_dates)}")
            
            if renew_dates:
                print("需要更新的日期:")
                for i, date in enumerate(renew_dates[:5]):  # 只显示前5个
                    print(f"  {i+1}. {date}")
                if len(renew_dates) > 5:
                    print(f"  ... 还有 {len(renew_dates) - 5} 个日期")
            else:
                print("  无需更新")
            
            # 验证结果
            if renew_dates:
                for date in renew_dates:
                    if date <= latest_db_date:
                        print(f"  ❌ 错误: {date} 不应该大于 {latest_db_date}")
                        break
                else:
                    print(f"  ✅ 验证通过: 所有日期都大于 {latest_db_date}")
            else:
                print(f"  ✅ 验证通过: 没有需要更新的日期")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_renew_dates() 