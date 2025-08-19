#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试波谷检测算法
测试股票：000002.SZ
测试截止日期：2014年12月31日
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService
from app.analyzer.strategy.historicLow.strategy_settings import invest_settings


def preprocess_daily_data(daily_data: list) -> list:
    """
    数据预处理方法
    
    Args:
        daily_data: 原始日线数据列表
        
    Returns:
        list: 预处理后的数据列表
    """
    print("🧹 数据预处理：过滤负价格数据...")
    positive_data = []
    last_negative_date = None
    
    for record in daily_data:
        # 检查所有价格字段是否为正
        open_price = float(record['open'])
        high_price = float(record['highest'])
        low_price = float(record['lowest'])
        close_price = float(record['close'])
        
        if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
            last_negative_date = record['date']
            continue
        
        positive_data.append(record)
    
    if last_negative_date:
        print(f"⚠️  发现负价格数据，最后负价格日期: {last_negative_date}")
        print(f"📊 过滤前: {len(daily_data)} 条，过滤后: {len(positive_data)} 条")
    else:
        print("✅ 未发现负价格数据")
    
    return positive_data


def test_valley_detection():
    """测试波谷检测算法"""
    print("🔍 开始测试波谷检测算法")
    print(f"📊 测试股票: 000002.SZ")
    print(f"📅 测试截止日期: 2014年12月31日")
    print(f"⚙️  配置参数:")
    print(f"   - 最小跌幅阈值: {invest_settings['daily_data_requirements']['valley_detection']['min_drop_threshold'] * 100}%")
    print(f"   - 局部最低点判断范围: {invest_settings['daily_data_requirements']['valley_detection']['local_range_days']}天")
    print(f"   - 前期高点回溯天数: {invest_settings['daily_data_requirements']['valley_detection']['lookback_days']}天")
    print()
    
    try:
        # 初始化数据库管理器
        print("📡 初始化数据库管理器...")
        db_manager = DatabaseManager()
        
        # 获取000002.SZ的日线数据（到2014年12月31日）
        print("📥 获取日线数据...")
        stock_id = "000002.SZ"
        end_date = "20241231"
        
        # 获取日线数据
        stock_kline_model = db_manager.get_table_instance("stock_kline")
        adj_factor_model = db_manager.get_table_instance("adj_factor")
        
        # 获取原始K线数据
        klines = stock_kline_model.get_all_k_lines_by_term(stock_id, "daily")
        
        if not klines:
            print("❌ 未获取到K线数据")
            return
        
        # 过滤到2014年12月31日的数据
        filtered_klines = [k for k in klines if k['date'] <= end_date]
        
        if not filtered_klines:
            print("❌ 过滤后没有数据")
            return
        
        # 获取复权因子
        qfq_factors = adj_factor_model.get_stock_factors(stock_id)
        
        # 使用DataSourceService进行复权
        daily_data = DataSourceService.to_qfq(filtered_klines, qfq_factors)
        
        if not daily_data or len(daily_data) == 0:
            print("❌ 未获取到日线数据")
            return
        
        print(f"✅ 获取到 {len(daily_data)} 条日线数据")
        print(f"📅 数据范围: {daily_data[0]['date']} 到 {daily_data[-1]['date']}")
        
        # 数据预处理
        print("🧹 数据预处理...")
        daily_data = preprocess_daily_data(daily_data)
        
        print()
        
        # 初始化策略服务
        print("🔧 初始化策略服务...")
        strategy_service = HistoricLowService()
        
        # 测试波谷检测
        print("🔍 开始波谷检测...")
        valleys = strategy_service.find_valleys(daily_data)
        
        print(f"✅ 检测完成！找到 {len(valleys)} 个波谷")
        print()
        
        if valleys:
            print("📊 波谷详细信息:")
            print("-" * 80)
            
            # 先打印所有波谷的日期，方便在K线图上查看
            print("📍 波谷日期列表（按时间顺序）:")
            print("=" * 50)
            for i, valley in enumerate(valleys, 1):
                print(f"{i:2d}. {valley['date']} (跌幅: {valley['drop_rate']*100:.1f}%)")
            print("=" * 50)
            print()
            
            # 然后打印详细信息
            print("📋 波谷详细信息:")
            print("-" * 80)
            for i, valley in enumerate(valleys, 1):
                print(f"波谷 {i}:")
                print(f"  日期: {valley['date']}")
                print(f"  价格: {valley['price']:.4f}")
                print(f"  跌幅: {valley['drop_rate']*100:.2f}%")
                print(f"  左侧高点: {valley['left_peak']:.4f} ({valley['left_peak_date']})")
                print(f"  数据索引: {valley['index']}")
                print()
            
            # 测试最深波谷
            print("🔍 测试最深波谷检测...")
            deepest_valley = strategy_service.find_deepest_valley(daily_data)
            
            if deepest_valley:
                print("✅ 最深波谷:")
                print(f"  日期: {deepest_valley['lowest_date']}")
                print(f"  价格: {deepest_valley['lowest_price']:.4f}")
                print(f"  跌幅: {deepest_valley['drop_rate']*100:.2f}%")
                print(f"  左侧高点: {deepest_valley['left_peak']:.4f} ({deepest_valley['left_peak_date']})")
            else:
                print("❌ 未找到最深波谷")
            
            print()
            
            # 测试高频触及波谷检测
            print("🔍 测试高频触及波谷检测...")
            print("⚙️  参数: 价格容忍度5%, 最小触及次数3次")
            frequent_valleys = strategy_service.find_frequently_touched_valleys(daily_data, price_tolerance=0.05, min_touch_count=3)
            
            if frequent_valleys:
                print(f"✅ 找到 {len(frequent_valleys)} 个高频触及波谷组")
                print()
                
                print("📊 高频触及波谷详细信息:")
                print("=" * 100)
                for i, group in enumerate(frequent_valleys, 1):
                    print(f"组 {i}: 触及 {group['touch_count']} 次, 强度分数: {group['strength_score']:.2f}")
                    print(f"  价格区间: {group['price_range']['min']:.4f} - {group['price_range']['max']:.4f} (平均: {group['price_range']['avg']:.4f})")
                    print(f"  时间跨度: {group['date_range']['earliest']} 到 {group['date_range']['latest']}")
                    print(f"  跌幅区间: {group['drop_range']['min']*100:.1f}% - {group['drop_range']['max']*100:.1f}% (平均: {group['drop_range']['avg']*100:.1f}%)")
                    print("  包含波谷:")
                    for j, valley in enumerate(group['valleys'], 1):
                        print(f"    {j}. {valley['date']} 价格:{valley['price']:.4f} 跌幅:{valley['drop_rate']*100:.1f}%")
                    print("-" * 80)
            else:
                print("❌ 未找到高频触及波谷")
            
            print()
            
            # 测试横盘确认波谷检测
            print("🔍 测试横盘确认波谷检测...")
            print("⚙️  参数: 横盘确认30天, 价格容忍度8%, 最小触及次数3次")
            consolidation_valleys = strategy_service.find_consolidation_valleys(
                daily_data, consolidation_days=30, price_tolerance=0.08, min_touch_count=3
            )
            
            if consolidation_valleys:
                print(f"✅ 找到 {len(consolidation_valleys)} 个横盘确认波谷")
                print()
                
                print("📊 横盘确认波谷详细信息:")
                print("=" * 120)
                for i, item in enumerate(consolidation_valleys, 1):
                    valley = item['valley']
                    consolidation = item['consolidation']
                    
                    print(f"横盘确认波谷 {i}: 确认分数: {item['consolidation_score']}")
                    print(f"  波谷信息:")
                    print(f"    日期: {valley['date']}")
                    print(f"    价格: {valley['price']:.4f}")
                    print(f"    跌幅: {valley['drop_rate']*100:.1f}%")
                    print(f"  横盘信息:")
                    print(f"    持续时间: {consolidation['duration_days']}天")
                    print(f"    触及次数: {consolidation['touch_count']}次")
                    print(f"    价格区间: {consolidation['price_range']['lower']:.4f} - {consolidation['price_range']['upper']:.4f}")
                    print(f"    价格波动: {consolidation['price_range']['volatility']*100:.1f}%")
                    print(f"    横盘质量: {consolidation['consolidation_quality']}")
                    print(f"    触及记录:")
                    for j, touch in enumerate(consolidation['touches'][:5], 1):  # 只显示前5个
                        print(f"      {j}. {touch['date']} H:{touch['high']:.4f} L:{touch['low']:.4f} C:{touch['close']:.4f}")
                    if len(consolidation['touches']) > 5:
                        print(f"      ... 还有 {len(consolidation['touches']) - 5} 个触及记录")
                    print("-" * 100)
            else:
                print("❌ 未找到横盘确认波谷")
        else:
            print("❌ 未检测到任何波谷")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def analyze_specific_consolidation_periods(daily_data):
    """
    分析用户提到的特定横盘时间段
    """
    print("\n" + "="*80)
    print("🔍 分析用户提到的特定横盘时间段")
    print("="*80)
    
    # 时间段1: 2021-7-28到2023年3月10日
    print("\n📅 时间段1: 2021-7-28到2023年3月10日")
    print("-" * 50)
    
    start_date = "20210728"
    end_date = "20230310"
    
    period_data = [d for d in daily_data if start_date <= d['date'] <= end_date]
    if period_data:
        print(f"数据条数: {len(period_data)}")
        print(f"开始日期: {period_data[0]['date']}, 价格: {period_data[0]['close']}")
        print(f"结束日期: {period_data[-1]['date']}, 价格: {period_data[-1]['close']}")
        
        # 计算价格区间
        prices = [float(d['close']) for d in period_data]
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        price_volatility = (price_range / min_price) * 100
        
        print(f"最低价: {min_price:.4f}")
        print(f"最高价: {max_price:.4f}")
        print(f"价格区间: {price_range:.4f}")
        print(f"价格波动率: {price_volatility:.2f}%")
        
        # 检查是否有波谷
        valleys_in_period = []
        for i, record in enumerate(period_data):
            if i < 30 or i >= len(period_data) - 30:  # 跳过边界
                continue
            current_price = float(record['close'])
            
            # 检查前后30天是否是最低点
            left_prices = [float(period_data[j]['close']) for j in range(max(0, i-30), i)]
            right_prices = [float(period_data[j]['close']) for j in range(i+1, min(len(period_data), i+31))]
            
            if left_prices and right_prices:
                if current_price <= min(left_prices) and current_price <= min(right_prices):
                    valleys_in_period.append({
                        'date': record['date'],
                        'price': current_price,
                        'index': i
                    })
        
        print(f"期间内发现的波谷数量: {len(valleys_in_period)}")
        for valley in valleys_in_period[:5]:  # 显示前5个
            print(f"  波谷: {valley['date']}, 价格: {valley['price']:.4f}")
    
    # 时间段2: 2023-4-24到2023-10-13日
    print("\n📅 时间段2: 2023-4-24到2023-10-13日")
    print("-" * 50)
    
    start_date = "20230424"
    end_date = "20231013"
    
    period_data = [d for d in daily_data if start_date <= d['date'] <= end_date]
    if period_data:
        print(f"数据条数: {len(period_data)}")
        print(f"开始日期: {period_data[0]['date']}, 价格: {period_data[0]['close']}")
        print(f"结束日期: {period_data[-1]['date']}, 价格: {period_data[-1]['close']}")
        
        # 计算价格区间
        prices = [float(d['close']) for d in period_data]
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        price_volatility = (price_range / min_price) * 100
        
        print(f"最低价: {min_price:.4f}")
        print(f"最高价: {max_price:.4f}")
        print(f"价格区间: {price_range:.4f}")
        print(f"价格波动率: {price_volatility:.2f}%")
        
        # 检查是否有波谷
        valleys_in_period = []
        for i, record in enumerate(period_data):
            if i < 30 or i >= len(period_data) - 30:  # 跳过边界
                continue
            current_price = float(record['close'])
            
            # 检查前后30天是否是最低点
            left_prices = [float(period_data[j]['close']) for j in range(max(0, i-30), i)]
            right_prices = [float(period_data[j]['close']) for j in range(i+1, min(len(period_data), i+31))]
            
            if left_prices and right_prices:
                if current_price <= min(left_prices) and current_price <= min(right_prices):
                    valleys_in_period.append({
                        'date': record['date'],
                        'price': current_price,
                        'index': i
                    })
        
        print(f"期间内发现的波谷数量: {len(valleys_in_period)}")
        for valley in valleys_in_period[:5]:  # 显示前5个
            print(f"  波谷: {valley['date']}, 价格: {valley['price']:.4f}")
    
    # 时间段3: 2019-5-6日到2019-6-28日
    print("\n📅 时间段3: 2019-5-6日到2019-6-28日")
    print("-" * 50)
    
    start_date = "20190506"
    end_date = "20190628"
    
    period_data = [d for d in daily_data if start_date <= d['date'] <= end_date]
    if period_data:
        print(f"数据条数: {len(period_data)}")
        print(f"开始日期: {period_data[0]['date']}, 价格: {period_data[0]['close']}")
        print(f"结束日期: {period_data[-1]['date']}, 价格: {period_data[-1]['close']}")
        
        # 计算价格区间
        prices = [float(d['close']) for d in period_data]
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        price_volatility = (price_range / min_price) * 100
        
        print(f"最低价: {min_price:.4f}")
        print(f"最高价: {max_price:.4f}")
        print(f"价格区间: {price_range:.4f}")
        print(f"价格波动率: {price_volatility:.2f}%")
        
        # 检查是否有波谷
        valleys_in_period = []
        for i, record in enumerate(period_data):
            if i < 30 or i >= len(period_data) - 30:  # 跳过边界
                continue
            current_price = float(record['close'])
            
            # 检查前后30天是否是最低点
            left_prices = [float(period_data[j]['close']) for j in range(max(0, i-30), i)]
            right_prices = [float(period_data[j]['close']) for j in range(i+1, min(len(period_data), i+31))]
            
            if left_prices and right_prices:
                if current_price <= min(left_prices) and current_price <= min(right_prices):
                    valleys_in_period.append({
                        'date': record['date'],
                        'price': current_price,
                        'index': i
                    })
        
        print(f"期间内发现的波谷数量: {len(valleys_in_period)}")
        for valley in valleys_in_period[:5]:  # 显示前5个
            print(f"  波谷: {valley['date']}, 价格: {valley['price']:.4f}")


