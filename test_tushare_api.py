#!/usr/bin/env python3
"""
Tushare API 测试脚本 - 诊断API调用问题
"""
import tushare as ts
from loguru import logger
import pandas as pd
import time

def test_tushare_connection():
    """测试Tushare连接"""
    print("🔍 测试Tushare连接...")
    
    try:
        # 读取token
        with open('app/data_source/providers/tushare/auth/token.txt', 'r') as f:
            token = f.read().strip()
        
        print(f"✅ Token读取成功: {token[:10]}...")
        
        # 设置token
        ts.set_token(token)
        print("✅ Token设置成功")
        
        # 创建API实例
        api = ts.pro_api()
        print("✅ API实例创建成功")
        
        return api
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return None

def test_stock_basic_api(api):
    """测试股票基础信息API"""
    print("\n📊 测试股票基础信息API...")
    
    try:
        # 测试1: 获取所有股票列表
        print("测试1: 获取所有股票列表")
        data1 = api.stock_basic(exchange='', list_status='L', fields='ts_code,name,area,industry,market,exchange,list_date')
        print(f"结果1: 数据类型: {type(data1)}")
        print(f"结果1: 数据形状: {data1.shape if hasattr(data1, 'shape') else 'N/A'}")
        print(f"结果1: 数据内容: {data1.head(3) if hasattr(data1, 'head') else data1}")
        
        # 测试2: 指定交易所
        print("\n测试2: 指定上海交易所")
        data2 = api.stock_basic(exchange='SSE', list_status='L', fields='ts_code,name,area,industry,market,exchange,list_date')
        print(f"结果2: 数据类型: {type(data2)}")
        print(f"结果2: 数据形状: {data2.shape if hasattr(data2, 'shape') else 'N/A'}")
        print(f"结果2: 数据内容: {data2.head(3) if hasattr(data2, 'head') else data2}")
        
        # 测试3: 指定深圳交易所
        print("\n测试3: 指定深圳交易所")
        data3 = api.stock_basic(exchange='SZSE', list_status='L', fields='ts_code,name,area,industry,market,exchange,list_date')
        print(f"结果3: 数据类型: {type(data3)}")
        print(f"结果3: 数据形状: {data3.shape if hasattr(data3, 'shape') else 'N/A'}")
        print(f"结果3: 数据内容: {data3.head(3) if hasattr(data3, 'head') else data3}")
        
        # 测试4: 不指定交易所，但指定状态
        print("\n测试4: 不指定交易所，指定上市状态")
        data4 = api.stock_basic(list_status='L', fields='ts_code,name,area,industry,market,exchange,list_date')
        print(f"结果4: 数据类型: {type(data4)}")
        print(f"结果4: 数据形状: {data4.shape if hasattr(data4, 'shape') else 'N/A'}")
        print(f"结果4: 数据内容: {data4.head(3) if hasattr(data4, 'head') else data4}")
        
        return data1
        
    except Exception as e:
        print(f"❌ 股票基础信息API测试失败: {e}")
        return None

def test_daily_kline_api(api):
    """测试日K线API"""
    print("\n📈 测试日K线API...")
    
    try:
        # 测试获取单只股票的日K线
        print("测试: 获取平安银行(000001.SZ)的日K线")
        data = api.daily(ts_code='000001.SZ', start_date='20240101', end_date='20240131')
        print(f"结果: 数据类型: {type(data)}")
        print(f"结果: 数据形状: {data.shape if hasattr(data, 'shape') else 'N/A'}")
        print(f"结果: 数据内容: {data.head(3) if hasattr(data, 'head') else data}")
        
        return data
        
    except Exception as e:
        print(f"❌ 日K线API测试失败: {e}")
        return None

def test_trade_cal_api(api):
    """测试交易日历API"""
    print("\n📅 测试交易日历API...")
    
    try:
        # 测试获取交易日历
        print("测试: 获取2024年1月的交易日历")
        data = api.trade_cal(exchange='SSE', start_date='20240101', end_date='20240131')
        print(f"结果: 数据类型: {type(data)}")
        print(f"结果: 数据形状: {data.shape if hasattr(data, 'shape') else 'N/A'}")
        print(f"结果: 数据内容: {data.head(5) if hasattr(data, 'head') else data}")
        
        return data
        
    except Exception as e:
        print(f"❌ 交易日历API测试失败: {e}")
        return None

def test_api_limits(api):
    """测试API限制"""
    print("\n⏱️ 测试API限制...")
    
    try:
        # 测试连续调用
        print("测试: 连续调用API 5次")
        for i in range(5):
            start_time = time.time()
            data = api.stock_basic(exchange='SSE', list_status='L', fields='ts_code,name')
            end_time = time.time()
            print(f"调用 {i+1}: 耗时 {end_time - start_time:.2f}秒, 数据量: {len(data) if hasattr(data, '__len__') else 'N/A'}")
            time.sleep(0.1)  # 短暂延迟
            
    except Exception as e:
        print(f"❌ API限制测试失败: {e}")

def check_tushare_version():
    """检查Tushare版本"""
    print("\n📦 检查Tushare版本...")
    try:
        print(f"Tushare版本: {ts.__version__}")
        print(f"Pandas版本: {pd.__version__}")
    except Exception as e:
        print(f"❌ 版本检查失败: {e}")

def main():
    """主函数"""
    print("🚀 Tushare API 诊断测试")
    print("=" * 60)
    
    # 检查版本
    check_tushare_version()
    
    # 测试连接
    api = test_tushare_connection()
    if not api:
        print("❌ 无法创建API实例，测试终止")
        return
    
    # 测试各种API
    test_stock_basic_api(api)
    test_daily_kline_api(api)
    test_trade_cal_api(api)
    test_api_limits(api)
    
    print("\n✅ 测试完成！")
    print("\n📚 常见问题排查:")
    print("1. Token是否有效 - 检查token.txt文件")
    print("2. 网络连接是否正常")
    print("3. API调用频率是否超限")
    print("4. 参数格式是否正确")
    print("5. Tushare版本是否兼容")

if __name__ == "__main__":
    main()
