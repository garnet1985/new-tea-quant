#!/usr/bin/env python3
"""
平安银行反转点识别测试脚本

使用周线数据识别平安银行的历史反转点，验证反转样本识别逻辑
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import json
from typing import List, Dict, Any, Optional


def test_pingan_reversal():
    """测试平安银行的反转点识别"""
    from start import App
    from app.data_loader.loaders import KlineLoader
    
    logger.info("🚀 开始测试平安银行反转点识别")
    
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
        
        # 添加技术指标
        klines_with_indicators = add_technical_indicators(weekly_klines)
        
        # 寻找反转点
        reversal_samples = find_stock_reversals(klines_with_indicators, stock_id, min_gain=0.15)
        
        logger.info(f"🎯 找到 {len(reversal_samples)} 个反转样本")
        
        # 打印详细结果
        print_reversal_details(reversal_samples)
        
        # 保存结果
        save_results(reversal_samples, stock_id)
        
        # 分析特征分布
        analyze_reversal_features(reversal_samples)
        
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
    
    # 计算RSI
    df['rsi'] = calculate_rsi(df['close'])
    
    # 计算布林带
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df['close'])
    
    # 计算价格位置
    df['price_position'] = df['close'].rolling(window=60).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() > x.min() else 0
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


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2) -> tuple:
    """计算布林带"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower


