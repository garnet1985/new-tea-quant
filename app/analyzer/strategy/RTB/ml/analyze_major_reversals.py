#!/usr/bin/env python3
"""
分析重大反转点结果

分析平安银行识别出的重大反转点，提供统计分析和可视化
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import json


def analyze_major_reversals():
    """分析重大反转点"""
    logger.info("📊 开始分析平安银行重大反转点")
    
    # 读取数据
    csv_path = Path(__file__).parent / "major_reversals_000001_SZ.csv"
    json_path = Path(__file__).parent / "major_reversals_000001_SZ.json"
    
    if not csv_path.exists():
        logger.error(f"❌ 文件不存在: {csv_path}")
        return
    
    # 读取CSV数据
    df = pd.read_csv(csv_path)
    logger.info(f"✅ 成功加载 {len(df)} 个重大反转点")
    
    # 基本统计
    show_basic_statistics(df)
    
    # 按时间分组分析
    analyze_by_time_periods(df)
    
    # 特征分析
    analyze_features(df)
    
    # 反转效果分析
    analyze_reversal_effectiveness(df)
    
    # 显示最佳反转点
    show_best_reversals(df)


def show_basic_statistics(df):
    """显示基本统计信息"""
    logger.info("\n" + "="*60)
    logger.info("📈 重大反转点基本统计")
    logger.info("="*60)
    
    logger.info(f"总数量: {len(df)} 个")
    logger.info(f"时间范围: {df['reversal_date'].min()} 到 {df['reversal_date'].max()}")
    
    # 收益统计
    logger.info(f"\n💰 收益统计:")
    logger.info(f"  平均收益: {df['reversal_gain'].mean()*100:.1f}%")
    logger.info(f"  最大收益: {df['reversal_gain'].max()*100:.1f}%")
    logger.info(f"  最小收益: {df['reversal_gain'].min()*100:.1f}%")
    logger.info(f"  收益标准差: {df['reversal_gain'].std()*100:.1f}%")
    
    # 持续时间统计
    logger.info(f"\n⏱️ 持续时间统计:")
    logger.info(f"  平均持续时间: {df['reversal_duration'].mean():.1f} 周")
    logger.info(f"  最长持续时间: {df['reversal_duration'].max()} 周")
    logger.info(f"  最短持续时间: {df['reversal_duration'].min()} 周")


def analyze_by_time_periods(df):
    """按时间周期分析"""
    logger.info("\n" + "="*60)
    logger.info("📅 按时间周期分析")
    logger.info("="*60)
    
    # 转换日期
    df['date'] = pd.to_datetime(df['reversal_date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    
    # 按年份统计
    yearly_stats = df.groupby('year').agg({
        'reversal_gain': ['count', 'mean', 'max'],
        'reversal_duration': 'mean'
    }).round(3)
    
    logger.info("\n📊 按年份统计:")
    for year in yearly_stats.index:
        count = yearly_stats.loc[year, ('reversal_gain', 'count')]
        avg_gain = yearly_stats.loc[year, ('reversal_gain', 'mean')]
        max_gain = yearly_stats.loc[year, ('reversal_gain', 'max')]
        avg_duration = yearly_stats.loc[year, ('reversal_duration', 'mean')]
        logger.info(f"  {year}年: {count}个反转点, 平均收益{avg_gain*100:.1f}%, 最大收益{max_gain*100:.1f}%, 平均持续{avg_duration:.1f}周")
    
    # 识别主要反转时期
    major_periods = identify_major_reversal_periods(df)
    logger.info(f"\n🎯 主要反转时期:")
    for period in major_periods:
        logger.info(f"  {period['period']}: {period['count']}个反转点, 平均收益{period['avg_gain']*100:.1f}%")


def identify_major_reversal_periods(df):
    """识别主要反转时期"""
    periods = []
    
    # 2022年熊市底部
    bear_market_2022 = df[df['date'].dt.year == 2022]
    if len(bear_market_2022) > 0:
        periods.append({
            'period': '2022年熊市底部',
            'count': len(bear_market_2022),
            'avg_gain': bear_market_2022['reversal_gain'].mean()
        })
    
    # 2023-2024年持续下跌
    decline_2023_2024 = df[(df['date'].dt.year >= 2023)]
    if len(decline_2023_2024) > 0:
        periods.append({
            'period': '2023-2024年持续下跌',
            'count': len(decline_2023_2024),
            'avg_gain': decline_2023_2024['reversal_gain'].mean()
        })
    
    return periods


def analyze_features(df):
    """分析反转点特征"""
    logger.info("\n" + "="*60)
    logger.info("🔍 反转点特征分析")
    logger.info("="*60)
    
    # 价格位置分析
    logger.info(f"\n📍 价格位置特征:")
    logger.info(f"  平均2年价格位置: {df['price_position_2y'].mean():.3f}")
    logger.info(f"  价格位置<0.1的比例: {(df['price_position_2y'] < 0.1).mean()*100:.1f}%")
    logger.info(f"  价格位置<0的比例: {(df['price_position_2y'] < 0).mean()*100:.1f}%")
    
    # 前期跌幅分析
    logger.info(f"\n📉 前期跌幅特征:")
    logger.info(f"  平均前期跌幅: {df['decline_from_peak'].mean()*100:.1f}%")
    logger.info(f"  跌幅>50%的比例: {(df['decline_from_peak'] > 0.5).mean()*100:.1f}%")
    logger.info(f"  跌幅>40%的比例: {(df['decline_from_peak'] > 0.4).mean()*100:.1f}%")
    
    # 均线收敛分析
    logger.info(f"\n📊 均线收敛特征:")
    logger.info(f"  平均均线收敛度: {df['ma_convergence'].mean():.3f}")
    logger.info(f"  收敛度<0.1的比例: {(df['ma_convergence'] < 0.1).mean()*100:.1f}%")
    
    # RSI分析
    logger.info(f"\n📈 RSI特征:")
    logger.info(f"  平均RSI: {df['rsi'].mean():.1f}")
    logger.info(f"  RSI<30的比例: {(df['rsi'] < 30).mean()*100:.1f}%")
    logger.info(f"  RSI<20的比例: {(df['rsi'] < 20).mean()*100:.1f}%")


def analyze_reversal_effectiveness(df):
    """分析反转效果"""
    logger.info("\n" + "="*60)
    logger.info("🎯 反转效果分析")
    logger.info("="*60)
    
    # 高收益反转点
    high_gain = df[df['reversal_gain'] > 0.3]
    logger.info(f"\n🚀 高收益反转点 (收益>30%):")
    logger.info(f"  数量: {len(high_gain)} 个 ({len(high_gain)/len(df)*100:.1f}%)")
    if len(high_gain) > 0:
        logger.info(f"  平均收益: {high_gain['reversal_gain'].mean()*100:.1f}%")
        logger.info(f"  平均持续时间: {high_gain['reversal_duration'].mean():.1f} 周")
    
    # 快速反转点
    quick_reversal = df[df['reversal_duration'] <= 10]
    logger.info(f"\n⚡ 快速反转点 (≤10周):")
    logger.info(f"  数量: {len(quick_reversal)} 个 ({len(quick_reversal)/len(df)*100:.1f}%)")
    if len(quick_reversal) > 0:
        logger.info(f"  平均收益: {quick_reversal['reversal_gain'].mean()*100:.1f}%")
    
    # 长期反转点
    long_reversal = df[df['reversal_duration'] >= 30]
    logger.info(f"\n🐌 长期反转点 (≥30周):")
    logger.info(f"  数量: {len(long_reversal)} 个 ({len(long_reversal)/len(df)*100:.1f}%)")
    if len(long_reversal) > 0:
        logger.info(f"  平均收益: {long_reversal['reversal_gain'].mean()*100:.1f}%")


def show_best_reversals(df):
    """显示最佳反转点"""
    logger.info("\n" + "="*60)
    logger.info("🏆 最佳反转点 TOP 5")
    logger.info("="*60)
    
    # 按收益排序
    top_reversals = df.nlargest(5, 'reversal_gain')
    
    for i, (_, reversal) in enumerate(top_reversals.iterrows(), 1):
        logger.info(f"\n🥇 第{i}名:")
        logger.info(f"  日期: {reversal['reversal_date']}")
        logger.info(f"  价格: {reversal['reversal_price']:.2f}元")
        logger.info(f"  收益: {reversal['reversal_gain']*100:.1f}%")
        logger.info(f"  持续时间: {reversal['reversal_duration']}周")
        logger.info(f"  价格位置: {reversal['price_position_2y']:.3f}")
        logger.info(f"  前期跌幅: {reversal['decline_from_peak']*100:.1f}%")
        logger.info(f"  RSI: {reversal['rsi']:.1f}")
    
    # 显示最典型的反转点特征
    logger.info(f"\n📊 典型反转点特征总结:")
    logger.info(f"  价格位置: {df['price_position_2y'].median():.3f} (中位数)")
    logger.info(f"  前期跌幅: {df['decline_from_peak'].median()*100:.1f}% (中位数)")
    logger.info(f"  均线收敛: {df['ma_convergence'].median():.3f} (中位数)")
    logger.info(f"  RSI: {df['rsi'].median():.1f} (中位数)")


if __name__ == "__main__":
    analyze_major_reversals()