if __name__ == "__main__":
    test_valley_detection()
    
    # 分析特定横盘时间段
    try:
        # 重新获取数据用于分析
        db_manager = DatabaseManager()
        db_manager.connect()
        
        stock_kline_table = db_manager.get_table_instance("stock_kline")
        adj_factor_table = db_manager.get_table_instance("adj_factor")
        
        # 获取000002.SZ的日线数据
        daily_data = stock_kline_table.load(
            condition="id = %s AND term = %s",
            params=("000002.SZ", "daily"),
            order_by="date ASC"
        )
        
        if daily_data:
            print(f"获取到 {len(daily_data)} 条日线数据")
            if daily_data:
                print(f"第一条数据: {daily_data[0]}")
                print(f"数据类型: {type(daily_data[0])}")
            
            # 获取复权因子并应用前复权
            print("🔧 应用前复权处理...")
            qfq_factors = adj_factor_table.get_stock_factors("000002.SZ")
            daily_data = DataSourceService.to_qfq(daily_data, qfq_factors)
            print("✅ 前复权处理完成")
            
            # 数据预处理
            daily_data = preprocess_daily_data(daily_data)
            
            # 分析特定时间段
            analyze_specific_consolidation_periods(daily_data)
            
            # 测试新的整合波谷检测方法
            print("\n" + "="*80)
            print("🧪 测试新的整合波谷检测方法")
            print("="*80)
            
            try:
                # 创建策略服务实例
                strategy_service = HistoricLowService()
                
                # 测试整合方法
                print("\n🔍 测试 find_merged_historic_lows...")
                merged_lows = strategy_service.find_merged_historic_lows(daily_data)
                
                if merged_lows:
                    print(f"\n✅ 成功找到 {len(merged_lows)} 个整合后的历史低点")
                    
                                    # 显示前5个多重确认的低点详情
                print("\n🏆 前5个多重确认的历史低点详情:")
                for i, low_point in enumerate(merged_lows[:5]):
                    print(f"\n{i+1}. 日期: {low_point['date']}")
                    print(f"   价格: {low_point['price']:.2f}")
                    print(f"   跌幅: {low_point['drop_rate']*100:.1f}%")
                    print(f"   来源数量: {len(low_point['conclusion_from'])}")
                    print(f"   来源: {low_point['conclusion_from']}")
                else:
                    print("❌ 未找到任何整合后的历史低点")
                    
            except Exception as e:
                print(f"❌ 测试整合方法失败: {e}")
                import traceback
                traceback.print_exc()
        
        db_manager.disconnect()
        
    except Exception as e:
        print(f"❌ 分析特定时间段失败: {e}")
        import traceback
        traceback.print_exc()
