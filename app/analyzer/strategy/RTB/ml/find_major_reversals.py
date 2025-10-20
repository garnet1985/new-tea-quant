#!/usr/bin/env python3
"""
重大反转点识别脚本 - 严格版本

目标：识别真正的重大反转点，数量控制在10个左右
适用：中长线RTB策略
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import json
from typing import List, Dict, Any, Optional


def find_major_reversals():
    """识别平安银行的重大反转点"""
    from start import App
    from app.data_loader.loaders import KlineLoader
    
    logger.info("🎯 开始识别平安银行重大反转点（严格版本）")
    
    # 初始化应用
    app = App()
    kline_loader = KlineLoader(app.db)
    
    # 获取平安银行的周线数据
    stock_id = "000001.SZ"
    start_date = "20180101"
    end_date = "20241231"
    
    logger.info(f"📊 获取平安银行({stock_id})周线数据: {start_date} - {end_date}")
    
    try:
        # 加载周线数据
        weekly_klines = kline_loader.load_weekly_qfq(stock_id, start_date, end_date)
        logger.info(f"✅ 成功加载 {len(weekly_klines)} 条周线数据")
        
        if len(weekly_klines) < 100:
            logger.error("❌ 数据不足，无法进行分析")
            return
        
        # 添加技术指标
        klines_with_indicators = add_technical_indicators(weekly_klines)
        
        # 寻找重大反转点（严格条件）
        major_reversals = find_stock_major_reversals(klines_with_indicators, stock_id)
        
        logger.info(f"🎯 找到 {len(major_reversals)} 个重大反转点")
        
        # 显示详细结果
        show_major_reversal_details(major_reversals)
        
        # 保存结果
        save_major_reversals(major_reversals, stock_id)
        
    except Exception as e:
        logger.error(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


def add_technical_indicators(klines: List[Dict]) -> List[Dict]:
    """添加技术指标"""
    df = pd.DataFrame(klines)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # 计算移动平均线
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    df['ma120'] = df['close'].rolling(window=120).mean()
    
    # 计算RSI
    df['rsi'] = calculate_rsi(df['close'])
    
    # 计算价格位置（更长期的历史区间）
    df['price_position_2y'] = df['close'].rolling(window=104).apply(  # 2年
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() > x.min() else 0
    )
    
    # 计算前期跌幅
    df['decline_from_peak'] = df['close'].rolling(window=52).apply(  # 1年
        lambda x: (x.max() - x.iloc[-1]) / x.max() if x.max() > 0 else 0
    )
    
    return df.to_dict('records')


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """计算RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def find_stock_major_reversals(klines: List[Dict], stock_id: str) -> List[Dict[str, Any]]:
    """找到重大反转点（严格条件）"""
    major_reversals = []
    
    # 需要更长的历史数据
    min_history = 120  # 至少120周的历史数据
    min_future = 40    # 至少40周的未来数据
    
    for i in range(min_history, len(klines) - min_future):
        current = klines[i]
        
        # 检查是否为重大反转点
        if is_major_reversal_point(klines, i):
            # 检查后续是否有重大反转收益
            reversal_result = check_major_reversal_success(klines, i, min_gain=0.25, max_weeks=60)
            
            if reversal_result['is_success']:
                # 计算反转点前的特征
                features = calculate_major_reversal_features(klines, i)
                
                reversal = {
                    'stock_id': stock_id,
                    'reversal_date': current['date'],
                    'reversal_price': current['close'],
                    'reversal_gain': reversal_result['max_gain'],
                    'reversal_duration': reversal_result['duration'],
                    'reversal_peak_date': reversal_result['peak_date'],
                    'reversal_peak_price': reversal_result['peak_price'],
                    'features': features
                }
                
                major_reversals.append(reversal)
    
    return major_reversals


