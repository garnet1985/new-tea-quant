#!/usr/bin/env python3
"""
反转趋势样本识别脚本

目标：
1. 在历史数据中找到真正的"反转趋势"样本
2. 分析哪些特征与反转成功最相关
3. 为机器学习提供高质量的训练数据
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import json
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

# 设置工作目录
os.chdir(str(project_root))

from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader
from utils.date.date_utils import DateUtils


class ReversalSampleFinder:
    """反转趋势样本识别器"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.data_loader = DataLoader(db)
        
    def find_reversal_samples(self, 
                            stock_list: List[str] = None,
                            start_date: str = "20100101",
                            end_date: str = "20241231",
                            min_reversal_gain: float = 0.15,  # 至少15%的反转收益
                            min_reversal_duration: int = 20,  # 至少20天的反转持续时间
                            max_lookback_days: int = 365):    # 最多回看365天
        """
        识别反转趋势样本
        
        Args:
            stock_list: 股票列表，None表示所有股票
            start_date: 开始日期
            end_date: 结束日期
            min_reversal_gain: 最小反转收益
            min_reversal_duration: 最小反转持续时间
            max_lookback_days: 最大回看天数
        """
        logger.info(f"🔍 开始识别反转趋势样本")
        logger.info(f"参数: 最小收益={min_reversal_gain*100:.1f}%, 最小持续时间={min_reversal_duration}天")
        
        reversal_samples = []
        
        # 获取股票列表
        if not stock_list:
            stock_list = self._get_stock_list()
            
        logger.info(f"📊 将分析 {len(stock_list)} 只股票")
        
        for i, stock_id in enumerate(stock_list):
            if i % 100 == 0:
                logger.info(f"进度: {i}/{len(stock_list)} ({i/len(stock_list)*100:.1f}%)")
                
            try:
                samples = self._find_stock_reversals(
                    stock_id, start_date, end_date,
                    min_reversal_gain, min_reversal_duration, max_lookback_days
                )
                reversal_samples.extend(samples)
                
            except Exception as e:
                logger.debug(f"分析股票 {stock_id} 时出错: {e}")
                continue
        
        logger.info(f"✅ 识别完成，找到 {len(reversal_samples)} 个反转样本")
        return reversal_samples
    
    def _get_stock_list(self) -> List[str]:
        """获取股票列表"""
        try:
            stock_table = self.db.get_table_instance('stock_list')
            stocks = stock_table.load(columns=['stock_id'])
            return [stock['stock_id'] for stock in stocks]
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    def _find_stock_reversals(self, 
                            stock_id: str,
                            start_date: str,
                            end_date: str,
                            min_reversal_gain: float,
                            min_reversal_duration: int,
                            max_lookback_days: int) -> List[Dict[str, Any]]:
        """
        找到单只股票的反转样本
        """
        try:
            # 获取股票K线数据
            klines = self.data_loader.load_stock_klines(
                stock_id, start_date, end_date, terms=['daily']
            )
            
            if not klines or len(klines) < 100:
                return []
            
            # 计算技术指标
            klines_with_indicators = self._add_technical_indicators(klines)
            
            reversal_samples = []
            
            # 遍历每个可能的反转点
            for i in range(max_lookback_days, len(klines_with_indicators) - min_reversal_duration):
                current_date = klines_with_indicators[i]['date']
                current_price = klines_with_indicators[i]['close']
                
                # 检查是否为潜在反转点
                if self._is_potential_reversal_point(klines_with_indicators, i):
                    # 检查后续是否有反转收益
                    reversal_result = self._check_reversal_success(
                        klines_with_indicators, i, min_reversal_gain, min_reversal_duration
                    )
                    
                    if reversal_result['is_success']:
                        # 计算反转点前的特征
                        features = self._calculate_reversal_features(
                            klines_with_indicators, i
                        )
                        
                        sample = {
                            'stock_id': stock_id,
                            'reversal_date': current_date,
                            'reversal_price': current_price,
                            'reversal_gain': reversal_result['max_gain'],
                            'reversal_duration': reversal_result['duration'],
                            'reversal_peak_date': reversal_result['peak_date'],
                            'reversal_peak_price': reversal_result['peak_price'],
                            'features': features,
                            'market_context': self._get_market_context(klines_with_indicators, i)
                        }
                        
                        reversal_samples.append(sample)
            
            return reversal_samples
            
        except Exception as e:
            logger.debug(f"分析股票 {stock_id} 反转时出错: {e}")
            return []
    
    def _add_technical_indicators(self, klines: List[Dict]) -> List[Dict]:
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
        df['rsi'] = self._calculate_rsi(df['close'])
        
        # 计算布林带
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
        
        return df.to_dict('records')
    
    def _is_potential_reversal_point(self, klines: List[Dict], index: int) -> bool:
        """
        判断是否为潜在反转点
        
        条件：
        1. 价格在历史低位附近
        2. 均线收敛
        3. 波动性较小
        4. 成交量相对较低
        """
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
        
        # 4. 成交量检查
        recent_volumes = [k['volume'] for k in recent_klines if k['volume'] > 0]
        avg_volume = np.mean(recent_volumes) if recent_volumes else 1
        volume_ratio = current['volume'] / avg_volume if avg_volume > 0 else 1
        
        # 反转点判断条件
        conditions = [
            price_position < 0.3,      # 价格在历史区间30%以下
            ma_std < 0.1,              # 均线收敛
            volatility < 0.05,         # 波动性较小
            volume_ratio < 1.5,        # 成交量不过分放大
            current.get('rsi', 50) < 60  # RSI不过热
        ]
        
        return sum(conditions) >= 3  # 至少满足3个条件
    
    def _check_reversal_success(self, klines: List[Dict], start_index: int, 
                              min_gain: float, min_duration: int) -> Dict[str, Any]:
        """
        检查反转是否成功
        
        返回：
        - is_success: 是否成功
        - max_gain: 最大收益
        - duration: 持续时间
        - peak_date: 峰值日期
        - peak_price: 峰值价格
        """
        start_price = klines[start_index]['close']
        max_gain = 0
        peak_index = start_index
        peak_price = start_price
        
        # 检查后续30天内的表现
        for i in range(start_index + 1, min(start_index + 30, len(klines))):
            current_price = klines[i]['close']
            gain = (current_price - start_price) / start_price
            
            if gain > max_gain:
                max_gain = gain
                peak_index = i
                peak_price = current_price
            
            # 如果收益达到目标且持续时间足够
            if gain >= min_gain and (i - start_index) >= min_duration:
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
    
    def _calculate_reversal_features(self, klines: List[Dict], index: int) -> Dict[str, float]:
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
        features['ma20_slope'] = self._calculate_ma_slope(recent_klines, 'ma20')
        features['ma60_slope'] = self._calculate_ma_slope(recent_klines, 'ma60')
        
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
        
        return features
    
    def _get_market_context(self, klines: List[Dict], index: int) -> Dict[str, Any]:
        """获取市场背景信息"""
        # 这里可以添加市场指数的相关信息
        return {
            'market_trend': 'neutral',  # 简化处理
            'market_volatility': 'normal'
        }
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> tuple:
        """计算布林带"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    def _calculate_ma_slope(self, klines: List[Dict], ma_type: str, period: int = 5) -> float:
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
    
    def save_samples(self, samples: List[Dict[str, Any]], filename: str = "reversal_samples.json"):
        """保存反转样本"""
        output_path = Path(__file__).parent / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"💾 反转样本已保存到: {output_path}")
    
    def analyze_samples(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            'feature_correlations': features_df.corr()['reversal_gain'].to_dict(),
            'feature_stats': features_df.describe().to_dict()
        }
        
        return analysis


def main():
    """主函数"""
    logger.info("🚀 启动反转趋势样本识别")
    
    # 初始化数据库
    db = DatabaseManager()
    db.initialize()
    
    # 创建识别器
    finder = ReversalSampleFinder(db)
    
    # 识别反转样本
    samples = finder.find_reversal_samples(
        stock_list=None,  # 分析所有股票
        start_date="20200101",  # 从2020年开始
        end_date="20241231",    # 到2024年结束
        min_reversal_gain=0.15,  # 至少15%收益
        min_reversal_duration=20  # 至少20天
    )
    
    # 保存样本
    finder.save_samples(samples)
    
    # 分析样本
    analysis = finder.analyze_samples(samples)
    
    # 保存分析结果
    analysis_path = Path(__file__).parent / "reversal_analysis.json"
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"📊 分析结果已保存到: {analysis_path}")
    logger.info(f"✅ 识别完成！找到 {len(samples)} 个反转样本")


if __name__ == "__main__":
    main()
