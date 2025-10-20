#!/usr/bin/env python3
"""
显示平安银行反转点位置脚本

帮助人肉验证反转点识别的准确性
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import json
from typing import List, Dict, Any, Optional


def show_pingan_reversals():
    """显示平安银行的反转点位置"""
    from start import App
    from app.data_loader.loaders import KlineLoader
    
    logger.info("🔍 显示平安银行反转点位置")
    
    # 初始化应用
    app = App()
    
    # 创建KlineLoader
    kline_loader = KlineLoader(app.db)
    
    # 获取平安银行的周线数据
    stock_id = "000001.SZ"  # 平安银行
    start_date = "20180101"
    end_date = "20241231"
    
    logger.info(f"📊 获取平安银行({stock_id})周线数据: {start_date} - {end_date}")
    
    try:
        # 加载周线数据
        weekly_klines = kline_loader.load_weekly_qfq(stock_id, start_date, end_date)
        logger.info(f"✅ 成功加载 {len(weekly_klines)} 条周线数据")
        
        if len(weekly_klines) < 50:
            logger.error("❌ 数据不足，无法进行分析")
            return
        
        # 读取反转样本数据
        reversal_file = Path(__file__).parent / "pingan_reversal_samples_000001_SZ.json"
        if not reversal_file.exists():
            logger.error(f"❌ 反转样本文件不存在: {reversal_file}")
            return
            
        with open(reversal_file, 'r', encoding='utf-8') as f:
            reversal_samples = json.load(f)
        
        logger.info(f"📈 找到 {len(reversal_samples)} 个反转点")
        
        # 按时间排序
        reversal_samples.sort(key=lambda x: x['reversal_date'])
        
        # 显示反转点详情
        show_reversal_details(weekly_klines, reversal_samples)
        
        # 生成CSV文件便于分析
        save_reversal_csv(reversal_samples)
        
    except Exception as e:
        logger.error(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


def show_reversal_details(klines: List[Dict], reversal_samples: List[Dict[str, Any]]):
    """显示反转点详情"""
    logger.info("="*80)
    logger.info("🎯 平安银行反转点详情 (按时间排序)")
    logger.info("="*80)
    
    # 创建价格数据字典便于查找
    price_dict = {}
    for kline in klines:
        date_str = str(kline['date'])[:10]  # 只取日期部分
        price_dict[date_str] = {
            'close': kline['close'],
            'high': kline['highest'],
            'low': kline['lowest'],
            'volume': kline['volume']
        }
    
    for i, sample in enumerate(reversal_samples, 1):
        reversal_date = str(sample['reversal_date'])[:10]
        peak_date = str(sample['reversal_peak_date'])[:10]
        
        # 获取价格信息
        reversal_price_info = price_dict.get(reversal_date, {})
        peak_price_info = price_dict.get(peak_date, {})
        
        logger.info(f"\n📈 反转点 #{i:2d}: {reversal_date}")
        logger.info(f"   📍 反转价格: {sample['reversal_price']:.2f}元")
        logger.info(f"   📈 最大收益: {sample['reversal_gain']*100:.1f}%")
        logger.info(f"   ⏱️  持续时间: {sample['reversal_duration']}周")
        logger.info(f"   🎯 峰值日期: {peak_date}")
        logger.info(f"   📊 峰值价格: {sample['reversal_peak_price']:.2f}元")
        
        # 显示技术指标
        features = sample['features']
        logger.info(f"   🔧 技术指标:")
        logger.info(f"     价格位置: {features['price_position']:.3f} (0=最低, 1=最高)")
        logger.info(f"     均线收敛: {features['ma_convergence']:.3f}")
        logger.info(f"     MA20斜率: {features['ma20_slope']:.3f}")
        logger.info(f"     MA60斜率: {features['ma60_slope']:.3f}")
        logger.info(f"     波动性: {features['volatility']:.3f}")
        logger.info(f"     RSI: {features['rsi']:.1f}")
        logger.info(f"     布林带位置: {features['bb_position']:.3f}")
        
        # 显示前后价格对比
        if reversal_price_info and peak_price_info:
            logger.info(f"   📊 价格对比:")
            logger.info(f"     反转日收盘: {reversal_price_info.get('close', 0):.2f}元")
            logger.info(f"     反转日最高: {reversal_price_info.get('high', 0):.2f}元")
            logger.info(f"     反转日最低: {reversal_price_info.get('low', 0):.2f}元")
            logger.info(f"     峰值日收盘: {peak_price_info.get('close', 0):.2f}元")


def save_reversal_csv(reversal_samples: List[Dict[str, Any]]):
    """保存反转点到CSV文件便于分析"""
    csv_file = Path(__file__).parent / "pingan_reversals_analysis.csv"
    
    # 准备数据
    data = []
    for i, sample in enumerate(reversal_samples, 1):
        features = sample['features']
        row = {
            '序号': i,
            '反转日期': str(sample['reversal_date'])[:10],
            '反转价格': round(sample['reversal_price'], 2),
            '最大收益(%)': round(sample['reversal_gain'] * 100, 1),
            '持续时间(周)': sample['reversal_duration'],
            '峰值日期': str(sample['reversal_peak_date'])[:10],
            '峰值价格': round(sample['reversal_peak_price'], 2),
            '价格位置': round(features['price_position'], 3),
            '均线收敛': round(features['ma_convergence'], 3),
            'MA20斜率': round(features['ma20_slope'], 3),
            'MA60斜率': round(features['ma60_slope'], 3),
            '波动性': round(features['volatility'], 3),
            '成交量比': round(features['volume_ratio'], 3),
            'RSI': round(features['rsi'], 1),
            '布林带位置': round(features['bb_position'], 3)
        }
        data.append(row)
    
    # 保存到CSV
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    logger.info(f"💾 反转点分析已保存到: {csv_file}")
    logger.info(f"📊 共 {len(data)} 个反转点，可以用Excel打开查看")


def show_specific_periods(reversal_samples: List[Dict[str, Any]]):
    """显示特定时期的反转点"""
    logger.info("\n" + "="*80)
    logger.info("📅 按年份分组的反转点")
    logger.info("="*80)
    
    # 按年份分组
    years = {}
    for sample in reversal_samples:
        date_str = str(sample['reversal_date'])[:10]
        year = date_str[:4]
        if year not in years:
            years[year] = []
        years[year].append(sample)
    
    for year in sorted(years.keys()):
        samples = years[year]
        logger.info(f"\n🗓️  {year}年: {len(samples)}个反转点")
        
        for sample in samples:
            date_str = str(sample['reversal_date'])[:10]
            gain_pct = sample['reversal_gain'] * 100
            logger.info(f"   {date_str}: {sample['reversal_price']:.2f}元 → {gain_pct:.1f}%")


def show_high_performance_reversals(reversal_samples: List[Dict[str, Any]]):
    """显示高收益反转点"""
    logger.info("\n" + "="*80)
    logger.info("🏆 高收益反转点 (收益>20%)")
    logger.info("="*80)
    
    high_performance = [s for s in reversal_samples if s['reversal_gain'] > 0.20]
    
    if not high_performance:
        logger.info("❌ 没有找到收益>20%的反转点")
        return
    
    for sample in high_performance:
        date_str = str(sample['reversal_date'])[:10]
        gain_pct = sample['reversal_gain'] * 100
        logger.info(f"📈 {date_str}: {sample['reversal_price']:.2f}元 → {gain_pct:.1f}%")


if __name__ == "__main__":
    show_pingan_reversals()