def is_major_reversal_point(klines: List[Dict], index: int) -> bool:
    """判断是否为重大反转点（严格条件）"""
    if index < 120:
        return False
        
    current = klines[index]
    recent_klines = klines[index-120:index]
    
    # 1. 价格位置检查（2年历史区间）
    recent_closes = [k['close'] for k in recent_klines]
    min_price = min(recent_closes)
    max_price = max(recent_closes)
    price_position_2y = (current['close'] - min_price) / (max_price - min_price)
    
    # 2. 前期跌幅检查（1年内从峰值下跌）
    peak_price = max(recent_closes)
    decline_from_peak = (peak_price - current['close']) / peak_price
    
    # 3. 均线收敛检查（更严格）
    ma_values = [current.get('ma5', 0), current.get('ma10', 0), 
                current.get('ma20', 0), current.get('ma60', 0)]
    ma_std = np.std(ma_values) / current['close'] if current['close'] > 0 else 1
    
    # 4. 长期趋势检查（MA120）
    ma120_slope = calculate_ma_slope(recent_klines, 'ma120', period=10)
    
    # 5. RSI超卖检查
    rsi = current.get('rsi', 50)
    
    # 6. 波动性检查
    recent_returns = []
    for i in range(1, len(recent_klines)):
        if recent_klines[i-1]['close'] > 0:
            ret = (recent_klines[i]['close'] - recent_klines[i-1]['close']) / recent_klines[i-1]['close']
            recent_returns.append(abs(ret))
    volatility = np.mean(recent_returns) if recent_returns else 1
    
    # 重大反转点判断条件（严格）
    conditions = [
        price_position_2y < 0.15,      # 价格在2年历史区间15%以下
        decline_from_peak > 0.30,      # 从峰值下跌超过30%
        ma_std < 0.08,                 # 均线收敛
        ma120_slope < 0.005,           # 长期趋势不向上
        rsi < 35,                      # RSI超卖
        volatility < 0.04,             # 波动性较小
    ]
    
    satisfied_conditions = sum(conditions)
    
    # 打印调试信息
    if satisfied_conditions >= 5:  # 至少满足5个条件
        logger.debug(f"重大反转点 {current['date']}: 价格位置2年={price_position_2y:.3f}, "
                    f"前期跌幅={decline_from_peak:.3f}, 均线收敛={ma_std:.3f}, "
                    f"MA120斜率={ma120_slope:.3f}, RSI={rsi:.1f}, 波动性={volatility:.3f}, "
                    f"满足条件={satisfied_conditions}")
    
    return satisfied_conditions >= 5  # 至少满足5个严格条件


def check_major_reversal_success(klines: List[Dict], start_index: int, min_gain: float, max_weeks: int) -> Dict[str, Any]:
    """检查重大反转是否成功"""
    start_price = klines[start_index]['close']
    max_gain = 0
    peak_index = start_index
    peak_price = start_price
    
    # 检查后续周数内的表现
    for i in range(start_index + 1, min(start_index + max_weeks, len(klines))):
        current_price = klines[i]['close']
        gain = (current_price - start_price) / start_price
        
        if gain > max_gain:
            max_gain = gain
            peak_index = i
            peak_price = current_price
        
        # 如果收益达到目标
        if gain >= min_gain:
            return {
                'is_success': True,
                'max_gain': max_gain,
                'duration': i - start_index,
                'peak_date': klines[peak_index]['date'],
                'peak_price': peak_price
            }
    
    return {
        'is_success': max_gain >= min_gain,
        'max_gain': max_gain,
        'duration': peak_index - start_index,
        'peak_date': klines[peak_index]['date'],
        'peak_price': peak_price
    }


