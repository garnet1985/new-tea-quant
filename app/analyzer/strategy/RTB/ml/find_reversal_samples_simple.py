#!/usr/bin/env python3
"""
反转趋势样本识别脚本 - 简化版本
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import json
from typing import List, Dict, Any, Optional


def find_reversal_samples_simple(db, data_loader, 
                                start_date: str = "20200101",
                                end_date: str = "20241231",
                                min_reversal_gain: float = 0.15,
                                max_stocks: int = 50):  # 限制股票数量进行测试
    """
    简化版反转样本识别
    """
    logger.info(f"🔍 开始识别反转趋势样本 (测试版本，限制{max_stocks}只股票)")
    
    # 获取股票列表
    try:
        stock_table = db.get_table_instance('stock_list')
        stocks = stock_table.load(limit=max_stocks)
        stock_list = [stock['id'] for stock in stocks]
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return []
    
    logger.info(f"📊 将分析 {len(stock_list)} 只股票")
    
    reversal_samples = []
    
    for i, stock_id in enumerate(stock_list):
        if i % 10 == 0:
            logger.info(f"进度: {i}/{len(stock_list)} ({i/len(stock_list)*100:.1f}%)")
        
        try:
            # 获取股票K线数据
            klines = data_loader.load_stock_klines(
                stock_id, start_date, end_date, terms=['daily']
            )
            
            if not klines or len(klines) < 100:
                continue
            
            # 计算技术指标
            klines_with_indicators = add_technical_indicators(klines)
            
            # 寻找反转点
            samples = find_stock_reversals(klines_with_indicators, stock_id, min_reversal_gain)
            reversal_samples.extend(samples)
            
        except Exception as e:
            logger.debug(f"分析股票 {stock_id} 时出错: {e}")
            continue
    
    logger.info(f"✅ 识别完成，找到 {len(reversal_samples)} 个反转样本")
    return reversal_samples


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
    
    # 计算RSI
    df['rsi'] = calculate_rsi(df['close'])
    
    return df.to_dict('records')


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """计算RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def find_stock_reversals(klines: List[Dict], stock_id: str, min_gain: float) -> List[Dict[str, Any]]:
    """找到单只股票的反转样本"""
    reversal_samples = []
    
    for i in range(60, len(klines) - 30):  # 确保有足够的历史数据和未来数据
        current = klines[i]
        
        # 检查是否为潜在反转点
        if is_potential_reversal_point(klines, i):
            # 检查后续是否有反转收益
            reversal_result = check_reversal_success(klines, i, min_gain)
            
            if reversal_result['is_success']:
                # 计算反转点前的特征
                features = calculate_reversal_features(klines, i)
                
                sample = {
                    'stock_id': stock_id,
                    'reversal_date': current['date'],
                    'reversal_price': current['close'],
                    'reversal_gain': reversal_result['max_gain'],
                    'reversal_duration': reversal_result['duration'],
                    'features': features
                }
                
                reversal_samples.append(sample)
    
    return reversal_samples


def is_potential_reversal_point(klines: List[Dict], index: int) -> bool:
    """判断是否为潜在反转点"""
    if index < 60:
        return False
        
    current = klines[index]
    recent_klines = klines[index-60:index]
    
    # 1. 价格位置检查
    recent_closes = [k['close'] for k in recent_klines]
    min_price = min(recent_closes)
    max_price = max(recent_closes)
    price_position = (current['close'] - min_price) / (max_price - min_price)
    
    # 2. 均线收敛检查
    ma_values = [current.get('ma5', 0), current.get('ma10', 0), 
                current.get('ma20', 0), current.get('ma60', 0)]
    ma_std = np.std(ma_values) / current['close'] if current['close'] > 0 else 1
    
    # 3. 波动性检查
    recent_returns = []
    for i in range(1, len(recent_klines)):
        if recent_klines[i-1]['close'] > 0:
            ret = (recent_klines[i]['close'] - recent_klines[i-1]['close']) / recent_klines[i-1]['close']
            recent_returns.append(abs(ret))
    volatility = np.mean(recent_returns) if recent_returns else 1
    
    # 反转点判断条件
    conditions = [
        price_position < 0.3,      # 价格在历史区间30%以下
        ma_std < 0.1,              # 均线收敛
        volatility < 0.05,         # 波动性较小
        current.get('rsi', 50) < 60  # RSI不过热
    ]
    
    return sum(conditions) >= 3  # 至少满足3个条件


