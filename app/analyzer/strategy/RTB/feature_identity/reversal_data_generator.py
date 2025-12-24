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

from app.data_manager.data_manager import DataManager
from app.analyzer.strategy.RTB.settings import settings
from app.analyzer.strategy.RTB.feature_identity.reversal_identify import identify_major_reversals

logger = logging.getLogger(__name__)

class ReversalDataGenerator:
    def __init__(self):
        self.data_mgr = DataManager(is_verbose=False)
        self.positive_reversals = []
        self.negative_reversals = []
        self.csv_root = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/ml/data/"
        
        # 确保目录存在
        os.makedirs(self.csv_root, exist_ok=True)

    def get_sample_list(self):
        """获取股票样本列表 - 使用RTB策略的抽样方式"""
        try:
            # 直接使用RTB settings中的配置
            from app.analyzer.strategy.RTB.settings import settings
            
            # 获取所有股票
            all_stocks = self.data_mgr.load_stock_list(filtered=True)
            
            # 使用RTB的抽样数量
            sample_count = settings.get('mode', {}).get('test_amount', 500)
            
            # 随机抽样
            if len(all_stocks) > sample_count:
                candidates = np.random.choice(all_stocks, sample_count, replace=False).tolist()
            else:
                candidates = all_stocks
            
            print(f"✅ 获取到 {len(candidates)} 个股票样本")
            return candidates
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            # 备用方案：使用主要股票
            return [
                {"id": "000001.SZ"}, {"id": "000002.SZ"}, {"id": "000858.SZ"}, 
                {"id": "600036.SH"}, {"id": "600519.SH"}, {"id": "600887.SH"}
            ]

    def identify_reversal_for_stocks(self):
        """为所有股票识别反转点"""
        # print("🎯 开始识别所有股票的反转点...")
        
        candidates = self.get_sample_list()
        all_samples = []
        success_count = 0
        
        for i, stock in enumerate(candidates, 1):
            stock_id = stock['id'] if isinstance(stock, dict) else stock
            
            # 每处理10个股票显示一次进度
            if i % 10 == 0 or i == 1:
                print(f"[{i}/{len(candidates)}] 处理股票: {stock_id}")
            
            try:
                samples = self.identify_reversal_for_stock(stock)
                if samples:
                    all_samples.extend(samples)
                    success_count += 1
                
            except Exception as e:
                if i % 50 == 0:  # 每50个股票显示一次错误
                    print(f"处理 {stock_id} 失败: {e}")
                continue

        print(f"✅ 成功处理 {success_count}/{len(candidates)} 个股票")
        
        # 保存数据
        if all_samples:
            self.save_data(all_samples)
        else:
            print("❌ 未生成任何样本")

    def identify_reversal_for_stock(self, stock):
        """为单个股票识别反转点并生成样本"""
        try:
            # 提取股票ID
            if isinstance(stock, dict):
                stock_id = stock['id']
            else:
                stock_id = stock
            
            # 使用reversal_identify识别重大反转点
            major_reversals = identify_major_reversals(stock_id)
            
            if not major_reversals:
                return []
            
            # 获取周线数据用于生成更多样本
            weekly_klines = self.data_mgr.load_klines(stock_id, term='weekly', adjust='qfq', as_dataframe=False)
            
            if len(weekly_klines) < 100:
                return []
            
            # 生成基于真实反转点的样本
            samples = self.generate_samples_from_reversals(stock_id, major_reversals, weekly_klines)
            
            return samples
            
        except Exception as e:
            # 静默处理错误，避免过多日志
            return []

    def generate_samples_from_reversals(self, stock_id, major_reversals, weekly_klines):
        """基于重大反转点生成训练样本"""
        samples = []
        
        # 只使用真实反转点，按照收益分类成功/失败
        for reversal in major_reversals:
            # 添加stock_id到reversal对象中
            reversal['stock_id'] = stock_id
            # 计算技术指标和特征
            features = self.calculate_reversal_features(reversal, weekly_klines)
            
            # 按照15%阈值分类成功/失败
            is_successful = 1 if reversal['reversal_gain'] >= 0.15 else 0
            
            # 创建样本
            sample = {
                'stock_id': stock_id,
                'date': str(reversal['date']),
                'price': reversal['price'],
                'reversal_gain': reversal['reversal_gain'],
                'reversal_duration': reversal['reversal_duration'],
                'is_successful_reversal': is_successful,  # 1=大收益(≥15%), 0=小收益(<15%)
                'monthly_valley_date': reversal['monthly_valley_date'],
                'monthly_drop_rate': reversal['monthly_drop_rate'],
                'reversal_score': reversal['score'],
                **features
            }
            
            samples.append(sample)
        
        return samples

    def generate_variants_from_reversal(self, stock_id, reversal):
        """为单个反转点生成变体样本"""
        variants = []
        
        for i in range(15):  # 每个反转点生成15个变体
            # 模拟时间变化
            date_offset = np.random.randint(-3, 4)  # 前后3周
            # 正确处理日期格式
            reversal_date_str = str(reversal['date'])
            try:
                reversal_date_obj = pd.to_datetime(reversal_date_str, format='%Y%m%d')
                simulated_date_obj = reversal_date_obj + pd.Timedelta(weeks=date_offset)
                simulated_date = int(simulated_date_obj.strftime('%Y%m%d'))
            except ValueError:
                simulated_date = int(reversal_date_str)  # 如果解析失败，使用原始日期
            
            # 模拟价格变化
            price_variation = np.random.uniform(0.95, 1.05)  # ±5%
            simulated_price = reversal['price'] * price_variation
            
            # 模拟收益变化
            gain_variation = np.random.uniform(0.8, 1.2)  # ±20%
            simulated_gain = reversal['reversal_gain'] * gain_variation
            
            # 计算技术指标
            indicators = self.calculate_technical_indicators(simulated_price, reversal)
            
            # 创建样本
            sample = {
                'stock_id': stock_id,
                'date': str(simulated_date),
                'price': simulated_price,
                'target_reversal_gain': simulated_gain,
                'target_duration': reversal['reversal_duration'],
                'monthly_valley_date': reversal['monthly_valley_date'],
                'monthly_drop_rate': reversal['monthly_drop_rate'],
                'score': reversal['score'],
                'is_reversal': 1 if simulated_gain >= 0.15 else 0,
                **indicators
            }
            
            variants.append(sample)
        
        return variants

    def generate_historical_samples(self, stock_id, weekly_klines, num_samples):
        """基于历史数据生成样本"""
        samples = []
        
        for i in range(min(num_samples, len(weekly_klines) - 40)):
            idx = np.random.randint(20, len(weekly_klines) - 20)
            
            current_price = float(weekly_klines[idx]['close'])
            current_date = weekly_klines[idx]['date']
            
            # 计算未来收益
            future_weeks = min(20, len(weekly_klines) - idx - 1)
            if future_weeks <= 0:
                continue
            
            future_data = weekly_klines[idx+1:idx+1+future_weeks]
            future_highs = []
            for k in future_data:
                if 'highest' in k:
                    future_highs.append(float(k['highest']))
                else:
                    future_highs.append(float(k['close']))
            
            max_future_price = max(future_highs)
            reversal_gain = (max_future_price - current_price) / current_price
            
            # 计算技术指标
            indicators = self.calculate_technical_indicators(current_price, {})
            
            sample = {
                'stock_id': stock_id,
                'date': current_date,
                'price': current_price,
                'target_reversal_gain': reversal_gain,
                'target_duration': future_weeks,
                'monthly_valley_date': '',
                'monthly_drop_rate': np.random.uniform(0, 0.3),
                'score': np.random.uniform(40, 80),
                'is_reversal': 1 if reversal_gain >= 0.15 else 0,
                **indicators
            }
            
            samples.append(sample)
        
        return samples

    def calculate_reversal_features(self, reversal, weekly_klines):
        """计算反转点特征 - 包含RTB核心参数"""
        
        # 解析日期
        try:
            reversal_date = pd.to_datetime(str(reversal['date']), format='%Y%m%d')
        except:
            reversal_date = pd.Timestamp.now()
        
        # 计算RTB核心特征
        rtb_features = self.calculate_rtb_core_features(reversal, weekly_klines)
        
        # 基础反转特征
        features = {
            # 价格相关特征
            'price_level': reversal['price'],
            'price_position_in_range': self.calculate_price_position(reversal, weekly_klines),
            
            # 跌幅相关特征
            'monthly_drop_rate': reversal.get('monthly_drop_rate', 0),
            'major_drop': 1 if reversal.get('monthly_drop_rate', 0) >= 0.30 else 0,
            'extreme_drop': 1 if reversal.get('monthly_drop_rate', 0) >= 0.50 else 0,
            
            # 反转质量特征
            'reversal_score': reversal.get('score', 0),
            'high_score': 1 if reversal.get('score', 0) >= 70 else 0,
            
            # 时间特征
            'year': reversal_date.year,
            'month': reversal_date.month,
            'quarter': (reversal_date.month - 1) // 3 + 1,
            'is_winter': 1 if reversal_date.month in [12, 1, 2] else 0,  # 冬季效应
            'is_spring': 1 if reversal_date.month in [3, 4, 5] else 0,   # 春季效应
            
            # 市场环境特征
            'market_phase': self.classify_market_phase(reversal_date),
            
            # RTB核心特征
            **rtb_features
        }
        
        return features
    
    def calculate_price_position(self, reversal, weekly_klines):
        """计算价格在历史范围内的位置"""
        try:
            reversal_date = pd.to_datetime(str(reversal['date']), format='%Y%m%d')
            # 简化计算：假设在低位
            return np.random.uniform(0.05, 0.25)  # 反转点通常在历史低位的5%-25%
        except:
            return 0.15
    
    def classify_market_phase(self, date):
        """分类市场阶段"""
        year = date.year
        if year in [2008, 2015, 2018, 2022]:
            return 'bear_market'  # 熊市
        elif year in [2009, 2014, 2019, 2020, 2021]:
            return 'bull_market'  # 牛市
        else:
            return 'sideways'  # 震荡市
    
    def estimate_rsi_level(self, reversal):
        """估算RSI水平"""
        # 基于跌幅估算RSI
        drop_rate = reversal.get('monthly_drop_rate', 0)
        if drop_rate >= 0.50:
            return 'oversold'  # 超卖
        elif drop_rate >= 0.30:
            return 'weak'      # 弱势
        else:
            return 'normal'    # 正常
    
    def estimate_volume_surge(self, reversal):
        """估算成交量放大"""
        # 基于反转质量估算成交量
        score = reversal.get('score', 0)
        if score >= 70:
            return 'high'      # 高成交量
        elif score >= 50:
            return 'medium'    # 中等成交量
        else:
            return 'low'       # 低成交量
    
    def calculate_rtb_core_features(self, reversal, weekly_klines):
        """计算RTB核心特征"""
        features = {}
        
        try:
            # 找到反转点在周线数据中的位置
            reversal_date = pd.to_datetime(str(reversal['date']), format='%Y%m%d')
            reversal_idx = None
            
            for i, kline in enumerate(weekly_klines):
                kline_date = pd.to_datetime(str(kline['date']), format='%Y%m%d')
                if abs((kline_date - reversal_date).days) <= 7:  # 一周内
                    reversal_idx = i
                    break
            
            if reversal_idx is not None and reversal_idx >= 20:  # 确保有足够的历史数据
                print(f"🔍 找到反转点索引: {reversal_idx}, 周线数据长度: {len(weekly_klines)}")
                # 1. 交易量变化特征
                volume_features = self.calculate_volume_features(weekly_klines, reversal_idx)
                features.update(volume_features)
                
                # 2. 成交额变化特征
                turnover_features = self.calculate_turnover_features(weekly_klines, reversal_idx)
                features.update(turnover_features)
                
                # 3. 均线特征
                ma_features = self.calculate_ma_features(weekly_klines, reversal_idx)
                features.update(ma_features)
                
                # 4. 市值特征（需要从数据库获取）
                stock_id = reversal.get('stock_id', '000001.SZ')  # 使用默认值
                market_cap_features = self.calculate_market_cap_features(stock_id, reversal_date)
                features.update(market_cap_features)
                
                # 5. 技术指标特征
                technical_features = self.calculate_technical_features(weekly_klines, reversal_idx)
                features.update(technical_features)
                
            else:
                # 如果数据不足，使用默认值
                features = self.get_default_rtb_features()
                
        except Exception as e:
            # 出错时使用默认值
            print(f"⚠️ RTB特征计算出错: {e}")
            features = self.get_default_rtb_features()
        
        return features
    
    def calculate_volume_features(self, weekly_klines, reversal_idx):
        """计算交易量相关特征"""
        try:
            # 反转点前后的交易量
            reversal_volume = weekly_klines[reversal_idx].get('volume', 0)
            
            # 计算历史平均交易量（反转点前20周）
            prev_volumes = [kline.get('volume', 0) for kline in weekly_klines[max(0, reversal_idx-20):reversal_idx]]
            avg_prev_volume = np.mean(prev_volumes) if prev_volumes else reversal_volume
            
            # 计算后续平均交易量（反转点后5周）
            next_volumes = [kline.get('volume', 0) for kline in weekly_klines[reversal_idx+1:min(len(weekly_klines), reversal_idx+6)]]
            avg_next_volume = np.mean(next_volumes) if next_volumes else reversal_volume
            
            # 交易量比率
            volume_ratio_before = reversal_volume / avg_prev_volume if avg_prev_volume > 0 else 1.0
            volume_ratio_after = avg_next_volume / avg_prev_volume if avg_prev_volume > 0 else 1.0
            volume_change_ratio = avg_next_volume / reversal_volume if reversal_volume > 0 else 1.0
            
            return {
                'volume_ratio_before': volume_ratio_before,
                'volume_ratio_after': volume_ratio_after,
                'volume_change_ratio': volume_change_ratio,
                'volume_surge_before': 1 if volume_ratio_before >= 1.5 else 0,
                'volume_surge_after': 1 if volume_ratio_after >= 1.2 else 0,
            }
        except:
            return self.get_default_volume_features()
    
    def calculate_turnover_features(self, weekly_klines, reversal_idx):
        """计算成交额相关特征"""
        try:
            # 反转点前后的成交额
            reversal_turnover = weekly_klines[reversal_idx].get('turnover', 0)
            
            # 计算历史平均成交额
            prev_turnovers = [kline.get('turnover', 0) for kline in weekly_klines[max(0, reversal_idx-20):reversal_idx]]
            avg_prev_turnover = np.mean(prev_turnovers) if prev_turnovers else reversal_turnover
            
            # 计算后续平均成交额
            next_turnovers = [kline.get('turnover', 0) for kline in weekly_klines[reversal_idx+1:min(len(weekly_klines), reversal_idx+6)]]
            avg_next_turnover = np.mean(next_turnovers) if next_turnovers else reversal_turnover
            
            # 成交额比率
            turnover_ratio_before = reversal_turnover / avg_prev_turnover if avg_prev_turnover > 0 else 1.0
            turnover_ratio_after = avg_next_turnover / avg_prev_turnover if avg_prev_turnover > 0 else 1.0
            
            return {
                'turnover_ratio_before': turnover_ratio_before,
                'turnover_ratio_after': turnover_ratio_after,
                'turnover_surge_before': 1 if turnover_ratio_before >= 1.5 else 0,
                'turnover_surge_after': 1 if turnover_ratio_after >= 1.2 else 0,
            }
        except:
            return self.get_default_turnover_features()
    
    def calculate_ma_features(self, weekly_klines, reversal_idx):
        """计算均线相关特征"""
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
            
            # 均线斜率（使用前5周数据计算）
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
            ma_alignment = 1 if ma5 > ma10 > ma20 else 0  # 多头排列
            ma_alignment_bear = 1 if ma5 < ma10 < ma20 else 0  # 空头排列
            
            return {
                'ma5_slope': ma5_slope,
                'ma10_slope': ma10_slope,
                'ma20_slope': ma20_slope,
                'ma_convergence': ma_convergence,
                'price_vs_ma5': price_vs_ma5,
                'price_vs_ma10': price_vs_ma10,
                'price_vs_ma20': price_vs_ma20,
                'ma_alignment_bull': ma_alignment,
                'ma_alignment_bear': ma_alignment_bear,
                'ma_convergence_high': 1 if ma_convergence < 0.05 else 0,
            }
        except:
            return self.get_default_ma_features()
    
    def calculate_market_cap_features(self, stock_id, reversal_date):
        """计算市值相关特征"""
        try:
            # 这里需要从数据库获取市值数据
            # 暂时使用模拟数据
            import random
            
            # 模拟市值分类
            market_cap = random.uniform(50, 5000)  # 50亿到5000亿
            
            return {
                'market_cap': market_cap,
                'market_cap_large': 1 if market_cap >= 1000 else 0,  # 大盘股
                'market_cap_medium': 1 if 300 <= market_cap < 1000 else 0,  # 中盘股
                'market_cap_small': 1 if market_cap < 300 else 0,  # 小盘股
            }
        except:
            return self.get_default_market_cap_features()
    
    def calculate_technical_features(self, weekly_klines, reversal_idx):
        """计算技术指标特征"""
        try:
            # 获取价格数据
            prices = [kline.get('close', 0) for kline in weekly_klines[max(0, reversal_idx-20):reversal_idx+1]]
            volumes = [kline.get('volume', 0) for kline in weekly_klines[max(0, reversal_idx-20):reversal_idx+1]]
            
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
            
            # 成交量动量
            volume_momentum = (volumes[-1] - np.mean(volumes[-6:-1])) / np.mean(volumes[-6:-1]) if len(volumes) >= 6 else 0
            
            return {
                'rsi': rsi,
                'rsi_oversold': 1 if rsi < 30 else 0,
                'rsi_overbought': 1 if rsi > 70 else 0,
                'volatility': volatility,
                'price_momentum_5': price_momentum_5,
                'price_momentum_10': price_momentum_10,
                'volume_momentum': volume_momentum,
            }
        except:
            return self.get_default_technical_features()
    
    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50  # 默认值
        
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
    
    def get_default_rtb_features(self):
        """获取RTB特征的默认值"""
        features = {}
        features.update(self.get_default_volume_features())
        features.update(self.get_default_turnover_features())
        features.update(self.get_default_ma_features())
        features.update(self.get_default_market_cap_features())
        features.update(self.get_default_technical_features())
        return features
    
    def get_default_volume_features(self):
        return {
            'volume_ratio_before': 1.0,
            'volume_ratio_after': 1.0,
            'volume_change_ratio': 1.0,
            'volume_surge_before': 0,
            'volume_surge_after': 0,
        }
    
    def get_default_turnover_features(self):
        return {
            'turnover_ratio_before': 1.0,
            'turnover_ratio_after': 1.0,
            'turnover_surge_before': 0,
            'turnover_surge_after': 0,
        }
    
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
    
    def get_default_market_cap_features(self):
        return {
            'market_cap': 1000.0,
            'market_cap_large': 1,
            'market_cap_medium': 0,
            'market_cap_small': 0,
        }
    
    def get_default_technical_features(self):
        return {
            'rsi': 50.0,
            'rsi_oversold': 0,
            'rsi_overbought': 0,
            'volatility': 0.1,
            'price_momentum_5': 0.0,
            'price_momentum_10': 0.0,
            'volume_momentum': 0.0,
        }

    def reversal_to_csv(self, samples):
        """将反转数据转换为CSV格式"""
        if not samples:
            return pd.DataFrame()
        
        df = pd.DataFrame(samples)
        
        # 确保列的顺序
        feature_cols = [col for col in df.columns if col not in ['stock_id', 'date', 'price', 'reversal_gain', 'reversal_duration', 'is_successful_reversal']]
        column_order = ['stock_id', 'date', 'price', 'reversal_gain', 'reversal_duration', 'is_successful_reversal'] + feature_cols
        
        df = df[column_order]
        return df

    def save_data(self, samples):
        """保存数据到CSV文件"""
        if not samples:
            logger.error("❌ 没有数据需要保存")
            return
        
        # 转换为DataFrame
        df = self.reversal_to_csv(samples)
        
        if df.empty:
            logger.error("❌ DataFrame为空")
            return
        
        # 保存CSV文件
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reversal_ml_data_{timestamp}.csv"
        filepath = os.path.join(self.csv_root, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        # 显示统计信息 - 专注于反转成功/失败分析
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
        
        # 显示成功vs失败的特征对比
        if successful_reversals > 0 and failed_reversals > 0:
            successful_avg_drop = df[df['is_successful_reversal'] == 1]['monthly_drop_rate'].mean()
            failed_avg_drop = df[df['is_successful_reversal'] == 0]['monthly_drop_rate'].mean()
            successful_avg_score = df[df['is_successful_reversal'] == 1]['reversal_score'].mean()
            failed_avg_score = df[df['is_successful_reversal'] == 0]['reversal_score'].mean()
            
            print(f"📈 成功vs失败特征对比:")
            print(f"   成功反转平均跌幅: {successful_avg_drop:.1%}")
            print(f"   失败反转平均跌幅: {failed_avg_drop:.1%}")
            print(f"   成功反转平均分数: {successful_avg_score:.1f}")
            print(f"   失败反转平均分数: {failed_avg_score:.1f}")
        
        # 显示前几个股票的统计
        print("📊 前5个股票统计:")
        for i, stock_id in enumerate(df['stock_id'].unique()[:5]):
            stock_data = df[df['stock_id'] == stock_id]
            total_samples = len(stock_data)
            successful_samples = stock_data['is_successful_reversal'].sum()
            avg_gain = stock_data['reversal_gain'].mean()
            print(f"   {stock_id}: {total_samples} 反转点, {successful_samples} 成功, 平均收益 {avg_gain:.1%}")
        
        if len(df['stock_id'].unique()) > 5:
            print(f"   ... 还有 {len(df['stock_id'].unique()) - 5} 个股票")
        
        return filepath

    def run(self):
        """运行完整的数据生成流程"""
        print("🚀 开始运行反转数据生成器...")
        self.identify_reversal_for_stocks()
        print("✅ 反转数据生成完成！")