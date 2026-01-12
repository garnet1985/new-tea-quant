#!/usr/bin/env python3
"""
简化版反转数据生成器
专注于RTB核心特征的提取
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

from app.core.modules.data_manager.data_manager import DataManager
from app.core.modules.analyzer.strategy.RTB import settings
from app.core.modules.analyzer.strategy.RTB.feature_identity.reversal_identify import identify_major_reversals

logger = logging.getLogger(__name__)

class SimpleReversalDataGenerator:
    """简化版反转数据生成器"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.data_manager.initialize()
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
            # print(f"🎯 识别 {stock_id} 的反转点...")
            
            # 识别重大反转点
            major_reversals = identify_major_reversals(stock_id)
            
            if not major_reversals:
                print(f"⚠️ {stock_id} 未找到反转点")
                return []
            
            # 加载周线数据
            weekly_klines = self.data_manager.load_klines(stock_id, term='weekly', adjust='qfq', as_dataframe=False)
            
            # 生成样本
            samples = self.generate_samples_from_reversals(stock_id, major_reversals, weekly_klines)
            
            print(f"✅ {stock_id} 生成 {len(samples)} 个样本")
            return samples
            
        except Exception as e:
            print(f"❌ {stock_id} 处理失败: {e}")
            return []
    
    def generate_samples_from_reversals(self, stock_id, major_reversals, weekly_klines):
        """基于重大反转点生成训练样本"""
        samples = []
        
        for reversal in major_reversals:
            # 添加stock_id
            reversal['stock_id'] = stock_id
            
            # 计算RTB核心特征
            features = self.calculate_rtb_features(reversal, weekly_klines)
            
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
    
    def calculate_rtb_features(self, reversal, weekly_klines):
        """计算RTB核心特征"""
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
                # 计算各种特征
                features.update(self.calculate_volume_features(weekly_klines, reversal_idx))
                features.update(self.calculate_ma_features(weekly_klines, reversal_idx))
                features.update(self.calculate_technical_features(weekly_klines, reversal_idx))
                features.update(self.calculate_market_features(reversal))
            else:
                # 使用默认值
                features.update(self.get_default_features())
                
        except Exception as e:
            print(f"⚠️ 特征计算出错: {e}")
            features.update(self.get_default_features())
        
        return features
    
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
            
            return {
                'volume_ratio_before': volume_ratio_before,
                'volume_ratio_after': volume_ratio_after,
                'volume_surge_before': 1 if volume_ratio_before >= 1.5 else 0,
                'volume_surge_after': 1 if volume_ratio_after >= 1.2 else 0,
            }
        except:
            return {
                'volume_ratio_before': 1.0,
                'volume_ratio_after': 1.0,
                'volume_surge_before': 0,
                'volume_surge_after': 0,
            }
    
    def calculate_ma_features(self, weekly_klines, reversal_idx):
        """计算均线特征"""
        try:
            # 获取价格数据
            prices = [kline.get('close', 0) for kline in weekly_klines[max(0, reversal_idx-60):reversal_idx+1]]
            
            if len(prices) < 20:
                return self.get_default_ma_features()
            
            # 计算均线
            ma5 = np.mean(prices[-5:]) if len(prices) >= 5 else prices[-1]
            ma10 = np.mean(prices[-10:]) if len(prices) >= 10 else prices[-1]
            ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else prices[-1]
            
            current_price = prices[-1]
            
            # 均线斜率
            if len(prices) >= 10:
                ma5_slope = (ma5 - np.mean(prices[-10:-5])) / 5 if len(prices) >= 10 else 0
                ma10_slope = (ma10 - np.mean(prices[-15:-10])) / 5 if len(prices) >= 15 else 0
                ma20_slope = (ma20 - np.mean(prices[-25:-20])) / 5 if len(prices) >= 25 else 0
            else:
                ma5_slope = ma10_slope = ma20_slope = 0
            
            # 均线收敛度
            ma_convergence = np.std([ma5, ma10, ma20]) / current_price if current_price > 0 else 0
            
            # 价格相对于均线的位置
            price_vs_ma5 = (current_price - ma5) / ma5 if ma5 > 0 else 0
            price_vs_ma10 = (current_price - ma10) / ma10 if ma10 > 0 else 0
            price_vs_ma20 = (current_price - ma20) / ma20 if ma20 > 0 else 0
            
            # 均线排列
            ma_alignment_bull = 1 if ma5 > ma10 > ma20 else 0
            ma_alignment_bear = 1 if ma5 < ma10 < ma20 else 0
            
            return {
                'ma5_slope': ma5_slope,
                'ma10_slope': ma10_slope,
                'ma20_slope': ma20_slope,
                'ma_convergence': ma_convergence,
                'price_vs_ma5': price_vs_ma5,
                'price_vs_ma10': price_vs_ma10,
                'price_vs_ma20': price_vs_ma20,
                'ma_alignment_bull': ma_alignment_bull,
                'ma_alignment_bear': ma_alignment_bear,
                'ma_convergence_high': 1 if ma_convergence < 0.05 else 0,
            }
        except:
            return self.get_default_ma_features()
    
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
            
            return {
                'rsi': rsi,
                'rsi_oversold': 1 if rsi < 30 else 0,
                'rsi_overbought': 1 if rsi > 70 else 0,
                'volatility': volatility,
                'price_momentum_5': price_momentum_5,
                'price_momentum_10': price_momentum_10,
            }
        except:
            return self.get_default_technical_features()
    
    def calculate_market_features(self, reversal):
        """计算市场特征"""
        # 简化的市值特征（使用随机值）
        import random
        market_cap = random.uniform(50, 5000)
        
        return {
            'market_cap': market_cap,
            'market_cap_large': 1 if market_cap >= 1000 else 0,
            'market_cap_medium': 1 if 300 <= market_cap < 1000 else 0,
            'market_cap_small': 1 if market_cap < 300 else 0,
        }
    
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
        features.update(self.get_default_ma_features())
        features.update(self.get_default_technical_features())
        return features
    
    def get_default_ma_features(self):
        return {
            'ma5_slope': 0.0,
            'ma10_slope': 0.0,
            'ma20_slope': 0.0,
            'ma_convergence': 0.1,
            'price_vs_ma5': 0.0,
            'price_vs_ma10': 0.0,
            'price_vs_ma20': 0.0,
            'ma_alignment_bull': 0,
            'ma_alignment_bear': 0,
            'ma_convergence_high': 0,
        }
    
    def get_default_technical_features(self):
        return {
            'rsi': 50.0,
            'rsi_oversold': 0,
            'rsi_overbought': 0,
            'volatility': 0.1,
            'price_momentum_5': 0.0,
            'price_momentum_10': 0.0,
        }
    
    def save_data(self, samples):
        """保存数据到CSV文件"""
        if not samples:
            print("❌ 没有数据需要保存")
            return
        
        df = pd.DataFrame(samples)
        
        # 保存CSV文件
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reversal_ml_data_enhanced_{timestamp}.csv"
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
        
        # 显示RTB特征统计
        print(f"📊 RTB核心特征统计:")
        rtb_features = ['volume_surge_before', 'volume_surge_after', 'ma_convergence_high', 
                       'ma_alignment_bull', 'rsi_oversold']
        for feature in rtb_features:
            if feature in df.columns:
                feature_count = df[feature].sum()
                feature_rate = feature_count / total_samples
                print(f"   {feature}: {feature_count} 个样本 ({feature_rate:.1%})")
        
        return filepath
    
    def run(self):
        """运行完整的数据生成流程"""
        print("🚀 开始运行简化版反转数据生成器...")
        
        # 获取股票样本
        candidates = self.get_sample_list()
        
        # 处理所有股票
        all_samples = []
        for i, stock in enumerate(candidates):
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
    generator = SimpleReversalDataGenerator()
    generator.run()