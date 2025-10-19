#!/usr/bin/env python3
"""
比较不同收敛阈值的表现：0.04（严格）、0.06（中等）、0.08（宽松）
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

def analyze_stock_convergence(stock_id, threshold):
    """分析单只股票的收敛情况"""
    from utils.db.db_manager import DatabaseManager
    db = DatabaseManager(use_connection_pool=True)
    db.initialize()
    data_loader = DataLoader(db)
    
    # 获取周线数据
    weekly_data = data_loader.load_klines(stock_id, term='weekly', adjust='qfq')
    
    if not weekly_data or len(weekly_data) < 100:
        return None
    
    # 提取价格数据和日期
    closes = [k['close'] for k in weekly_data if k.get('close')]
    dates = [k['date'] for k in weekly_data if k.get('date')]
    
    # 计算移动平均线
    def rolling_mean(data, window):
        result = np.full(len(data), np.nan)
        for i in range(window - 1, len(data)):
            result[i] = np.mean(data[i - window + 1:i + 1])
        return result
    
    ma5 = rolling_mean(closes, 5)
    ma10 = rolling_mean(closes, 10)
    ma20 = rolling_mean(closes, 20)
    ma60 = rolling_mean(closes, 60)
    
    # 找到所有满足收敛条件的点
    convergence_points = []
    
    for i in range(60, len(closes)):
        if np.isnan(ma5[i]) or np.isnan(ma10[i]) or np.isnan(ma20[i]) or np.isnan(ma60[i]):
            continue
            
        ma_values = [ma5[i], ma10[i], ma20[i], ma60[i]]
        ma_max = max(ma_values)
        ma_min = min(ma_values)
        ma_convergence = (ma_max - ma_min) / closes[i]
        
        if ma_convergence < threshold and i < len(dates):
            convergence_points.append({
                'idx': i,
                'date': dates[i],
                'convergence': ma_convergence,
                'price': closes[i]
            })
    
    # 将连续的时间点合并为时间段
    convergence_periods = []
    if convergence_points:
        current_period = [convergence_points[0]]
        
        for i in range(1, len(convergence_points)):
            if convergence_points[i]['idx'] == convergence_points[i-1]['idx'] + 1:
                current_period.append(convergence_points[i])
            else:
                if len(current_period) >= 1:
                    start_point = current_period[0]
                    end_point = current_period[-1]
                    
                    convergence_periods.append({
                        'start_date': start_point['date'],
                        'end_date': end_point['date'],
                        'duration_weeks': len(current_period),
                        'avg_convergence': sum(p['convergence'] for p in current_period) / len(current_period),
                        'start_price': start_point['price'],
                        'end_price': end_point['price'],
                        'price_change': (end_point['price'] - start_point['price']) / start_point['price']
                    })
                
                current_period = [convergence_points[i]]
        
        # 处理最后一个时间段
        if len(current_period) >= 1:
            start_point = current_period[0]
            end_point = current_period[-1]
            
            convergence_periods.append({
                'start_date': start_point['date'],
                'end_date': end_point['date'],
                'duration_weeks': len(current_period),
                'avg_convergence': sum(p['convergence'] for p in current_period) / len(current_period),
                'start_price': start_point['price'],
                'end_price': end_point['price'],
                'price_change': (end_point['price'] - start_point['price']) / start_point['price']
            })
    
    # 统计信息
    if convergence_periods:
        total_weeks = sum(p['duration_weeks'] for p in convergence_periods)
        avg_duration = total_weeks / len(convergence_periods)
        avg_convergence = sum(p['avg_convergence'] for p in convergence_periods) / len(convergence_periods)
        
        positive_changes = [p for p in convergence_periods if p['price_change'] > 0]
        negative_changes = [p for p in convergence_periods if p['price_change'] < 0]
        
        win_rate = len(positive_changes) / len(convergence_periods) * 100
        
        avg_positive_change = sum(p['price_change'] for p in positive_changes) / len(positive_changes) if positive_changes else 0
        avg_negative_change = sum(p['price_change'] for p in negative_changes) / len(negative_changes) if negative_changes else 0
        
        return {
            'stock_id': stock_id,
            'threshold': threshold,
            'periods_count': len(convergence_periods),
            'total_weeks': total_weeks,
            'avg_duration': avg_duration,
            'avg_convergence': avg_convergence,
            'win_rate': win_rate,
            'avg_positive_change': avg_positive_change,
            'avg_negative_change': avg_negative_change,
            'expected_value': (win_rate/100 * avg_positive_change) + ((100-win_rate)/100 * avg_negative_change)
        }
    else:
        return {
            'stock_id': stock_id,
            'threshold': threshold,
            'periods_count': 0,
            'total_weeks': 0,
            'avg_duration': 0,
            'avg_convergence': 0,
            'win_rate': 0,
            'avg_positive_change': 0,
            'avg_negative_change': 0,
            'expected_value': 0
        }

def compare_thresholds():
    """比较不同收敛阈值的表现"""
    
    print("="*80)
    print("比较不同收敛阈值的表现：0.04（严格）、0.06（中等）、0.08（宽松）")
    print("="*80)
    
    # 测试股票列表
    test_stocks = [
        "000001.SZ",  # 平安银行
        "000002.SZ",  # 万科A
        "000858.SZ",  # 五粮液
        "600036.SH",  # 招商银行
        "600519.SH",  # 贵州茅台
        "000725.SZ",  # 京东方A
        "002415.SZ",  # 海康威视
        "600276.SH",  # 恒瑞医药
    ]
    
    thresholds = [0.04, 0.06, 0.08]
    all_results = []
    
    for threshold in thresholds:
        print(f"\n🔍 测试阈值: {threshold}")
        print("-" * 60)
        
        threshold_results = []
        
        for stock_id in test_stocks:
            result = analyze_stock_convergence(stock_id, threshold)
            if result:
                threshold_results.append(result)
                print(f"   {stock_id}: {result['periods_count']}个时间段, "
                      f"胜率{result['win_rate']:.1f}%, "
                      f"期望值{result['expected_value']*100:.2f}%")
        
        all_results.append({
            'threshold': threshold,
            'results': threshold_results
        })
    
    # 汇总分析
    print(f"\n" + "="*80)
    print("📊 汇总分析结果")
    print("="*80)
    
    for threshold_data in all_results:
        threshold = threshold_data['threshold']
        results = threshold_data['results']
        
        if results:
            valid_results = [r for r in results if r['periods_count'] > 0]
            
            if valid_results:
                avg_periods = sum(r['periods_count'] for r in valid_results) / len(valid_results)
                avg_win_rate = sum(r['win_rate'] for r in valid_results) / len(valid_results)
                avg_expected_value = sum(r['expected_value'] for r in valid_results) / len(valid_results)
                avg_positive_change = sum(r['avg_positive_change'] for r in valid_results) / len(valid_results)
                avg_negative_change = sum(r['avg_negative_change'] for r in valid_results) / len(valid_results)
                
                print(f"\n📏 阈值 {threshold}:")
                print(f"   📊 平均收敛时间段数: {avg_periods:.1f}")
                print(f"   🎯 平均胜率: {avg_win_rate:.1f}%")
                print(f"   💰 平均期望值: {avg_expected_value*100:.2f}%")
                print(f"   📈 平均上涨幅度: {avg_positive_change*100:.2f}%")
                print(f"   📉 平均下跌幅度: {avg_negative_change*100:.2f}%")
                print(f"   ✅ 有效股票数: {len(valid_results)}/{len(results)}")
            else:
                print(f"\n📏 阈值 {threshold}: 无有效收敛时间段")
        else:
            print(f"\n📏 阈值 {threshold}: 无数据")
    
    # 找出最佳阈值
    print(f"\n🏆 最佳阈值推荐:")
    print("-" * 60)
    
    best_threshold = None
    best_expected_value = -999
    
    for threshold_data in all_results:
        threshold = threshold_data['threshold']
        results = threshold_data['results']
        
        if results:
            valid_results = [r for r in results if r['periods_count'] > 0]
            if valid_results:
                avg_expected_value = sum(r['expected_value'] for r in valid_results) / len(valid_results)
                avg_win_rate = sum(r['win_rate'] for r in valid_results) / len(valid_results)
                avg_periods = sum(r['periods_count'] for r in valid_results) / len(valid_results)
                
                print(f"   阈值 {threshold}: 期望值{avg_expected_value*100:.2f}%, "
                      f"胜率{avg_win_rate:.1f}%, "
                      f"平均{avg_periods:.1f}个时间段")
                
                if avg_expected_value > best_expected_value:
                    best_expected_value = avg_expected_value
                    best_threshold = threshold
    
    if best_threshold is not None:
        print(f"\n🎯 推荐使用阈值: {best_threshold} (期望值最高: {best_expected_value*100:.2f}%)")
    else:
        print(f"\n❌ 无法确定最佳阈值")

if __name__ == "__main__":
    compare_thresholds()
