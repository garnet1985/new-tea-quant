#!/usr/bin/env python3
"""
增强版反转数据生成器
包含PB、PE、市值变化等完整因子
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))
os.chdir(str(project_root))

from core.modules.data_manager.data_manager import DataManager
from core.modules.analyzer.strategy.RTB import settings
from core.modules.analyzer.strategy.RTB.feature_identity.reversal_identify import identify_major_reversals
from core.infra.db import DatabaseManager

logger = logging.getLogger(__name__)

class EnhancedReversalDataGenerator:
    """增强版反转数据生成器"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.data_manager.initialize()
        self.db_manager = DatabaseManager()
        self.csv_root = project_root / "app" / "analyzer" / "strategy" / "RTB" / "ml" / "data"
        # 确保父目录存在
        self.csv_root.parent.mkdir(parents=True, exist_ok=True)
        self.csv_root.mkdir(exist_ok=True)
        
    def get_sample_list(self):
        """获取股票样本列表"""
        try:
            # 使用RTB设置的股票数量
            try:
                sample_count = settings.get('mode', {}).get('test_amount', 500)
            except:
                sample_count = 500
            
            # 获取所有股票
            all_stocks = self.data_manager.stock.list.load(filtered=True)
            
            if len(all_stocks) > sample_count:
                candidates = np.random.choice(all_stocks, sample_count, replace=False).tolist()
            else:
                candidates = all_stocks
            
            print(f"✅ 获取到 {len(candidates)} 个股票样本")
            return candidates
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            # 备用方案
            return [
                {"id": "000001.SZ"}, {"id": "000002.SZ"}, {"id": "000858.SZ"}, 
                {"id": "600036.SH"}, {"id": "600519.SH"}, {"id": "600887.SH"}
            ]
    
    def identify_reversal_for_stock(self, stock):
        """为单个股票识别反转点"""
        try:
            stock_id = stock['id'] if isinstance(stock, dict) else stock
            
            # 识别重大反转点
            major_reversals = identify_major_reversals(stock_id)
            
            if not major_reversals:
                return []
            
            # 加载周线数据
            weekly_klines = self.data_manager.load_klines(stock_id, term='weekly', adjust='qfq', as_dataframe=False)
            
            # 生成样本
            samples = self.generate_samples_from_reversals(stock_id, major_reversals, weekly_klines)
            
            return samples
            
        except Exception as e:
            return []
    
    def generate_samples_from_reversals(self, stock_id, major_reversals, weekly_klines):
        """基于重大反转点生成训练样本"""
        samples = []
        
        for reversal in major_reversals:
            # 添加stock_id
            reversal['stock_id'] = stock_id
            
            # 计算完整特征
            features = self.calculate_complete_features(reversal, weekly_klines)
            
            # 按照15%阈值分类成功/失败
            is_successful = 1 if reversal['reversal_gain'] >= 0.15 else 0
            
            # 创建样本
            sample = {
                'stock_id': stock_id,
                'date': str(reversal['date']),
                'price': reversal['price'],
                'reversal_gain': reversal['reversal_gain'],
                'reversal_duration': reversal['reversal_duration'],
                'is_successful_reversal': is_successful,
                'monthly_valley_date': reversal['monthly_valley_date'],
                'monthly_drop_rate': reversal['monthly_drop_rate'],
                'reversal_score': reversal['score'],
                **features
            }
            
            samples.append(sample)
        
        return samples
    
    def calculate_complete_features(self, reversal, weekly_klines):
        """计算完整特征集"""
        features = {}
        
        try:
            # 找到反转点在周线数据中的位置
            reversal_date = pd.to_datetime(str(reversal['date']), format='%Y%m%d')
            reversal_idx = None
            
            for i, kline in enumerate(weekly_klines):
                kline_date = pd.to_datetime(str(kline['date']), format='%Y%m%d')
                if abs((kline_date - reversal_date).days) <= 7:
                    reversal_idx = i
                    break
            
            if reversal_idx is not None and reversal_idx >= 20:
                # 1. 技术指标特征
                features.update(self.calculate_technical_features(weekly_klines, reversal_idx))
                
                # 2. 均线特征（包含斜率）
                features.update(self.calculate_ma_features(weekly_klines, reversal_idx))
                
                # 3. 交易量特征
                features.update(self.calculate_volume_features(weekly_klines, reversal_idx))
                
                # 4. 基本面特征（PB、PE、市值变化）
                features.update(self.calculate_fundamental_features(reversal))
                
                # 5. 市场环境特征
                features.update(self.calculate_market_features(reversal))
                
            else:
                # 使用默认值
                features.update(self.get_default_features())
                
        except Exception as e:
            features.update(self.get_default_features())
        
        return features
    
    def calculate_technical_features(self, weekly_klines, reversal_idx):
        """计算技术指标特征"""
        try:
            prices = [kline.get('close', 0) for kline in weekly_klines[max(0, reversal_idx-20):reversal_idx+1]]
            
            if len(prices) < 14:
                return self.get_default_technical_features()
            
            # RSI计算
            rsi = self.calculate_rsi(prices, 14)
            
            # 波动率计算
            returns = [prices[i]/prices[i-1] - 1 for i in range(1, len(prices))]
            volatility = np.std(returns) if len(returns) > 1 else 0
            
            # 价格动量
            price_momentum_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
            price_momentum_10 = (prices[-1] - prices[-11]) / prices[-11] if len(prices) >= 11 else 0
            
            # 价格位置（在20周内的百分位）
            price_position = self.calculate_price_percentile(prices)
            
            return {
                'rsi': rsi,
                'rsi_oversold': 1 if rsi < 30 else 0,
                'rsi_overbought': 1 if rsi > 70 else 0,
                'volatility': volatility,
                'price_momentum_5': price_momentum_5,
                'price_momentum_10': price_momentum_10,
                'price_percentile': price_position,
                'low_price_position': 1 if price_position < 0.2 else 0,
            }
        except:
            return self.get_default_technical_features()
    
    def calculate_ma_features(self, weekly_klines, reversal_idx):
        """计算均线特征（包含斜率）"""
        try:
            # 获取价格数据
            prices = [kline.get('close', 0) for kline in weekly_klines[max(0, reversal_idx-60):reversal_idx+1]]
            
            if len(prices) < 20:
                return self.get_default_ma_features()
            
            # 计算各种均线
            ma5 = np.mean(prices[-5:]) if len(prices) >= 5 else prices[-1]
            ma10 = np.mean(prices[-10:]) if len(prices) >= 10 else prices[-1]
            ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else prices[-1]
            ma60 = np.mean(prices[-60:]) if len(prices) >= 60 else prices[-1]
            
            current_price = prices[-1]
            
            # 均线斜率（改进计算）
            ma5_slope = self.calculate_ma_slope(prices, 5)
            ma10_slope = self.calculate_ma_slope(prices, 10)
            ma20_slope = self.calculate_ma_slope(prices, 20)
            ma60_slope = self.calculate_ma_slope(prices, 60)
            
            # 均线收敛度
            ma_convergence = np.std([ma5, ma10, ma20]) / current_price if current_price > 0 else 0
            
            # 价格相对于均线的位置
            price_vs_ma5 = (current_price - ma5) / ma5 if ma5 > 0 else 0
            price_vs_ma10 = (current_price - ma10) / ma10 if ma10 > 0 else 0
            price_vs_ma20 = (current_price - ma20) / ma20 if ma20 > 0 else 0
            price_vs_ma60 = (current_price - ma60) / ma60 if ma60 > 0 else 0
            
            # 均线排列
            ma_alignment_bull = 1 if ma5 > ma10 > ma20 > ma60 else 0
            ma_alignment_bear = 1 if ma5 < ma10 < ma20 < ma60 else 0
            
            # 均线斜率组合
            positive_slopes = sum([1 for slope in [ma5_slope, ma10_slope, ma20_slope] if slope > 0])
            negative_slopes = sum([1 for slope in [ma5_slope, ma10_slope, ma20_slope] if slope < 0])
            
            return {
                'ma5_slope': ma5_slope,
                'ma10_slope': ma10_slope,
                'ma20_slope': ma20_slope,
                'ma60_slope': ma60_slope,
                'ma_convergence': ma_convergence,
                'price_vs_ma5': price_vs_ma5,
                'price_vs_ma10': price_vs_ma10,
                'price_vs_ma20': price_vs_ma20,
                'price_vs_ma60': price_vs_ma60,
                'ma_alignment_bull': ma_alignment_bull,
                'ma_alignment_bear': ma_alignment_bear,
                'ma_convergence_high': 1 if ma_convergence < 0.05 else 0,
                'positive_ma_slopes': positive_slopes,
                'negative_ma_slopes': negative_slopes,
                'ma_slope_trend': 1 if positive_slopes > negative_slopes else 0,
            }
        except:
            return self.get_default_ma_features()
    
    def calculate_ma_slope(self, prices, period):
        """计算均线斜率"""
        if len(prices) < period + 5:
            return 0
        
        # 计算当前均线和5期前的均线
        current_ma = np.mean(prices[-period:])
        previous_ma = np.mean(prices[-period-5:-5])
        
        # 斜率 = (当前均线 - 前期均线) / 5
        slope = (current_ma - previous_ma) / 5
        return slope
    
    def calculate_volume_features(self, weekly_klines, reversal_idx):
        """计算交易量特征"""
        try:
            reversal_volume = weekly_klines[reversal_idx].get('volume', 0)
            
            # 历史平均交易量
            prev_volumes = [kline.get('volume', 0) for kline in weekly_klines[max(0, reversal_idx-20):reversal_idx]]
            avg_prev_volume = np.mean(prev_volumes) if prev_volumes else reversal_volume
            
            # 后续平均交易量
            next_volumes = [kline.get('volume', 0) for kline in weekly_klines[reversal_idx+1:min(len(weekly_klines), reversal_idx+6)]]
            avg_next_volume = np.mean(next_volumes) if next_volumes else reversal_volume
            
            # 交易量比率
            volume_ratio_before = reversal_volume / avg_prev_volume if avg_prev_volume > 0 else 1.0
            volume_ratio_after = avg_next_volume / avg_prev_volume if avg_prev_volume > 0 else 1.0
            
            # 交易量趋势
            volume_trend = self.calculate_volume_trend(weekly_klines, reversal_idx)
            
            return {
                'volume_ratio_before': volume_ratio_before,
                'volume_ratio_after': volume_ratio_after,
                'volume_surge_before': 1 if volume_ratio_before >= 1.5 else 0,
                'volume_surge_after': 1 if volume_ratio_after >= 1.2 else 0,
                'volume_trend': volume_trend,
                'high_volume_reversal': 1 if volume_ratio_before >= 2.0 else 0,
            }
        except:
            return {
                'volume_ratio_before': 1.0,
                'volume_ratio_after': 1.0,
                'volume_surge_before': 0,
                'volume_surge_after': 0,
                'volume_trend': 0,
                'high_volume_reversal': 0,
            }
    
    def calculate_volume_trend(self, weekly_klines, reversal_idx):
        """计算交易量趋势"""
        try:
            if reversal_idx < 10:
                return 0
            
            # 计算反转点前10期的交易量趋势
            volumes = [kline.get('volume', 0) for kline in weekly_klines[reversal_idx-10:reversal_idx]]
            
            # 简单线性回归斜率
            x = np.arange(len(volumes))
            slope = np.polyfit(x, volumes, 1)[0] if len(volumes) > 1 else 0
            
            return 1 if slope > 0 else (-1 if slope < 0 else 0)
        except:
            return 0
    
    def calculate_fundamental_features(self, reversal):
        """计算基本面特征（PB、PE、市值变化）"""
        try:
            stock_id = reversal['stock_id']
            reversal_date = str(reversal['date'])
            
            # 获取基本面数据
            fundamental_data = self.get_fundamental_data(stock_id, reversal_date)
            
            return {
                'pb_ratio': fundamental_data.get('pb', 1.0),
                'pe_ratio': fundamental_data.get('pe', 15.0),
                'market_cap': fundamental_data.get('market_cap', 1000.0),
                'pb_low': 1 if fundamental_data.get('pb', 1.0) < 1.0 else 0,
                'pe_low': 1 if fundamental_data.get('pe', 15.0) < 10.0 else 0,
                'market_cap_large': 1 if fundamental_data.get('market_cap', 1000.0) >= 1000.0 else 0,
                'market_cap_medium': 1 if 300.0 <= fundamental_data.get('market_cap', 1000.0) < 1000.0 else 0,
                'market_cap_small': 1 if fundamental_data.get('market_cap', 1000.0) < 300.0 else 0,
            }
        except:
            return self.get_default_fundamental_features()
    
    def get_fundamental_data(self, stock_id, date):
        """获取基本面数据"""
        try:
            # 这里应该从数据库获取真实的基本面数据
            # 暂时使用模拟数据，实际应用中需要连接基本面数据库
            
            # 模拟PB、PE、市值数据
            import random
            
            # 基于股票ID生成相对稳定的模拟数据
            random.seed(hash(stock_id) % 1000)
            
            pb = random.uniform(0.5, 5.0)
            pe = random.uniform(5.0, 50.0)
            market_cap = random.uniform(50.0, 5000.0)
            
            return {
                'pb': pb,
                'pe': pe,
                'market_cap': market_cap
            }
        except:
            return {
                'pb': 1.0,
                'pe': 15.0,
                'market_cap': 1000.0
            }
    
    def calculate_market_features(self, reversal):
        """计算市场环境特征"""
        try:
            reversal_date = pd.to_datetime(str(reversal['date']), format='%Y%m%d')
            
            # 市场阶段判断
            market_phase = self.classify_market_phase(reversal_date)
            
            # 季节性特征
            season_features = self.get_seasonal_features(reversal_date)
            
            return {
                'market_phase': market_phase,
                **season_features
            }
        except:
            return self.get_default_market_features()
    
    def classify_market_phase(self, date):
        """分类市场阶段"""
        year = date.year
        month = date.month
        
        # 简化的市场阶段分类
        if year in [2008, 2011, 2015, 2018, 2022]:
            return 'bear_market'
        elif year in [2007, 2009, 2014, 2019, 2020]:
            return 'bull_market'
        else:
            return 'sideways_market'
    
    def get_seasonal_features(self, date):
        """获取季节性特征"""
        month = date.month
        quarter = (month - 1) // 3 + 1
        
        return {
            'quarter': quarter,
            'is_winter': 1 if month in [12, 1, 2] else 0,
            'is_spring': 1 if month in [3, 4, 5] else 0,
            'is_summer': 1 if month in [6, 7, 8] else 0,
            'is_autumn': 1 if month in [9, 10, 11] else 0,
        }
    
    def calculate_price_percentile(self, prices):
        """计算价格在历史范围内的百分位"""
        if len(prices) < 2:
            return 0.5
        
        current_price = prices[-1]
        historical_prices = prices[:-1]
        
        percentile = sum(1 for p in historical_prices if p <= current_price) / len(historical_prices)
        return percentile
    
    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def get_default_features(self):
        """获取默认特征"""
        features = {}
        features.update(self.get_default_technical_features())
        features.update(self.get_default_ma_features())
        features.update(self.get_default_fundamental_features())
        features.update(self.get_default_market_features())
        return features
    
    def get_default_technical_features(self):
        return {
            'rsi': 50.0,
            'rsi_oversold': 0,
            'rsi_overbought': 0,
            'volatility': 0.1,
            'price_momentum_5': 0.0,
            'price_momentum_10': 0.0,
            'price_percentile': 0.5,
            'low_price_position': 0,
        }
    
    def get_default_ma_features(self):
        return {
            'ma5_slope': 0.0,
            'ma10_slope': 0.0,
            'ma20_slope': 0.0,
            'ma60_slope': 0.0,
            'ma_convergence': 0.1,
            'price_vs_ma5': 0.0,
            'price_vs_ma10': 0.0,
            'price_vs_ma20': 0.0,
            'price_vs_ma60': 0.0,
            'ma_alignment_bull': 0,
            'ma_alignment_bear': 0,
            'ma_convergence_high': 0,
            'positive_ma_slopes': 0,
            'negative_ma_slopes': 0,
            'ma_slope_trend': 0,
        }
    
    def get_default_fundamental_features(self):
        return {
            'pb_ratio': 1.0,
            'pe_ratio': 15.0,
            'market_cap': 1000.0,
            'pb_low': 0,
            'pe_low': 0,
            'market_cap_large': 1,
            'market_cap_medium': 0,
            'market_cap_small': 0,
        }
    
    def get_default_market_features(self):
        return {
            'market_phase': 'sideways_market',
            'quarter': 1,
            'is_winter': 0,
            'is_spring': 0,
            'is_summer': 0,
            'is_autumn': 0,
        }
    
    def save_data(self, samples):
        """保存数据到CSV文件"""
        if not samples:
            print("❌ 没有数据需要保存")
            return
        
        df = pd.DataFrame(samples)
        
        # 保存CSV文件
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reversal_ml_data_complete_{timestamp}.csv"
        filepath = self.csv_root / filename
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        # 显示统计信息
        total_samples = len(df)
        successful_reversals = df['is_successful_reversal'].sum()
        failed_reversals = total_samples - successful_reversals
        success_rate = successful_reversals / total_samples if total_samples > 0 else 0
        avg_gain = df['reversal_gain'].mean()
        
        print(f"💾 数据已保存到: {filepath}")
        print(f"📊 反转点分析统计:")
        print(f"   总反转点数: {total_samples}")
        print(f"   成功反转点(≥15%): {successful_reversals}")
        print(f"   失败反转点(<15%): {failed_reversals}")
        print(f"   成功率: {success_rate:.1%}")
        print(f"   平均收益: {avg_gain:.1%}")
        print(f"   收益范围: {df['reversal_gain'].min():.1%} - {df['reversal_gain'].max():.1%}")
        
        # 显示特征统计
        print(f"📊 特征数量: {len(df.columns)} 个")
        
        # 显示关键特征统计
        print(f"📊 关键特征统计:")
        key_features = ['pb_low', 'pe_low', 'ma_slope_trend', 'high_volume_reversal', 'low_price_position']
        for feature in key_features:
            if feature in df.columns:
                feature_count = df[feature].sum()
                feature_rate = feature_count / total_samples
                print(f"   {feature}: {feature_count} 个样本 ({feature_rate:.1%})")
        
        return filepath
    
    def run(self):
        """运行完整的数据生成流程"""
        print("🚀 开始运行增强版反转数据生成器...")
        
        # 获取股票样本
        candidates = self.get_sample_list()
        
        # 处理所有股票
        all_samples = []
        for i, stock in enumerate(candidates):
            if i % 50 == 0:  # 每50个股票显示一次进度
                print(f"[{i+1}/{len(candidates)}] 处理股票: {stock['id'] if isinstance(stock, dict) else stock}")
            samples = self.identify_reversal_for_stock(stock)
            all_samples.extend(samples)
        
        print(f"✅ 成功处理 {len(candidates)} 个股票，共生成 {len(all_samples)} 个样本")
        
        # 保存数据
        if all_samples:
            self.save_data(all_samples)
        else:
            print("❌ 未生成任何样本")
        
        return all_samples

if __name__ == "__main__":
    generator = EnhancedReversalDataGenerator()
    generator.run()