def check_reversal_success(klines: List[Dict], start_index: int, min_gain: float) -> Dict[str, Any]:
    """检查反转是否成功"""
    start_price = klines[start_index]['close']
    max_gain = 0
    peak_index = start_index
    
    # 检查后续30天内的表现
    for i in range(start_index + 1, min(start_index + 30, len(klines))):
        current_price = klines[i]['close']
        gain = (current_price - start_price) / start_price
        
        if gain > max_gain:
            max_gain = gain
            peak_index = i
        
        # 如果收益达到目标
        if gain >= min_gain:
            return {
                'is_success': True,
                'max_gain': max_gain,
                'duration': i - start_index
            }
    
    return {
        'is_success': max_gain >= min_gain,
        'max_gain': max_gain,
        'duration': peak_index - start_index
    }


def calculate_reversal_features(klines: List[Dict], index: int) -> Dict[str, float]:
    """计算反转点前的特征"""
    current = klines[index]
    recent_klines = klines[max(0, index-60):index]
    
    features = {}
    
    # 价格位置特征
    recent_closes = [k['close'] for k in recent_klines]
    min_price = min(recent_closes)
    max_price = max(recent_closes)
    features['price_position'] = (current['close'] - min_price) / (max_price - min_price)
    
    # 均线特征
    ma_values = [current.get('ma5', 0), current.get('ma10', 0), 
                current.get('ma20', 0), current.get('ma60', 0)]
    features['ma_convergence'] = np.std(ma_values) / current['close'] if current['close'] > 0 else 1
    features['ma20_slope'] = calculate_ma_slope(recent_klines, 'ma20')
    features['ma60_slope'] = calculate_ma_slope(recent_klines, 'ma60')
    
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


def calculate_ma_slope(klines: List[Dict], ma_type: str, period: int = 5) -> float:
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


def analyze_samples(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析反转样本的特征分布"""
    if not samples:
        return {}
        
    df = pd.DataFrame(samples)
    
    # 提取特征数据
    features_df = pd.json_normalize(df['features'])
    features_df['reversal_gain'] = df['reversal_gain']
    features_df['reversal_duration'] = df['reversal_duration']
    
    analysis = {
        'total_samples': len(samples),
        'avg_reversal_gain': df['reversal_gain'].mean(),
        'avg_reversal_duration': df['reversal_duration'].mean(),
        'feature_correlations': features_df.corr()['reversal_gain'].to_dict() if 'reversal_gain' in features_df.columns else {},
        'feature_stats': features_df.describe().to_dict()
    }
    
    return analysis


def save_samples(samples: List[Dict[str, Any]], filename: str = "reversal_samples.json"):
    """保存反转样本"""
    output_path = Path(__file__).parent / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(samples, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"💾 反转样本已保存到: {output_path}")


def main():
    """主函数 - 需要在start.py中调用"""
    from start import App
    
    logger.info("🚀 启动反转趋势样本识别")
    
    # 初始化应用
    app = App()
    
    # 创建DataLoader
    from app.data_loader import DataLoader
    data_loader = DataLoader(app.db)
    
    # 识别反转样本
    samples = find_reversal_samples_simple(
        db=app.db,
        data_loader=data_loader,
        start_date="20220101",  # 从2022年开始
        end_date="20241231",    # 到2024年结束
        min_reversal_gain=0.15,  # 至少15%收益
        max_stocks=100  # 限制100只股票进行测试
    )
    
    # 保存样本
    save_samples(samples)
    
    # 分析样本
    analysis = analyze_samples(samples)
    
    # 保存分析结果
    analysis_path = Path(__file__).parent / "reversal_analysis.json"
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"📊 分析结果已保存到: {analysis_path}")
    logger.info(f"✅ 识别完成！找到 {len(samples)} 个反转样本")
    
    # 打印关键发现
    if samples:
        logger.info(f"📈 平均反转收益: {analysis['avg_reversal_gain']*100:.1f}%")
        logger.info(f"⏱️ 平均反转持续时间: {analysis['avg_reversal_duration']:.1f}天")
        
        # 打印特征相关性
        correlations = analysis.get('feature_correlations', {})
        logger.info("🔍 特征与反转收益的相关性:")
        for feature, corr in correlations.items():
            if feature != 'reversal_gain':
                logger.info(f"  {feature}: {corr:.3f}")


if __name__ == "__main__":
    main()
