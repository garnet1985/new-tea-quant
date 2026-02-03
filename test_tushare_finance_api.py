#!/usr/bin/env python3
"""
测试 Tushare fina_indicator API，查看是否返回重复记录
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from userspace.data_source.providers.tushare.provider import TushareProvider
from core.modules.data_source.data_class.config import DataSourceConfig
import pandas as pd

def test_finance_api():
    """测试 Tushare fina_indicator API"""
    
    # 初始化 provider
    # 尝试从文件或环境变量读取 token
    from core.infra.project_context import PathManager
    
    token = None
    # 1. 尝试从文件读取
    auth_token_path = PathManager.data_source_provider("tushare") / "auth_token.txt"
    if auth_token_path.exists():
        try:
            with open(auth_token_path, 'r') as f:
                token = f.read().strip()
            print(f"✅ 从文件读取 token: {auth_token_path}")
        except Exception as e:
            print(f"⚠️  读取 token 文件失败: {e}")
    
    # 2. 如果文件没有，尝试从环境变量读取
    if not token:
        token = os.getenv("TUSHARE_TOKEN")
        if token:
            print(f"✅ 从环境变量读取 token")
    
    if not token:
        print("❌ 无法获取 Tushare token")
        print("   请设置以下之一：")
        print(f"   1. 文件: {auth_token_path}")
        print("   2. 环境变量: TUSHARE_TOKEN")
        return
    
    provider_config = {"token": token}
    provider = TushareProvider(provider_config)
    
    # 测试股票：000045.SZ（从日志中看到的）
    ts_code = "000045.SZ"
    
    # 测试一个季度：2015Q3（从日志中看到的）
    # Tushare API 需要日期格式，我们传入季度范围
    # 2015Q3 对应 20150701 到 20150930
    start_date = "20150701"
    end_date = "20150930"
    
    print(f"🔍 测试股票: {ts_code}")
    print(f"📅 日期范围: {start_date} 到 {end_date}")
    print(f"📊 预期季度: 2015Q3")
    print("-" * 80)
    
    # 调用 API
    try:
        result = provider.get_finance_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if result is None:
            print("❌ API 返回 None")
            return
        
        if isinstance(result, pd.DataFrame):
            print(f"✅ API 返回 DataFrame，共 {len(result)} 行")
            print(f"\n📋 列名: {list(result.columns)}")
            print(f"\n📊 数据预览（前10行）:")
            print(result.head(10).to_string())
            
            # 检查 end_date 列
            if 'end_date' in result.columns:
                print(f"\n🔍 end_date 列的唯一值:")
                unique_end_dates = result['end_date'].unique()
                print(f"   唯一 end_date 数量: {len(unique_end_dates)}")
                print(f"   唯一 end_date 列表: {sorted(unique_end_dates)}")
                
                # 检查是否有重复的 end_date
                end_date_counts = result['end_date'].value_counts()
                duplicates = end_date_counts[end_date_counts > 1]
                if len(duplicates) > 0:
                    print(f"\n⚠️  发现重复的 end_date:")
                    for end_date, count in duplicates.items():
                        print(f"   {end_date}: {count} 条记录")
                        # 显示这些重复记录的详细信息
                        dup_records = result[result['end_date'] == end_date]
                        print(f"   重复记录详情:")
                        print(dup_records.to_string())
                else:
                    print(f"\n✅ 没有发现重复的 end_date")
            
            # 检查是否有完全重复的行
            print(f"\n🔍 检查完全重复的行:")
            duplicates = result[result.duplicated()]
            if len(duplicates) > 0:
                print(f"⚠️  发现 {len(duplicates)} 行完全重复的记录")
                print(duplicates.to_string())
            else:
                print(f"✅ 没有发现完全重复的行")
            
            # 详细比较两条记录，看看是否有任何差异
            if len(result) == 2:
                print(f"\n🔍 详细比较两条记录:")
                row0 = result.iloc[0]
                row1 = result.iloc[1]
                
                # 检查每个字段是否有差异
                differences = []
                for col in result.columns:
                    val0 = row0[col]
                    val1 = row1[col]
                    # 处理 NaN 值
                    import pandas as pd
                    if pd.isna(val0) and pd.isna(val1):
                        continue
                    if val0 != val1:
                        differences.append({
                            'column': col,
                            'row0': val0,
                            'row1': val1
                        })
                
                if differences:
                    print(f"⚠️  发现 {len(differences)} 个字段有差异:")
                    for diff in differences:
                        print(f"   {diff['column']}: row0={diff['row0']}, row1={diff['row1']}")
                else:
                    print(f"✅ 两条记录在所有字段上都完全相同（包括 NaN 值）")
                
                # 检查 DataFrame 的索引
                print(f"\n🔍 DataFrame 索引信息:")
                print(f"   row0 index: {result.index[0]}")
                print(f"   row1 index: {result.index[1]}")
                
                # 检查是否有隐藏的元数据差异
                print(f"\n🔍 检查数据类型:")
                print(f"   row0 dtypes: {row0.dtype if hasattr(row0, 'dtype') else 'N/A'}")
                print(f"   row1 dtypes: {row1.dtype if hasattr(row1, 'dtype') else 'N/A'}")
            
            # 检查是否有部分字段重复但其他字段不同的情况
            if 'end_date' in result.columns:
                print(f"\n🔍 按 end_date 分组统计:")
                grouped = result.groupby('end_date').size()
                print(grouped.to_string())
                
        else:
            print(f"⚠️  API 返回类型: {type(result)}")
            print(f"   内容: {result}")
            
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_finance_api()
