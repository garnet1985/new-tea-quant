#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from app.data_source.data_source_manager import DataSourceManager
from utils.db.db_manager import get_sync_db_manager
from datetime import datetime

def generate_comparison_excel(ts_code='000001.SZ', code='000001', stock_name='平安银行'):
    # 初始化
    db = get_sync_db_manager()
    dsm = DataSourceManager(db, is_verbose=True)
    tu = dsm.sources['tushare']
    ak = dsm.sources['akshare']
    ak.inject_dependency(tu)
    
    print(f"=== 生成{stock_name}2021-2024年数据对比Excel ===")
    
    # 定义年份列表
    years = [2021, 2023, 2024]
    all_data = []
    
    for year in years:
        start_date = f'{year}0101'
        end_date = f'{year}1231'
        print(f"\n=== 处理 {year} 年数据 ===")
    
        print(f"1. 获取本地数据库的{year}年日线收盘价...")
        # 获取本地数据库的日线数据
        local_data = []
        for date in pd.date_range(start=start_date, end=end_date, freq='D'):
            date_str = date.strftime('%Y%m%d')
            close_price = ak.storage.get_close_price(ts_code, date_str)
            if close_price:
                local_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'local_close': close_price
                })
        
        local_df = pd.DataFrame(local_data)
        print(f"本地数据行数: {len(local_df)}")
        
        print(f"2. 获取AKShare的{year}年QFQ日线收盘价...")
        # 获取AKShare的QFQ数据
        try:
            akshare_data = ak.api(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            # 处理AKShare数据
            akshare_df = akshare_data.copy()
            akshare_df['date'] = pd.to_datetime(akshare_df['日期']).dt.strftime('%Y-%m-%d')
            akshare_df = akshare_df[['date', '收盘']].rename(columns={'收盘': 'akshare_qfq_close'})
            print(f"AKShare数据行数: {len(akshare_df)}")
        except Exception as e:
            print(f"AKShare数据获取失败: {e}")
            akshare_df = pd.DataFrame(columns=['date', 'akshare_qfq_close'])
        
        print(f"3. 获取Tushare的{year}年QFQ因子...")
        # 获取Tushare的QFQ因子
        try:
            tushare_factors = tu.api.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
            print(f"Tushare原始数据行数: {len(tushare_factors)}")
            
            tushare_df = tushare_factors.copy()
            tushare_df['date'] = pd.to_datetime(tushare_df['trade_date']).dt.strftime('%Y-%m-%d')
            tushare_df = tushare_df[['date', 'adj_factor']].rename(columns={'adj_factor': 'tushare_qfq_factor'})
            print(f"Tushare因子数据行数: {len(tushare_df)}")
        except Exception as e:
            print(f"Tushare因子数据获取失败: {e}")
            tushare_df = pd.DataFrame(columns=['date', 'tushare_qfq_factor'])
        
        print(f"4. 合并{year}年数据...")
        # 合并所有数据
        year_df = local_df.copy()
        
        if not akshare_df.empty:
            year_df = year_df.merge(akshare_df, on='date', how='left')
        else:
            year_df['akshare_qfq_close'] = None
        
        if not tushare_df.empty:
            year_df = year_df.merge(tushare_df, on='date', how='left')
        else:
            year_df['tushare_qfq_factor'] = None
        
        # 添加到总数据
        all_data.append(year_df)
        print(f"{year}年数据处理完成，行数: {len(year_df)}")
    
    # 合并所有年份的数据
    print("\n5. 合并所有年份数据...")
    result_df = pd.concat(all_data, ignore_index=True)
    result_df = result_df.sort_values('date')
    
    print("6. 生成Excel文件...")
    # 生成Excel文件
    filename = f'{stock_name}_2021-2024年数据对比_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # 写入数据
        result_df.to_excel(writer, sheet_name='数据对比', index=False)
        
        # 获取工作表对象
        worksheet = writer.sheets['数据对比']
        
        # 设置列宽
        worksheet.column_dimensions['A'].width = 12  # 日期
        worksheet.column_dimensions['B'].width = 15  # 本地收盘价
        worksheet.column_dimensions['C'].width = 15  # AKShare QFQ收盘价
        worksheet.column_dimensions['D'].width = 15  # Tushare QFQ因子
    
    print(f"Excel文件已生成: {filename}")
    print(f"总数据行数: {len(result_df)}")
    
    # 显示前几行数据
    print("\n前5行数据预览:")
    print(result_df.head())
    
    # 显示数据统计
    print("\n数据统计:")
    print(f"本地数据有效行数: {result_df['local_close'].notna().sum()}")
    print(f"AKShare数据有效行数: {result_df['akshare_qfq_close'].notna().sum()}")
    print(f"Tushare因子有效行数: {result_df['tushare_qfq_factor'].notna().sum()}")
    
    # 按年份统计
    print("\n按年份统计:")
    for year in years:
        year_data = result_df[result_df['date'].str.startswith(str(year))]
        print(f"{year}年: {len(year_data)}行数据")
    
    return filename

if __name__ == "__main__":
    # 定义要处理的股票列表
    stocks = [
        {'ts_code': '688310.SH', 'code': '688310', 'name': '迈得医疗'},
        {'ts_code': '000999.SZ', 'code': '000999', 'name': '华润三九'},
        {'ts_code': '300303.SZ', 'code': '300303', 'name': '聚飞光电'}
    ]
    
    # 为每只股票生成Excel文件
    for stock in stocks:
        print(f"\n{'='*50}")
        print(f"开始处理: {stock['name']} ({stock['ts_code']})")
        print(f"{'='*50}")
        try:
            filename = generate_comparison_excel(
                ts_code=stock['ts_code'],
                code=stock['code'],
                stock_name=stock['name']
            )
            print(f"✅ {stock['name']} Excel文件生成成功: {filename}")
        except Exception as e:
            print(f"❌ {stock['name']} 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print("所有股票处理完成！")
    print(f"{'='*50}") 