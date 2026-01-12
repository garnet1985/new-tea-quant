#!/usr/bin/env python3
"""
ReverseTrendBet 策略 - ML增强版本
基于机器学习验证的重要参数重新定义阈值

V21.0 ML增强版本：
基于7407个反转点样本的机器学习分析结果，重新定义关键参数阈值：
1. 波动率 (volatility): 重要性 0.106 - 最高权重
2. 反转后成交量放大 (volume_ratio_after): 重要性 0.080 - 第二重要
3. 均线收敛度 (ma_convergence): 重要性 0.056 - 中高权重
4. 价格相对均线位置: 重要性 0.053-0.045 - 中等权重
5. 成交量放大倍数: ≥1.5倍为有效信号
6. 小盘股偏好: 成功率89.1% > 大盘股86.6%
"""
import math
import numpy as np
from typing import Dict, List, Any, Optional
from loguru import logger

from app.core.modules.analyzer.strategy.RTB.settings import settings
from app.core.modules.analyzer.analyzer_service import AnalyzerService
from app.core.utils.icon.icon_service import IconService
from ...components.base_strategy import BaseStrategy
from ...components.entity.opportunity import Opportunity

class ReverseTrendBet(BaseStrategy):
    """ReverseTrendBet ML增强版本策略实现"""
    
    def __init__(self, db=None, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="ReverseTrendBet",
            key="RTB",
            version="1.0.0"
        )
        if db is not None:
            super().initialize()

    # ========================================================
    # Core logic:
    # ========================================================

    @staticmethod
    def scan_opportunity(stock: Dict[str, Any], data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描单只股票的投资机会 - RTB V21.0 ML增强版本
        
        基于7407个反转点样本的机器学习分析结果：
        
        核心参数权重（按重要性排序）：
        1. 波动率 (volatility): 0.106 - 最高权重
        2. 反转后成交量放大 (volume_ratio_after): 0.080 - 第二重要
        3. 均线收敛度 (ma_convergence): 0.056 - 中高权重
        4. 价格相对MA10位置 (price_vs_ma10): 0.053
        5. 价格相对MA20位置 (price_vs_ma20): 0.046
        6. 10期价格动量 (price_momentum_10): 0.045
        7. 价格相对MA5位置 (price_vs_ma5): 0.045
        8. 价格相对MA60位置 (price_vs_ma60): 0.044
        9. 月线跌幅 (monthly_drop_rate): 0.044
        10. 反转前成交量放大 (volume_ratio_before): 0.042
        
        关键发现：
        - 反转后成交量放大成功率差异 +11.4% (95.1% vs 83.7%)
        - 小盘股成功率89.1% > 中盘股87.2% > 大盘股86.6%
        - MA20正斜率成功率88.0% > 负斜率86.1%

        Returns: Optional[Dict]
        """
        # 切换到周线数据
        weekly_klines = data.get('klines', {}).get('weekly', [])
        
        if len(weekly_klines) < 100:  # 周线需要更少的数据点（约2年）
            return None
            
        record_of_today = weekly_klines[-1]
        today_close = record_of_today.get('close')
        
        if not today_close or today_close <= 0:
            return None

        # 计算ML增强版特征
        features = ReverseTrendBet._calculate_ml_enhanced_features(weekly_klines, stock['id'], None)
        
        if not features:
            return None
        
        # ML增强版财务筛选（优先小盘股）
        financial_indicators = ReverseTrendBet._get_financial_indicators_from_klines(record_of_today)
        if not ReverseTrendBet._check_ml_enhanced_financial_conditions(financial_indicators):
            return None
        
        # 检查ML增强版条件
        if not ReverseTrendBet._check_ml_enhanced_conditions(features):
            return None

        # 构建机会对象
        opportunity = Opportunity(
            stock=stock,
            record_of_today=record_of_today,
            extra_fields={
                'features': features,
                'strategy_version': 'V21.0_ML_Enhanced',
                'financial_indicators': financial_indicators,
                'ml_signal_conditions': {
                    # 最高权重参数
                    'volatility': features['volatility'],
                    'volume_ratio_after': features['volume_ratio_after'],
                    
                    # 中高权重参数
                    'ma_convergence': features['ma_convergence'],
                    'price_vs_ma10': features['price_vs_ma10'],
                    'price_vs_ma20': features['price_vs_ma20'],
                    'price_momentum_10': features['price_momentum_10'],
                    'price_vs_ma5': features['price_vs_ma5'],
                    'price_vs_ma60': features['price_vs_ma60'],
                    'monthly_drop_rate': features['monthly_drop_rate'],
                    'volume_ratio_before': features['volume_ratio_before'],
                    
                    # 均线斜率参数
                    'ma20_slope': features['ma20_slope'],
                    'ma_slope_trend': features['ma_slope_trend'],
                    
                    # 技术指标
                    'rsi': features['rsi'],
                    'price_percentile': features['price_percentile'],
                }
            },
            lower_bound=today_close * 0.98,  # 2%的买入区间
            upper_bound=today_close * 1.02,
        )

        return opportunity

    @staticmethod
    def _calculate_ml_enhanced_features(weekly_klines: List[Dict[str, Any]], stock_id: str = None, db_manager = None) -> Optional[Dict[str, float]]:
        """
        计算ML增强版特征
        基于机器学习验证的重要参数
        """
        try:
            # 提取价格和成交量数据
            closes = [k['close'] for k in weekly_klines if k.get('close')]
            highs = [k['highest'] for k in weekly_klines if k.get('highest')]
            lows = [k['lowest'] for k in weekly_klines if k.get('lowest')]
            volumes = [k['volume'] for k in weekly_klines if k.get('volume', 0)]
            amounts = [k['amount'] for k in weekly_klines if k.get('amount', 0)]
            
            if len(closes) < 100:
                return None
                
            # 转换为numpy数组
            closes = np.array(closes)
            highs = np.array(highs)
            lows = np.array(lows)
            volumes = np.array(volumes)
            amounts = np.array(amounts)
            
            # 获取当前K线的移动平均线和财务指标
            current_kline = weekly_klines[-1]
            ma5_val = current_kline.get('ma5')
            ma10_val = current_kline.get('ma10')
            ma20_val = current_kline.get('ma20')
            ma60_val = current_kline.get('ma60')
            
            if not all([ma5_val, ma10_val, ma20_val, ma60_val]):
                return None
                
            # 获取财务指标
            market_cap = current_kline.get('total_market_value', 0)
            pe_ratio = current_kline.get('pe', 0)
            pb_ratio = current_kline.get('pb', 0)
            ps_ratio = current_kline.get('ps', 0)
            turnover_rate = current_kline.get('turnover_rate', 0)
            
            current_price = closes[-1]
            
            # 1. 波动率计算 (最高权重 0.106)
            if len(closes) >= 20:
                price_changes = np.diff(closes[-20:])  # 20期价格变化
                returns = price_changes / closes[-20:-1]  # 20期收益率
                volatility = np.std(returns) if len(returns) > 1 else 0
            else:
                price_changes = np.diff(closes)  # 所有价格变化
                returns = price_changes / closes[:-1]  # 所有收益率
                volatility = np.std(returns) if len(returns) > 1 else 0
            
            # 2. 成交量放大计算 (第二重要 0.080)
            volume_ratio_after = 1.0
            volume_ratio_before = 1.0
            if len(volumes) >= 10:
                # 反转后成交量放大（未来5期）
                future_volumes = volumes[-5:] if len(volumes) >= 5 else volumes
                prev_volumes = volumes[-10:-5] if len(volumes) >= 10 else volumes[-5:]
                if len(prev_volumes) > 0:
                    avg_prev_volume = np.mean(prev_volumes)
                    avg_future_volume = np.mean(future_volumes)
                    volume_ratio_after = avg_future_volume / avg_prev_volume if avg_prev_volume > 0 else 1.0
                    
                # 反转前成交量放大（前5期）
                current_volume = volumes[-1]
                volume_ratio_before = current_volume / avg_prev_volume if avg_prev_volume > 0 else 1.0
            
            # 3. 均线收敛度计算 (中高权重 0.056)
            ma_values = [ma5_val, ma10_val, ma20_val, ma60_val]
            ma_convergence = np.std(ma_values) / current_price if current_price > 0 else 0
            
            # 4. 价格相对均线位置计算 (中等权重 0.053-0.045)
            price_vs_ma5 = (current_price - ma5_val) / ma5_val if ma5_val > 0 else 0
            price_vs_ma10 = (current_price - ma10_val) / ma10_val if ma10_val > 0 else 0
            price_vs_ma20 = (current_price - ma20_val) / ma20_val if ma20_val > 0 else 0
            price_vs_ma60 = (current_price - ma60_val) / ma60_val if ma60_val > 0 else 0
            
            # 5. 价格动量计算 (中等权重 0.045)
            price_momentum_5 = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
            price_momentum_10 = (closes[-1] - closes[-11]) / closes[-11] if len(closes) >= 11 else 0
            
            # 6. 月线跌幅计算 (中等权重 0.044)
            monthly_drop_rate = 0.0
            if len(closes) >= 60:  # 约15个月的周线数据
                max_price_3m = np.max(closes[-60:])  # 3个月内最高价
                current_price = closes[-1]
                monthly_drop_rate = (max_price_3m - current_price) / max_price_3m if max_price_3m > 0 else 0
            
            # 7. 均线斜率计算
            ma5_slope = ReverseTrendBet._calculate_ma_slope(closes, 5)
            ma10_slope = ReverseTrendBet._calculate_ma_slope(closes, 10)
            ma20_slope = ReverseTrendBet._calculate_ma_slope(closes, 20)
            ma60_slope = ReverseTrendBet._calculate_ma_slope(closes, 60)
            
            # 均线斜率趋势判断
            positive_slopes = sum([1 for slope in [ma5_slope, ma10_slope, ma20_slope] if slope > 0])
            ma_slope_trend = 1 if positive_slopes > 1.5 else 0  # 多数均线为正斜率
            
            # 8. RSI计算
            rsi = ReverseTrendBet._calculate_rsi(closes, 14)
            
            # 9. 价格历史分位数计算
            price_percentile = ReverseTrendBet._calculate_price_percentile(closes)
            
            return {
                # 最高权重参数
                'volatility': volatility,
                'volume_ratio_after': volume_ratio_after,
                
                # 中高权重参数
                'ma_convergence': ma_convergence,
                'price_vs_ma10': price_vs_ma10,
                'price_vs_ma20': price_vs_ma20,
                'price_momentum_10': price_momentum_10,
                'price_vs_ma5': price_vs_ma5,
                'price_vs_ma60': price_vs_ma60,
                'monthly_drop_rate': monthly_drop_rate,
                'volume_ratio_before': volume_ratio_before,
                
                # 均线斜率参数
                'ma5_slope': ma5_slope,
                'ma10_slope': ma10_slope,
                'ma20_slope': ma20_slope,
                'ma60_slope': ma60_slope,
                'ma_slope_trend': ma_slope_trend,
                
                # 技术指标
                'rsi': rsi,
                'price_percentile': price_percentile,
                
                # 财务指标
                'market_cap': market_cap,
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'ps_ratio': ps_ratio,
                'turnover_rate': turnover_rate,
            }
            
        except Exception as e:
            logger.error(f"计算ML增强版特征失败: {e}")
            return None

    @staticmethod
    def _calculate_ma_slope(prices, period):
        """计算均线斜率"""
        if len(prices) < period + 5:
            return 0
        
        # 计算当前均线和5期前的均线
        current_ma = np.mean(prices[-period:])
        previous_ma = np.mean(prices[-period-5:-5])
        
        # 斜率 = (当前均线 - 前期均线) / 5
        slope = (current_ma - previous_ma) / 5
        return slope

    @staticmethod
    def _calculate_rsi(prices, period=14):
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

    @staticmethod
    def _calculate_price_percentile(prices):
        """计算价格在历史范围内的百分位"""
        if len(prices) < 2:
            return 0.5
        
        current_price = prices[-1]
        historical_prices = prices[:-1]
        
        percentile = sum(1 for p in historical_prices if p <= current_price) / len(historical_prices)
        return percentile

    @staticmethod
    def _get_financial_indicators_from_klines(current_kline: Dict[str, Any]) -> Dict[str, float]:
        """从当前K线数据中提取财务指标"""
        try:
            financial_metrics = {
                'market_cap': current_kline.get('total_market_value', 0),
                'pe_ratio': current_kline.get('pe', 0),
                'pb_ratio': current_kline.get('pb', 0),
                'ps_ratio': current_kline.get('ps', 0),
                'turnover_rate': current_kline.get('turnover_rate', 0),
                'volume_ratio_fin': current_kline.get('volume_ratio', 0),
            }
            return financial_metrics
            
        except Exception as e:
            logger.error(f"提取财务指标失败: {e}")
            return {}

    @staticmethod
    def _check_ml_enhanced_financial_conditions(financial_indicators: Dict[str, float]) -> bool:
        """
        检查ML增强版财务指标筛选条件
        优先小盘股：小盘股成功率89.1% > 中盘股87.2% > 大盘股86.6%
        """
        try:
            if not financial_indicators:
                return True
            
            # 从配置读取阈值
            thresholds = settings.get('core', {}).get('thresholds', {})
            
            market_cap = financial_indicators.get('market_cap', 0)
            pe_ratio = financial_indicators.get('pe_ratio', 0)
            pb_ratio = financial_indicators.get('pb_ratio', 0)
            ps_ratio = financial_indicators.get('ps_ratio', 0)
            
            # 从配置获取参数
            market_cap_max = thresholds.get('market_cap', {}).get('preference_max', 3000000)
            pe_min = thresholds.get('pe_ratio', {}).get('preference_min', 10)
            pe_max = thresholds.get('pe_ratio', {}).get('preference_max', 100)
            pb_min = thresholds.get('pb_ratio', {}).get('preference_min', 0.3)
            pb_max = thresholds.get('pb_ratio', {}).get('preference_max', 8.0)
            ps_min = thresholds.get('ps_ratio', {}).get('preference_min', 0.5)
            ps_max = thresholds.get('ps_ratio', {}).get('preference_max', 15.0)
            
            conditions = [
                # 市值筛选：优先小盘股
                market_cap < market_cap_max,
                
                # PE筛选
                (pe_ratio > pe_min and pe_ratio < pe_max),
                
                # PB筛选
                (pb_ratio > pb_min and pb_ratio < pb_max),
                
                # PS筛选
                (ps_ratio > ps_min and ps_ratio < ps_max),
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查ML增强版财务条件时出错: {e}")
            return True  # 出错时默认通过

    @staticmethod
    def _check_ml_enhanced_conditions(features: Dict[str, float]) -> bool:
        """
        检查ML增强版条件 - 优化版本
        基于机器学习分析结果优化参数以提高ROI
        """
        try:
            # 从配置读取阈值
            thresholds = settings.get('core', {}).get('thresholds', {})
            
            # 从配置获取各项参数
            market_cap_cfg = thresholds.get('market_cap', {})
            pe_cfg = thresholds.get('pe_ratio', {})
            pb_cfg = thresholds.get('pb_ratio', {})
            rsi_cfg = thresholds.get('rsi', {})
            price_pct_cfg = thresholds.get('price_percentile', {})
            vol_cfg = thresholds.get('volatility', {})
            vol_before_cfg = thresholds.get('volume_ratio_before', {})
            vol_after_cfg = thresholds.get('volume_ratio_after', {})
            ma_conv_cfg = thresholds.get('ma_convergence', {})
            ma20_cfg = thresholds.get('price_vs_ma20', {})
            ma60_cfg = thresholds.get('price_vs_ma60', {})
            drop_cfg = thresholds.get('monthly_drop_rate', {})
            slope_cfg = thresholds.get('ma20_slope', {})
            
            conditions = [
                # 1. 市值筛选条件 (基于脚本分析优化)
                features['market_cap'] < market_cap_cfg.get('max', 1800000),
                
                # 2. PE比率筛选 (基于脚本分析优化)
                features['pe_ratio'] < pe_cfg.get('max', 120),
                features['pe_ratio'] > pe_cfg.get('min', 2),
                
                # 3. PB比率筛选 (基于脚本分析优化)
                features['pb_ratio'] < pb_cfg.get('max', 7.5),
                features['pb_ratio'] > pb_cfg.get('min', 0.1),
                
                # 4. RSI条件 (基于脚本分析优化)
                features['rsi'] < rsi_cfg.get('max', 92),
                features['rsi'] > rsi_cfg.get('min', 7),
                
                # 5. 价格历史分位数 (基于脚本分析优化)
                features['price_percentile'] < price_pct_cfg.get('max', 0.95),
                features['price_percentile'] > price_pct_cfg.get('min', 0.00),
                
                # 6. 波动率条件 (基于脚本分析优化)
                features['volatility'] > vol_cfg.get('min', 0.007),
                features['volatility'] < vol_cfg.get('max', 0.450),
                
                # 7. 成交量条件 (基于脚本分析优化)
                features['volume_ratio_before'] >= vol_before_cfg.get('min', 0.7),
                features['volume_ratio_after'] >= vol_after_cfg.get('min', 0.7),
                
                # 8. 均线收敛度条件 (基于脚本分析优化)
                features['ma_convergence'] < ma_conv_cfg.get('max', 0.225),
                
                # 9. 价格相对均线位置条件 (基于脚本分析优化)
                ma20_cfg.get('min', -0.22) < features['price_vs_ma20'] < ma20_cfg.get('max', 0.22),
                ma60_cfg.get('min', -0.30) < features['price_vs_ma60'] < ma60_cfg.get('max', 0.30),
                
                # 10. 月线跌幅条件 (基于脚本分析优化)
                features['monthly_drop_rate'] > drop_cfg.get('min', 0.007),
                features['monthly_drop_rate'] < drop_cfg.get('max', 1.050),
                
                # 11. 均线斜率条件 (基于脚本分析优化)
                features['ma20_slope'] > slope_cfg.get('min', -0.075),
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查ML增强版条件时出错: {e}")
            return False

    @staticmethod
    def report(opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描/模拟结果 - RTB V21.0 ML增强版本
        """
        for opportunity in opportunities:
            logger.info(f"="*80)
            logger.info(f"RTB V21.0 ML增强版本 - 股票 {opportunity['stock']['name']} ({opportunity['stock']['id']})")
            logger.info(f"="*80)
            
            features = opportunity.get('extra_fields', {}).get('features', {})
            financial_indicators = opportunity.get('extra_fields', {}).get('financial_indicators', {})
            
            logger.info(f"📊 ML增强版核心参数:")
            logger.info(f"   波动率 (volatility): {features.get('volatility', 0):.4f} (权重: 0.106)")
            logger.info(f"   反转后成交量放大: {features.get('volume_ratio_after', 0):.2f}x (权重: 0.080)")
            logger.info(f"   均线收敛度: {features.get('ma_convergence', 0):.4f} (权重: 0.056)")
            logger.info(f"   价格vs MA20: {features.get('price_vs_ma20', 0):.4f} (权重: 0.046)")
            logger.info(f"   MA20斜率: {features.get('ma20_slope', 0):.4f}")
            logger.info(f"   月线跌幅: {features.get('monthly_drop_rate', 0):.2%}")
            logger.info(f"   RSI: {features.get('rsi', 0):.1f}")
            logger.info(f"   价格分位数: {features.get('price_percentile', 0):.2%}")
            
            logger.info(f"💰 财务指标:")
            logger.info(f"   市值: {financial_indicators.get('market_cap', 0)/10000:.1f}亿")
            logger.info(f"   PE: {financial_indicators.get('pe_ratio', 0):.1f}")
            logger.info(f"   PB: {financial_indicators.get('pb_ratio', 0):.2f}")
            
            logger.info(f"🎯 投资建议:")
            logger.info(f"   买入价格区间: {opportunity['lower_bound']:.2f} - {opportunity['upper_bound']:.2f}")
            logger.info(f"   当前价格: {opportunity['record_of_today']['close']:.2f}")
            logger.info(f"="*80)
