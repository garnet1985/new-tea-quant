#!/usr/bin/env python3
"""
分析收敛期内的买入时机，找出最佳买入低点
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

def load_convergence_data():
    """加载之前分析的收敛时间段数据"""
    data_file = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/convergence_periods_analysis.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return None
    
    df = pd.read_csv(data_file)
    print(f"📊 加载数据: {len(df)} 个收敛时间段")
    return df

def analyze_convergence_period_details(stock_id, start_date, end_date, start_idx, end_idx):
    """分析单个收敛期内的详细价格行为"""
    from utils.db.db_manager import DatabaseManager
    db = DatabaseManager(use_connection_pool=True)
    db.initialize()
    data_loader = DataLoader(db)
    
    # 获取周线数据
    weekly_data = data_loader.load_klines(stock_id, term='weekly', adjust='qfq')
    
    if not weekly_data or len(weekly_data) < end_idx + 1:
        return None
    
    # 提取收敛期内的数据
    period_data = weekly_data[start_idx:end_idx + 1]
    
    if len(period_data) < 2:
        return None
    
    # 提取价格数据
    closes = [k['close'] for k in period_data]
    highs = [k['highest'] for k in period_data]
    lows = [k['lowest'] for k in period_data]
    dates = [k['date'] for k in period_data]
    
    # 计算收敛期内的价格统计
    period_start_price = closes[0]
    period_end_price = closes[-1]
    period_min_price = min(lows)
    period_max_price = max(highs)
    
    # 计算价格位置指标
    min_price_idx = lows.index(period_min_price)
    max_price_idx = highs.index(period_max_price)
    
    # 计算相对位置
    min_price_ratio = (period_min_price - period_start_price) / period_start_price
    max_price_ratio = (period_max_price - period_start_price) / period_start_price
    end_price_ratio = (period_end_price - period_start_price) / period_start_price
    
    # 计算价格波动
    price_volatility = (period_max_price - period_min_price) / period_start_price
    
    # 分析价格趋势
    price_trend = (period_end_price - period_start_price) / period_start_price
    
    # 计算低点出现的时间位置
    min_price_timing = min_price_idx / (len(period_data) - 1) if len(period_data) > 1 else 0
    
    return {
        'stock_id': stock_id,
        'start_date': start_date,
        'end_date': end_date,
        'duration_weeks': len(period_data),
        'period_start_price': period_start_price,
        'period_end_price': period_end_price,
        'period_min_price': period_min_price,
        'period_max_price': period_max_price,
        'min_price_idx': min_price_idx,
        'max_price_idx': max_price_idx,
        'min_price_ratio': min_price_ratio,
        'max_price_ratio': max_price_ratio,
        'end_price_ratio': end_price_ratio,
        'price_volatility': price_volatility,
        'price_trend': price_trend,
        'min_price_timing': min_price_timing,
        'closes': closes,
        'highs': highs,
        'lows': lows,
        'dates': dates
    }

def analyze_entry_timing_patterns(df):
    """分析买入时机模式"""
    print("\n" + "="*80)
    print("🎯 收敛期内买入时机分析")
    print("="*80)
    
    # 过滤掉包含NaN的数据
    df_clean = df.dropna()
    
    # 只分析高质量收敛期（基于之前的分析结果）
    high_quality_periods = df_clean[
        (df_clean['ma20_slope_end'] > 0.1) & 
        (df_clean['ma20_slope_start'] > 0.05) &
        (df_clean['avg_convergence'] < 0.07)
    ]
    
    print(f"📊 高质量收敛期数量: {len(high_quality_periods)}")
    
    if len(high_quality_periods) == 0:
        print("❌ 没有找到高质量收敛期")
        return
    
    # 分析每个高质量收敛期的详细情况
    detailed_analysis = []
    
    for _, period in high_quality_periods.iterrows():
        details = analyze_convergence_period_details(
            period['stock_id'],
            period['start_date'],
            period['end_date'],
            period['start_idx'],
            period['end_idx']
        )
        
        if details:
            # 添加后续表现信息
            details['return_20w'] = period['return_20w']
            details['is_profitable_20w'] = period['is_profitable_20w']
            detailed_analysis.append(details)
    
    if not detailed_analysis:
        print("❌ 无法获取详细分析数据")
        return
    
    # 转换为DataFrame
    detail_df = pd.DataFrame(detailed_analysis)
    
    print(f"📈 详细分析样本数: {len(detail_df)}")
    print(f"✅ 20周后盈利: {detail_df['is_profitable_20w'].sum()}")
    print(f"🎯 胜率: {detail_df['is_profitable_20w'].mean()*100:.1f}%")
    
    # 分析价格行为模式
    print(f"\n📊 收敛期内价格行为分析:")
    print("-" * 60)
    
    print(f"价格波动统计:")
    print(f"   平均价格波动: {detail_df['price_volatility'].mean()*100:.2f}%")
    print(f"   平均价格趋势: {detail_df['price_trend'].mean()*100:.2f}%")
    print(f"   平均最低价相对位置: {detail_df['min_price_ratio'].mean()*100:.2f}%")
    print(f"   平均最高价相对位置: {detail_df['max_price_ratio'].mean()*100:.2f}%")
    
    # 分析低点出现时机
    print(f"\n⏰ 低点出现时机分析:")
    print("-" * 60)
    
    # 按低点出现时机分组
    timing_groups = [
        (0.0, 0.2, "前20%时间"),
        (0.2, 0.4, "20%-40%时间"),
        (0.4, 0.6, "40%-60%时间"),
        (0.6, 0.8, "60%-80%时间"),
        (0.8, 1.0, "后20%时间")
    ]
    
    for start_timing, end_timing, label in timing_groups:
        subset = detail_df[(detail_df['min_price_timing'] >= start_timing) & (detail_df['min_price_timing'] < end_timing)]
        if len(subset) > 0:
            win_rate = subset['is_profitable_20w'].mean() * 100
            avg_return = subset['return_20w'].mean() * 100
            avg_volatility = subset['price_volatility'].mean() * 100
            print(f"   {label}: {len(subset)}个样本, 胜率{win_rate:.1f}%, 平均收益{avg_return:.1f}%, 平均波动{avg_volatility:.1f}%")
    
    # 分析价格位置策略
    print(f"\n💰 价格位置策略分析:")
    print("-" * 60)
    
    # 分析不同买入策略的效果
    strategies = [
        {
            'name': '在最低点买入',
            'condition': detail_df['min_price_ratio'] < -0.05,  # 最低价比开始价低5%以上
            'return_multiplier': 1.0  # 假设在最低点买入
        },
        {
            'name': '在开始价买入',
            'condition': detail_df['price_trend'] > -0.05,  # 收敛期内跌幅不超过5%
            'return_multiplier': 1.0  # 在开始价买入
        },
        {
            'name': '在结束价买入',
            'condition': detail_df['end_price_ratio'] > -0.02,  # 结束价比开始价高
            'return_multiplier': 1.0  # 在结束价买入
        }
    ]
    
    for strategy in strategies:
        subset = detail_df[strategy['condition']]
        if len(subset) > 0:
            win_rate = subset['is_profitable_20w'].mean() * 100
            avg_return = subset['return_20w'].mean() * 100
            print(f"   {strategy['name']}: {len(subset)}个样本, 胜率{win_rate:.1f}%, 平均收益{avg_return:.1f}%")
    
    # 分析最佳买入时机
    print(f"\n🎯 最佳买入时机分析:")
    print("-" * 60)
    
    # 分析低点出现时机与后续表现的关系
    early_low = detail_df[detail_df['min_price_timing'] < 0.3]  # 前30%时间出现低点
    mid_low = detail_df[(detail_df['min_price_timing'] >= 0.3) & (detail_df['min_price_timing'] < 0.7)]  # 中间40%时间
    late_low = detail_df[detail_df['min_price_timing'] >= 0.7]  # 后30%时间
    
    print(f"低点出现时机与后续表现:")
    for label, subset in [("前30%时间", early_low), ("中间40%时间", mid_low), ("后30%时间", late_low)]:
        if len(subset) > 0:
            win_rate = subset['is_profitable_20w'].mean() * 100
            avg_return = subset['return_20w'].mean() * 100
            avg_timing = subset['min_price_timing'].mean()
            print(f"   {label}: {len(subset)}个样本, 胜率{win_rate:.1f}%, 平均收益{avg_return:.1f}%, 平均低点时机{avg_timing:.2f}")
    
    # 分析价格波动与买入时机的关系
    print(f"\n📊 价格波动与买入时机关系:")
    print("-" * 60)
    
    # 按价格波动分组
    volatility_groups = [
        (0.0, 0.05, "低波动(<5%)"),
        (0.05, 0.10, "中波动(5%-10%)"),
        (0.10, 0.20, "高波动(10%-20%)"),
        (0.20, 1.0, "极高波动(>20%)")
    ]
    
    for start_vol, end_vol, label in volatility_groups:
        subset = detail_df[(detail_df['price_volatility'] >= start_vol) & (detail_df['price_volatility'] < end_vol)]
        if len(subset) > 0:
            win_rate = subset['is_profitable_20w'].mean() * 100
            avg_return = subset['return_20w'].mean() * 100
            avg_timing = subset['min_price_timing'].mean()
            print(f"   {label}: {len(subset)}个样本, 胜率{win_rate:.1f}%, 平均收益{avg_return:.1f}%, 平均低点时机{avg_timing:.2f}")
    
    return detail_df

def suggest_entry_strategies(detail_df):
    """基于分析结果提出买入策略建议"""
    print(f"\n" + "="*80)
    print("💡 买入策略建议")
    print("="*80)
    
    if detail_df is None or len(detail_df) == 0:
        print("❌ 没有足够的数据提供建议")
        return
    
    # 分析最佳策略
    print("🎯 基于分析结果的买入策略建议:")
    print("-" * 60)
    
    # 策略1：等待低点策略
    low_point_strategy = detail_df[detail_df['min_price_ratio'] < -0.03]  # 等待3%以上的回调
    if len(low_point_strategy) > 0:
        win_rate = low_point_strategy['is_profitable_20w'].mean() * 100
        avg_return = low_point_strategy['return_20w'].mean() * 100
        print(f"1. 等待低点策略 (等待3%以上回调):")
        print(f"   样本数: {len(low_point_strategy)}, 胜率: {win_rate:.1f}%, 平均收益: {avg_return:.1f}%")
        print(f"   建议: 在收敛期开始后，等待价格回调3%以上再买入")
    
    # 策略2：分批买入策略
    print(f"\n2. 分批买入策略:")
    print(f"   建议: 在收敛期开始时买入30%，在低点附近买入40%，在收敛期结束时买入30%")
    print(f"   优势: 降低时机风险，平均成本")
    
    # 策略3：技术指标确认策略
    print(f"\n3. 技术指标确认策略:")
    print(f"   建议: 结合MA20斜率确认，当MA20斜率开始转正时买入")
    print(f"   优势: 提高买入时机的准确性")
    
    # 策略4：波动率策略
    low_volatility = detail_df[detail_df['price_volatility'] < 0.08]  # 低波动收敛期
    if len(low_volatility) > 0:
        win_rate = low_volatility['is_profitable_20w'].mean() * 100
        avg_return = low_volatility['return_20w'].mean() * 100
        print(f"\n4. 低波动策略 (波动率<8%):")
        print(f"   样本数: {len(low_volatility)}, 胜率: {win_rate:.1f}%, 平均收益: {avg_return:.1f}%")
        print(f"   建议: 选择波动率较低的收敛期，在收敛期结束时买入")
    
    # 综合建议
    print(f"\n🎯 综合买入策略建议:")
    print("-" * 60)
    print(f"1. 主要策略: 等待低点策略")
    print(f"   - 在高质量收敛期开始时观察")
    print(f"   - 等待价格回调3-5%")
    print(f"   - 结合MA20斜率确认买入时机")
    print(f"   - 分批买入降低风险")
    
    print(f"\n2. 辅助策略: 技术确认")
    print(f"   - 确认MA20斜率开始转正")
    print(f"   - 确认价格不再创新低")
    print(f"   - 确认成交量配合")
    
    print(f"\n3. 风险控制:")
    print(f"   - 避免在收敛期前30%时间买入（低点可能未出现）")
    print(f"   - 避免在极高波动期买入（>20%）")
    print(f"   - 设置止损位在收敛期最低点下方2-3%")

def main():
    """主函数"""
    print("="*80)
    print("🎯 收敛期内买入时机分析")
    print("="*80)
    
    # 加载数据
    df = load_convergence_data()
    if df is None:
        return
    
    # 分析买入时机模式
    detail_df = analyze_entry_timing_patterns(df)
    
    # 提出买入策略建议
    suggest_entry_strategies(detail_df)
    
    # 保存详细分析数据
    if detail_df is not None and len(detail_df) > 0:
        output_file = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/entry_timing_analysis.csv"
        detail_df.to_csv(output_file, index=False)
        print(f"\n💾 详细分析数据已保存到: {output_file}")

if __name__ == "__main__":
    main()