def find_stock_reversals(klines: List[Dict], stock_id: str, min_gain: float = 0.15) -> List[Dict[str, Any]]:
    """找到单只股票的反转样本"""
    reversal_samples = []
    
    # 使用周线数据，需要更长的历史数据
    min_history = 60  # 至少60周的历史数据
    min_future = 20   # 至少20周的未来数据
    
    for i in range(min_history, len(klines) - min_future):
        current = klines[i]
        
        # 检查是否为潜在反转点
        if is_potential_reversal_point(klines, i):
            # 检查后续是否有反转收益
            reversal_result = check_reversal_success(klines, i, min_gain, min_future)
            
            if reversal_result['is_success']:
                # 计算反转点前的特征
                features = calculate_reversal_features(klines, i)
                
                sample = {
                    'stock_id': stock_id,
                    'reversal_date': current['date'],
                    'reversal_price': current['close'],
                    'reversal_gain': reversal_result['max_gain'],
                    'reversal_duration': reversal_result['duration'],
                    'reversal_peak_date': reversal_result['peak_date'],
                    'reversal_peak_price': reversal_result['peak_price'],
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
    
    # 3. 波动性检查（周线数据）
    recent_returns = []
    for i in range(1, len(recent_klines)):
        if recent_klines[i-1]['close'] > 0:
            ret = (recent_klines[i]['close'] - recent_klines[i-1]['close']) / recent_klines[i-1]['close']
            recent_returns.append(abs(ret))
    volatility = np.mean(recent_returns) if recent_returns else 1
    
    # 4. 成交量检查
    recent_volumes = [k['volume'] for k in recent_klines if k['volume'] > 0]
    avg_volume = np.mean(recent_volumes) if recent_volumes else 1
    volume_ratio = current['volume'] / avg_volume if avg_volume > 0 else 1
    
    # 5. 布林带位置检查
    bb_position = 0
    if current.get('bb_upper', 0) > current.get('bb_lower', 0):
        bb_position = (current['close'] - current['bb_lower']) / (current['bb_upper'] - current['bb_lower'])
    
    # 反转点判断条件（周线数据，条件稍微放宽）
    conditions = [
        price_position < 0.4,      # 价格在历史区间40%以下
        ma_std < 0.15,             # 均线收敛（周线数据放宽）
        volatility < 0.08,         # 波动性较小
        volume_ratio < 2.0,        # 成交量不过分放大
        current.get('rsi', 50) < 65,  # RSI不过热
        bb_position < 0.3,         # 在布林带下方
    ]
    
    satisfied_conditions = sum(conditions)
    
    # 打印调试信息
    if satisfied_conditions >= 3:
        logger.debug(f"潜在反转点 {current['date']}: 价格位置={price_position:.3f}, 均线收敛={ma_std:.3f}, "
                    f"波动性={volatility:.3f}, 成交量比={volume_ratio:.3f}, RSI={current.get('rsi', 50):.1f}, "
                    f"布林带位置={bb_position:.3f}, 满足条件={satisfied_conditions}")
    
    return satisfied_conditions >= 3  # 至少满足3个条件


def check_reversal_success(klines: List[Dict], start_index: int, min_gain: float, max_weeks: int) -> Dict[str, Any]:
    """检查反转是否成功"""
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
    
    # 成交量特征
    recent_volumes = [k['volume'] for k in recent_klines if k['volume'] > 0]
    avg_volume = np.mean(recent_volumes) if recent_volumes else 1
    features['volume_ratio'] = current['volume'] / avg_volume if avg_volume > 0 else 1
    
    # RSI特征
    features['rsi'] = current.get('rsi', 50)
    
    # 布林带特征
    if current.get('bb_upper', 0) > current.get('bb_lower', 0):
        features['bb_position'] = (current['close'] - current['bb_lower']) / (current['bb_upper'] - current['bb_lower'])
    else:
        features['bb_position'] = 0.5
    
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


def print_reversal_details(reversal_samples: List[Dict[str, Any]]):
    """打印反转点详细信息"""
    logger.info("="*80)
    logger.info("🎯 平安银行反转点详情")
    logger.info("="*80)
    
    for i, sample in enumerate(reversal_samples, 1):
        logger.info(f"\n📈 反转点 #{i}:")
        logger.info(f"  日期: {sample['reversal_date']}")
        logger.info(f"  价格: {sample['reversal_price']:.2f}")
        logger.info(f"  最大收益: {sample['reversal_gain']*100:.1f}%")
        logger.info(f"  持续时间: {sample['reversal_duration']}周")
        logger.info(f"  峰值日期: {sample['reversal_peak_date']}")
        logger.info(f"  峰值价格: {sample['reversal_peak_price']:.2f}")
        
        features = sample['features']
        logger.info(f"  特征:")
        logger.info(f"    价格位置: {features['price_position']:.3f}")
        logger.info(f"    均线收敛: {features['ma_convergence']:.3f}")
        logger.info(f"    MA20斜率: {features['ma20_slope']:.3f}")
        logger.info(f"    MA60斜率: {features['ma60_slope']:.3f}")
        logger.info(f"    波动性: {features['volatility']:.3f}")
        logger.info(f"    成交量比: {features['volume_ratio']:.3f}")
        logger.info(f"    RSI: {features['rsi']:.1f}")
        logger.info(f"    布林带位置: {features['bb_position']:.3f}")


def save_results(reversal_samples: List[Dict[str, Any]], stock_id: str):
    """保存结果到文件"""
    output_path = Path(__file__).parent / f"pingan_reversal_samples_{stock_id.replace('.', '_')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(reversal_samples, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"💾 反转样本已保存到: {output_path}")


def analyze_reversal_features(reversal_samples: List[Dict[str, Any]]):
    """分析反转特征分布"""
    if not reversal_samples:
        logger.info("❌ 没有找到反转样本，无法进行特征分析")
        return
    
    logger.info("\n📊 反转特征分析:")
    logger.info("="*50)
    
    # 提取特征数据
    features_list = [sample['features'] for sample in reversal_samples]
    gains = [sample['reversal_gain'] for sample in reversal_samples]
    
    # 计算特征统计
    feature_names = ['price_position', 'ma_convergence', 'ma20_slope', 'ma60_slope', 
                    'volatility', 'volume_ratio', 'rsi', 'bb_position']
    
    for feature_name in feature_names:
        values = [f.get(feature_name, 0) for f in features_list]
        logger.info(f"{feature_name}: 平均={np.mean(values):.3f}, 最小={np.min(values):.3f}, 最大={np.max(values):.3f}")
    
    # 分析收益分布
    logger.info(f"\n📈 收益分析:")
    logger.info(f"平均收益: {np.mean(gains)*100:.1f}%")
    logger.info(f"最大收益: {np.max(gains)*100:.1f}%")
    logger.info(f"最小收益: {np.min(gains)*100:.1f}%")
    logger.info(f"收益标准差: {np.std(gains)*100:.1f}%")


if __name__ == "__main__":
    test_pingan_reversal()