def calculate_major_reversal_features(klines: List[Dict], index: int) -> Dict[str, float]:
    """计算重大反转点前的特征"""
    current = klines[index]
    recent_klines = klines[max(0, index-120):index]
    
    features = {}
    
    # 价格位置特征（2年）
    recent_closes = [k['close'] for k in recent_klines]
    min_price = min(recent_closes)
    max_price = max(recent_closes)
    features['price_position_2y'] = (current['close'] - min_price) / (max_price - min_price)
    
    # 前期跌幅特征
    peak_price = max(recent_closes)
    features['decline_from_peak'] = (peak_price - current['close']) / peak_price
    
    # 均线特征
    ma_values = [current.get('ma5', 0), current.get('ma10', 0), 
                current.get('ma20', 0), current.get('ma60', 0)]
    features['ma_convergence'] = np.std(ma_values) / current['close'] if current['close'] > 0 else 1
    features['ma20_slope'] = calculate_ma_slope(recent_klines, 'ma20')
    features['ma60_slope'] = calculate_ma_slope(recent_klines, 'ma60')
    features['ma120_slope'] = calculate_ma_slope(recent_klines, 'ma120')
    
    # 波动性特征
    recent_returns = []
    for i in range(1, len(recent_klines)):
        if recent_klines[i-1]['close'] > 0:
            ret = (recent_klines[i]['close'] - recent_klines[i-1]['close']) / recent_klines[i-1]['close']
            recent_returns.append(abs(ret))
    features['volatility'] = np.mean(recent_returns) if recent_returns else 0
    
    # RSI特征
    features['rsi'] = current.get('rsi', 50)
    
    return features


def calculate_ma_slope(klines: List[Dict], ma_type: str, period: int = 10) -> float:
    """计算均线斜率"""
    if len(klines) < period:
        return 0
        
    ma_values = [k.get(ma_type, 0) for k in klines[-period:] if k.get(ma_type, 0) > 0]
    if len(ma_values) < 2:
        return 0
        
    # 简单线性回归计算斜率
    x = np.arange(len(ma_values))
    y = np.array(ma_values)
    slope = np.polyfit(x, y, 1)[0]
    return slope / y[0] if y[0] > 0 else 0  # 归一化斜率


def show_major_reversal_details(major_reversals: List[Dict[str, Any]]):
    """显示重大反转点详细信息"""
    logger.info("="*80)
    logger.info("🎯 平安银行重大反转点详情（严格版本）")
    logger.info("="*80)
    
    for i, reversal in enumerate(major_reversals, 1):
        logger.info(f"\n📈 重大反转点 #{i}:")
        logger.info(f"  日期: {reversal['reversal_date']}")
        logger.info(f"  价格: {reversal['reversal_price']:.2f}元")
        logger.info(f"  最大收益: {reversal['reversal_gain']*100:.1f}%")
        logger.info(f"  持续时间: {reversal['reversal_duration']}周")
        logger.info(f"  峰值日期: {reversal['reversal_peak_date']}")
        logger.info(f"  峰值价格: {reversal['reversal_peak_price']:.2f}元")
        
        features = reversal['features']
        logger.info(f"  特征:")
        logger.info(f"    2年价格位置: {features['price_position_2y']:.3f}")
        logger.info(f"    前期跌幅: {features['decline_from_peak']*100:.1f}%")
        logger.info(f"    均线收敛: {features['ma_convergence']:.3f}")
        logger.info(f"    MA20斜率: {features['ma20_slope']:.3f}")
        logger.info(f"    MA60斜率: {features['ma60_slope']:.3f}")
        logger.info(f"    MA120斜率: {features['ma120_slope']:.3f}")
        logger.info(f"    波动性: {features['volatility']:.3f}")
        logger.info(f"    RSI: {features['rsi']:.1f}")


def save_major_reversals(major_reversals: List[Dict[str, Any]], stock_id: str):
    """保存重大反转点到文件"""
    output_path = Path(__file__).parent / f"major_reversals_{stock_id.replace('.', '_')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(major_reversals, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"💾 重大反转点已保存到: {output_path}")
    
    # 同时保存CSV
    csv_path = Path(__file__).parent / f"major_reversals_{stock_id.replace('.', '_')}.csv"
    if major_reversals:
        df = pd.DataFrame(major_reversals)
        features_df = pd.json_normalize(df['features'])
        result_df = pd.concat([df[['stock_id', 'reversal_date', 'reversal_price', 'reversal_gain', 'reversal_duration']], features_df], axis=1)
        result_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"📊 CSV文件已保存到: {csv_path}")


if __name__ == "__main__":
    find_major_reversals()
