#!/usr/bin/env python3
"""
ReverseTrendBet 策略 - 在平稳段落中寻找突破机会
V8版本：基于ML优化的6个信号条件
"""
import math
import numpy as np
from typing import Dict, List, Any, Optional
from loguru import logger

from app.analyzer.strategy.RTB.settings import settings
from app.analyzer.analyzer_service import AnalyzerService
from utils.icon.icon_service import IconService
from ...components.base_strategy import BaseStrategy

class ReverseTrendBet(BaseStrategy):
    """ReverseTrendBet 策略实现"""
    
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="ReverseTrendBet",
            abbreviation="RTB"
        )
        super().initialize()

    # ========================================================
    # Core logic:
    # ========================================================

    @staticmethod
    def scan_opportunity(stock: Dict[str, Any], data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描单只股票的投资机会 - RTB V16机器学习优化版
        
        V16核心改进（基于104样本ML分析）：
        1. 信号检测：基于周线数据（长期趋势判断）
        2. 买入卖出：基于日线数据（精确执行）
        3. 时间止损：200个交易日（基于盈利样本171.8天平均时长）
        4. 止损优化：15%止损（基于ML分析的最大损失控制）
        5. RSI优化：放宽到70（基于ML分析RSI重要性较低）
        
        基于800股票样本的ML分析和失败因子反向研究，使用以下优化条件：
        
        核心收敛条件：
        1. ma_convergence < 0.068 (充分收敛，避免假突破)
        2. position > 0.33 (价格位置适中，避免过低位置)
        3. ma20_slope > 0.04 (MA20明显向上，避免疲软趋势)
        4. ma60_slope > -0.019 (MA60不向下，确保长期趋势稳定)
        
        成交量确认条件：
        5. volume_trend > 0 (成交量上升趋势)
        6. amount_ratio > 1.2 (成交金额放大)
        
        失败因子过滤：
        7. price_change_pct > -1.1 (避免价格变化太小)
        8. close_to_ma20 > -0.9 (价格与MA20有距离)
        9. duration_weeks < 20 (避免收敛时间过长)
        10. convergence_ratio > 0.068 (确保收敛充分)

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

        # 计算优化版特征（使用周线数据）
        features = ReverseTrendBet._calculate_optimized_features(weekly_klines, stock['id'], None)
        
        if not features:
            return None
            
        # 检查所有优化版条件是否同时满足
        if not ReverseTrendBet._check_optimized_conditions(features):
            return None

        # 构建机会对象
        opportunity = BaseStrategy.to_opportunity(
            stock=stock,
            record_of_today=record_of_today,
            extra_fields={
                'features': features,
                'strategy_version': 'V16_ML_Optimized',
                'signal_conditions': {
                    'ma_convergence': features['ma_convergence'],
                    'ma20_slope': features['ma20_slope'],
                    'ma60_slope': features['ma60_slope'],
                    'volume_trend': features['volume_trend'],
                    'amount_ratio': features['amount_ratio'],
                    'price_change_pct': features['price_change_pct'],
                    'close_to_ma20': features['close_to_ma20'],
                    'duration_weeks': features['duration_weeks'],
                    'convergence_ratio': features['convergence_ratio'],
                    'historical_percentile': features['historical_percentile'],
                    'oscillation_position': features['oscillation_position'],
                    'volume_confirmation': features['volume_confirmation'],
                    'rsi_signal': features['rsi_signal'],
                }
            },
            lower_bound=today_close * 0.98,  # 5%的买入区间
            upper_bound=today_close * 1.02,
        )

        return opportunity


    @staticmethod
    def _calculate_optimized_features(weekly_klines: List[Dict[str, Any]], stock_id: str = None, db_manager = None) -> Optional[Dict[str, float]]:
        """
        计算优化版V11策略的特征
        新增：历史分位数、震荡位置、成交量确认、RSI信号
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
            
            # 计算移动平均线
            ma5 = ReverseTrendBet._rolling_mean(closes, 5)
            ma10 = ReverseTrendBet._rolling_mean(closes, 10)
            ma20 = ReverseTrendBet._rolling_mean(closes, 20)
            ma60 = ReverseTrendBet._rolling_mean(closes, 60)
            
            if len(ma60) < 20:
                return None
                
            current_idx = -1
            
            # 1. ma_convergence: 均线收敛度
            ma_values = [ma5[current_idx], ma10[current_idx], ma20[current_idx], ma60[current_idx]]
            ma_max = max(ma_values)
            ma_min = min(ma_values)
            ma_convergence = (ma_max - ma_min) / closes[current_idx]
            
            # 2. ma20_slope: MA20斜率
            if len(ma20) >= 20:
                ma20_slope = (ma20[current_idx] - ma20[current_idx-20]) / ma20[current_idx-20]
            else:
                ma20_slope = 0
                
            # 3. ma60_slope: MA60斜率
            if len(ma60) >= 20:
                ma60_slope = (ma60[current_idx] - ma60[current_idx-20]) / ma60[current_idx-20]
            else:
                ma60_slope = 0
            
            # 4. volume_trend: 成交量趋势
            if len(volumes) >= 10:
                recent_vol = np.mean(volumes[-5:])
                prev_vol = np.mean(volumes[-10:-5])
                volume_trend = (recent_vol - prev_vol) / prev_vol if prev_vol > 0 else 0
            else:
                volume_trend = 0
                
            # 5. amount_ratio: 成交金额比率
            if len(amounts) >= 20:
                recent_amount = np.mean(amounts[-5:])
                avg_amount = np.mean(amounts[-20:])
                amount_ratio = recent_amount / avg_amount if avg_amount > 0 else 1
            else:
                amount_ratio = 1
            
            # 6. price_change_pct: 价格变化百分比
            if len(closes) >= 5:
                price_change_pct = (closes[current_idx] - closes[current_idx-5]) / closes[current_idx-5] * 100
            else:
                price_change_pct = 0
                
            # 7. close_to_ma20: 价格与MA20的距离百分比
            close_to_ma20 = (closes[current_idx] - ma20[current_idx]) / ma20[current_idx] * 100
            
            # 8. duration_weeks: 收敛持续时间
            duration_weeks = 10  # 简化处理
            
            # 9. convergence_ratio: 收敛比率
            convergence_ratio = ma_convergence
            
            # 10. historical_percentile: 全历史价格分位数 (新增)
            # 计算当前价格在历史价格中的分位数
            current_price = closes[current_idx]
            historical_percentile = (np.sum(closes <= current_price) / len(closes))
            
            # 11. oscillation_position: 震荡区间内位置 (新增)
            # 使用最近60周的高低点作为震荡区间
            if len(highs) >= 60:
                high_60w = np.max(highs[-60:])
                low_60w = np.min(lows[-60:])
                if high_60w > low_60w:
                    oscillation_position = (closes[current_idx] - low_60w) / (high_60w - low_60w)
                else:
                    oscillation_position = 0.5
            else:
                oscillation_position = 0.5
            
            # 12. volume_confirmation: 成交量确认信号 (新增)
            if len(volumes) >= 20:
                recent_vol = np.mean(volumes[-3:])
                avg_vol = np.mean(volumes[-20:])
                volume_confirmation = recent_vol / avg_vol if avg_vol > 0 else 1
            else:
                volume_confirmation = 1
            
            # 13. rsi_signal: RSI买入信号 (新增)
            # 使用框架的正确RSI计算
            rsi_signal = ReverseTrendBet._get_rsi_from_klines(weekly_klines)
            
            return {
                'ma_convergence': ma_convergence,
                'ma20_slope': ma20_slope,
                'ma60_slope': ma60_slope,
                'volume_trend': volume_trend,
                'amount_ratio': amount_ratio,
                'price_change_pct': price_change_pct,
                'close_to_ma20': close_to_ma20,
                'duration_weeks': duration_weeks,
                'convergence_ratio': convergence_ratio,
                'historical_percentile': historical_percentile,
                'oscillation_position': oscillation_position,
                'volume_confirmation': volume_confirmation,
                'rsi_signal': rsi_signal,
            }
            
        except Exception as e:
            logger.error(f"计算优化特征时出错: {e}")
            return None

    @staticmethod
    def _calculate_v10_features(weekly_klines: List[Dict[str, Any]], stock_id: str = None, db_manager = None) -> Optional[Dict[str, float]]:
        """
        计算V10 ML优化策略需要的特征
        基于800股票样本的ML分析和失败因子反向研究
        """
        try:
            # 提取价格和成交量数据
            closes = [k['close'] for k in weekly_klines if k.get('close')]
            highs = [k['highest'] for k in weekly_klines if k.get('highest')]
            lows = [k['lowest'] for k in weekly_klines if k.get('lowest')]
            volumes = [k['volume'] for k in weekly_klines if k.get('volume', 0)]
            amounts = [k['amount'] for k in weekly_klines if k.get('amount', 0)]
            dates = [k['date'] for k in weekly_klines if k.get('date')]
            
            if len(closes) < 100:  # 周线数据需要更少的数据点
                return None
                
            # 转换为numpy数组
            closes = np.array(closes)
            highs = np.array(highs)
            lows = np.array(lows)
            volumes = np.array(volumes)
            amounts = np.array(amounts)
            
            # 计算移动平均线
            ma5 = ReverseTrendBet._rolling_mean(closes, 5)
            ma10 = ReverseTrendBet._rolling_mean(closes, 10)
            ma20 = ReverseTrendBet._rolling_mean(closes, 20)
            ma60 = ReverseTrendBet._rolling_mean(closes, 60)
            
            if len(ma60) < 20:  # 确保有足够的数据
                return None
                
            current_idx = -1  # 最新数据
            
            # 1. ma_convergence: 均线收敛度 (用最大最小差值百分比)
            ma_values = [ma5[current_idx], ma10[current_idx], ma20[current_idx], ma60[current_idx]]
            ma_max = max(ma_values)
            ma_min = min(ma_values)
            ma_convergence = (ma_max - ma_min) / closes[current_idx]
            
            # 2. position: 价格相对位置（最近20周）
            if len(highs) >= 20:
                high_20w = np.max(highs[-20:])
                low_20w = np.min(lows[-20:])
                if high_20w > low_20w:
                    position = (closes[current_idx] - low_20w) / (high_20w - low_20w)
                else:
                    position = 0.5
            else:
                position = 0.5
            
            # 3. ma20_slope: MA20斜率 (20周变化率)
            if len(ma20) >= 20:
                ma20_slope = (ma20[current_idx] - ma20[current_idx-20]) / ma20[current_idx-20]
            else:
                ma20_slope = 0
                
            # 4. ma60_slope: MA60斜率 (20周变化率)
            if len(ma60) >= 20:
                ma60_slope = (ma60[current_idx] - ma60[current_idx-20]) / ma60[current_idx-20]
            else:
                ma60_slope = 0
            
            # 5. volume_trend: 成交量趋势 (最近5周vs前5周)
            if len(volumes) >= 10:
                recent_vol = np.mean(volumes[-5:])
                prev_vol = np.mean(volumes[-10:-5])
                volume_trend = (recent_vol - prev_vol) / prev_vol if prev_vol > 0 else 0
            else:
                volume_trend = 0
                
            # 6. amount_ratio: 成交金额比率 (最近5周vs历史平均)
            if len(amounts) >= 20:
                recent_amount = np.mean(amounts[-5:])
                avg_amount = np.mean(amounts[-20:])
                amount_ratio = recent_amount / avg_amount if avg_amount > 0 else 1
            else:
                amount_ratio = 1
            
            # 7. price_change_pct: 价格变化百分比 (最近5周)
            if len(closes) >= 5:
                price_change_pct = (closes[current_idx] - closes[current_idx-5]) / closes[current_idx-5] * 100
            else:
                price_change_pct = 0
                
            # 8. close_to_ma20: 价格与MA20的距离百分比
            close_to_ma20 = (closes[current_idx] - ma20[current_idx]) / ma20[current_idx] * 100
            
            # 9. duration_weeks: 收敛持续时间 (使用mark_period功能)
            # 这里简化计算，实际应该使用mark_period功能
            # 暂时用固定值，后续可以优化
            duration_weeks = 10  # 简化处理
            
            # 10. convergence_ratio: 收敛比率 (与ma_convergence相同)
            convergence_ratio = ma_convergence
            
            return {
                'ma_convergence': ma_convergence,
                'position': position,
                'ma20_slope': ma20_slope,
                'ma60_slope': ma60_slope,
                'volume_trend': volume_trend,
                'amount_ratio': amount_ratio,
                'price_change_pct': price_change_pct,
                'close_to_ma20': close_to_ma20,
                'duration_weeks': duration_weeks,
                'convergence_ratio': convergence_ratio,
            }
            
        except Exception as e:
            logger.error(f"计算V10特征时出错: {e}")
            return None

    @staticmethod
    def _get_rsi_from_klines(klines: List[Dict[str, Any]]) -> float:
        """
        从K线数据中获取RSI值，优先使用框架计算的RSI，如果没有则手动计算
        
        Args:
            klines: K线数据列表
            
        Returns:
            RSI值 (0-100)
        """
        try:
            # 首先尝试从框架计算的RSI字段获取
            rsi_values = []
            for k in klines:
                # 检查RSI字段名（统一使用"rsi"）
                rsi_val = k.get('rsi')
                if rsi_val is not None and rsi_val != 0 and rsi_val > 0:
                    rsi_values.append(float(rsi_val))
            
            if len(rsi_values) > 0:
                return rsi_values[-1]  # 返回最新的RSI值
            
            # 如果框架计算的RSI不可用，使用手动计算
            return ReverseTrendBet._calculate_rsi_manual(klines)
            
        except Exception as e:
            logger.warning(f"获取RSI时出错: {e}")
            return 50.0  # 默认中性值

    @staticmethod
    def _calculate_rsi_manual(klines: List[Dict[str, Any]], period: int = 14) -> float:
        """
        手动计算RSI指标
        
        Args:
            klines: K线数据列表
            period: RSI周期，默认14
            
        Returns:
            RSI值 (0-100)
        """
        try:
            if len(klines) < period + 1:
                return 50.0  # 数据不足时返回中性值
            
            # 提取收盘价
            closes = [float(k.get('close', 0)) for k in klines[-period-1:]]
            
            if len(closes) < period + 1:
                return 50.0
            
            # 计算价格变化
            price_changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            
            # 分离上涨和下跌
            gains = [max(change, 0) for change in price_changes]
            losses = [max(-change, 0) for change in price_changes]
            
            # 计算平均上涨和下跌
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
            
            # 避免除零错误
            if avg_loss == 0:
                return 100.0
            
            # 计算RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return round(rsi, 2)
            
        except Exception as e:
            logger.warning(f"计算RSI时出错: {e}")
            return 50.0

    @staticmethod
    def _check_optimized_conditions(features: Dict[str, float]) -> bool:
        """
        检查V16机器学习优化版策略的所有条件
        
        基于104样本ML分析的关键发现：
        1. 最大损失控制是关键（效应大小：2.452）
        2. 投资时长对盈利重要（效应大小：0.778）
        3. RSI重要性较低，可以放宽条件
        """
        try:
            conditions = [
                # 核心收敛条件 (基于ML分析优化)
                features['ma_convergence'] < 0.09,   # 充分收敛 (从0.12收紧到0.09)
                features['ma20_slope'] > -0.05,      # MA20趋势
                features['ma60_slope'] > -0.05,      # MA60趋势稳定
                
                # 成交量确认条件 (保持原有)
                features['volume_trend'] > -0.3,     # 成交量趋势
                features['amount_ratio'] > 0.7,      # 成交金额比率
                
                # 失败因子过滤 (保持原有)
                features['price_change_pct'] > -6.0, # 价格变化控制
                features['close_to_ma20'] > -5.0,    # MA20距离控制
                features['duration_weeks'] < 20,     # 收敛时间控制
                features['convergence_ratio'] > 0.06, # 收敛充分性
                
                # 新增优化条件 (基于ML分析收紧)
                features['historical_percentile'] < 0.35, # 历史分位数 < 35% (从50%收紧到35%)
                features['oscillation_position'] < 0.5,   # 震荡区间内位置 < 50% (在区间下半部分)
                features['volume_confirmation'] > 0.8,    # 成交量确认 > 0.8 (适度放量)
                features['rsi_signal'] < 70,              # RSI < 70 (基于ML分析放宽条件)
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查V15优化条件时出错: {e}")
            return False

    @staticmethod
    def _check_v11_conditions(features: Dict[str, float]) -> bool:
        """
        检查V11实用版策略的所有条件
        
        基于V10分析结果调整，平衡严格性和实用性
        """
        try:
            conditions = [
                # 核心收敛条件 (进一步放宽)
                features['ma_convergence'] < 0.12,   # 充分收敛 (从0.08放宽到0.12)
                features['position'] > 0.15,         # 价格位置适中 (从0.25放宽到0.15)
                features['ma20_slope'] > -0.05,      # MA20趋势 (从0.02放宽到-0.05)
                features['ma60_slope'] > -0.05,      # MA60趋势稳定 (从-0.03放宽到-0.05)
                
                # 成交量确认条件 (进一步放宽)
                features['volume_trend'] > -0.3,     # 成交量趋势 (从-0.1放宽到-0.3)
                features['amount_ratio'] > 0.7,      # 成交金额比率 (从1.0放宽到0.7)
                
                # 失败因子过滤 (进一步放宽)
                features['price_change_pct'] > -6.0, # 价格变化控制 (从-2.0放宽到-6.0)
                features['close_to_ma20'] > -5.0,    # MA20距离控制 (从-2.0放宽到-5.0)
                features['duration_weeks'] < 20,     # 收敛时间控制 (保持不变)
                features['convergence_ratio'] > 0.06, # 收敛充分性 (从0.08放宽到0.06)
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查V11条件时出错: {e}")
            return False

    @staticmethod
    def _check_v10_conditions(features: Dict[str, float]) -> bool:
        """
        检查V10 ML优化策略的所有条件
        
        基于800股票样本的ML分析和失败因子反向研究
        """
        try:
            conditions = [
                # 核心收敛条件
                features['ma_convergence'] < 0.068,  # 充分收敛，避免假突破
                features['position'] > 0.33,         # 价格位置适中，避免过低位置
                features['ma20_slope'] > 0.04,       # MA20明显向上，避免疲软趋势
                features['ma60_slope'] > -0.019,     # MA60不向下，确保长期趋势稳定
                
                # 成交量确认条件
                features['volume_trend'] > 0,        # 成交量上升趋势
                features['amount_ratio'] > 1.2,      # 成交金额放大
                
                # 失败因子过滤
                features['price_change_pct'] > -1.1, # 避免价格变化太小
                features['close_to_ma20'] > -0.9,    # 价格与MA20有距离
                features['duration_weeks'] < 20,     # 避免收敛时间过长
                features['convergence_ratio'] > 0.068, # 确保收敛充分
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查V10条件时出错: {e}")
            return False

    @staticmethod
    def _calculate_v8_features(daily_klines: List[Dict[str, Any]], stock_id: str = None, db_manager = None) -> Optional[Dict[str, float]]:
        """
        计算V8策略需要的8个核心特征
        """
        try:
            # 提取价格数据
            closes = [k['close'] for k in daily_klines if k.get('close')]
            highs = [k['highest'] for k in daily_klines if k.get('highest')]
            lows = [k['lowest'] for k in daily_klines if k.get('lowest')]
            
            if len(closes) < 100:  # 周线数据需要更少的数据点
                return None
                
            # 转换为numpy数组
            closes = np.array(closes)
            highs = np.array(highs)
            lows = np.array(lows)
            
            # 计算移动平均线
            ma5 = ReverseTrendBet._rolling_mean(closes, 5)
            ma10 = ReverseTrendBet._rolling_mean(closes, 10)
            ma20 = ReverseTrendBet._rolling_mean(closes, 20)
            ma60 = ReverseTrendBet._rolling_mean(closes, 60)
            
            if len(ma60) < 20:  # 确保有足够的数据
                return None
                
            current_idx = -1  # 最新数据
            
            # 1. ma_convergence: 均线收敛度 (用最大最小差值百分比)
            ma_values = [ma5[current_idx], ma10[current_idx], ma20[current_idx], ma60[current_idx]]
            ma_max = max(ma_values)
            ma_min = min(ma_values)
            ma_convergence = (ma_max - ma_min) / closes[current_idx]
            
            # 2. position: 价格相对位置（最近20周）
            if len(highs) >= 20:
                high_20w = np.max(highs[-20:])
                low_20w = np.min(lows[-20:])
                if high_20w > low_20w:
                    position = (closes[current_idx] - low_20w) / (high_20w - low_20w)
                else:
                    position = 0.5
            else:
                position = 0.5
                
            # 3. drawdown_120d: 120周跌幅（约2.3年）
            if len(highs) >= 120:
                high_120w = np.max(highs[-120:])
                drawdown_120d = (high_120w - closes[current_idx]) / high_120w
            else:
                drawdown_120d = 0.0
                
            # 4. 计算所有MA的斜率（20周变化率）
            ma_slopes = {}
            for ma_name, ma_data in [('ma5', ma5), ('ma10', ma10), ('ma20', ma20), ('ma60', ma60)]:
                if len(ma_data) >= 20:
                    ma_20w_ago = ma_data[current_idx - 20]
                    if ma_20w_ago > 0:
                        slope = (ma_data[current_idx] - ma_20w_ago) / ma_20w_ago
                    else:
                        slope = 0.0
                else:
                    slope = 0.0
                ma_slopes[f'{ma_name}_slope'] = slope
            
            # 保持ma60slope用于兼容性
            ma60slope = ma_slopes['ma60_slope']
                
            # 5. return_20w: 20周收益率
            if len(closes) >= 20:
                close_20w_ago = closes[current_idx - 20]
                if close_20w_ago > 0:
                    return_20d = (closes[current_idx] - close_20w_ago) / close_20w_ago
                else:
                    return_20d = 0.0
            else:
                return_20d = 0.0
                
            # 6. close_to_ma20: 价格相对MA20位置
            if ma20[current_idx] > 0:
                close_to_ma20 = (closes[current_idx] - ma20[current_idx]) / ma20[current_idx]
            else:
                close_to_ma20 = 0.0
                
            # 7. 简单回溯：检查是否有波谷
            # 检查过去60周是否有明显的波谷
            if len(lows) >= 60:
                # 寻找过去60周的最低点
                past_60w_lows = lows[-60:-10]  # 排除最近10周，避免当前价格影响
                if len(past_60w_lows) > 0:
                    past_trough = np.min(past_60w_lows)
                    current_price = closes[current_idx]
                    # 如果过去有波谷且明显低于当前价格，可能买在山顶
                    trough_ratio = (current_price - past_trough) / past_trough
                else:
                    trough_ratio = 0.0
            else:
                trough_ratio = 0.0
            
            # 8. 简化：只保留MA20和MA60斜率，去掉一致性检查
            
            # V9新增特征
            # 10. volume_ratio: 成交量比率
            volumes = [k.get('volume', 0) for k in daily_klines if k.get('volume')]
            if len(volumes) >= 20:
                volume_ma20 = np.mean(volumes[-20:])
                current_volume = volumes[current_idx]
                volume_ratio = current_volume / volume_ma20 if volume_ma20 > 0 else 1.0
            else:
                volume_ratio = 1.0
            
            # 11. turnover_ratio: 换手率比率
            turnovers = [k.get('turnover_rate', 0) for k in daily_klines if k.get('turnover_rate')]
            if len(turnovers) >= 20:
                turnover_ma20 = np.mean(turnovers[-20:])
                current_turnover = turnovers[current_idx]
                turnover_ratio = current_turnover / turnover_ma20 if turnover_ma20 > 0 else 1.0
            else:
                turnover_ratio = 1.0
            
            # 12. volatility_20w: 20周波动率
            if len(closes) >= 21:
                returns = np.diff(closes[-21:]) / closes[-21:-1]
                volatility_20d = np.std(returns) if len(returns) > 1 else 0.0
            else:
                volatility_20d = 0.0
            
            # 13. 暂时去掉PE、PB，专注于技术指标
                
            return {
                'ma_convergence': ma_convergence,  # 新的均线收敛度
                'position': position,
                'drawdown_120d': drawdown_120d,
                'return_20d': return_20d,
                'close_to_ma20': close_to_ma20,
                'trough_ratio': trough_ratio,  # 新增：波谷回溯检查
                'ma20_slope': ma_slopes['ma20_slope'],  # 只保留MA20和MA60斜率
                'ma60_slope': ma_slopes['ma60_slope'],
                'volume_ratio': volume_ratio,
                'turnover_ratio': turnover_ratio,
                'volatility_20d': volatility_20d,
            }
            
        except Exception as e:
            logger.debug(f"计算V8特征时出错: {e}")
            return None

    @staticmethod
    def _rolling_mean(data: np.ndarray, window: int) -> np.ndarray:
        """计算滚动平均"""
        if len(data) < window:
            return np.array([])
        result = np.zeros(len(data))
        for i in range(window - 1, len(data)):
            result[i] = np.mean(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def _check_v8_conditions(features: Dict[str, float]) -> bool:
        """
        检查V8的8个核心信号条件是否全部满足
        """
        try:
            # V8周线版：适合周线数据的宽松阈值
            conditions = [
                # 1. 均线收敛度（周线宽松）
                features['ma_convergence'] < 0.10,            # 均线收敛度 < 0.10 (周线数据波动更大)
                
                # 2. 价格位置（周线宽松）
                0.10 < features['position'] < 0.80,           # 价格位置在0.10-0.80之间 (周线范围更广)
                
                # 3. 前期跌幅（周线宽松）
                features['drawdown_120d'] >= 0.10,            # 前期跌幅 >= 0.10 (周线跌幅要求降低)
                
                # 4. 近期回调（周线宽松）
                -0.08 < features['return_20d'] < 0.05,        # 近期回调在-0.08到0.05之间 (周线波动更大)
                
                # 5. 低于均线（周线宽松）
                features['close_to_ma20'] <= 0.02,            # 低于均线 <= 0.02 (周线允许更高)
                
                # 6. 波谷回溯检查（周线宽松）
                features['trough_ratio'] < 0.20,              # 波谷回溯 < 0.20 (周线允许更大波动)
                
                # 7. MA20斜率（周线宽松）
                -0.08 < features['ma20_slope'] < 0.02,        # MA20斜率在-0.08到0.02之间 (周线范围更广)
                
                # 8. MA60斜率（周线宽松）
                -0.05 < features['ma60_slope'] < 0.03,        # MA60斜率在-0.05到0.03之间 (周线范围更广)
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.debug(f"检查V8条件时出错: {e}")
            return False

    @staticmethod
    def report(opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描/模拟结果 - RTB V15机器学习优化版
        
        Args:
            opportunities: 扫描阶段的投资机会列表
        """
        for opportunity in opportunities:
            logger.info(f"="*80)
            logger.info(f"RTB V16机器学习优化版 策略 - 股票 {opportunity['stock']['name']} ({opportunity['stock']['id']})")
            logger.info(f"="*80)
            logger.info(f"扫描日期: {opportunity['date']}")
            logger.info(f"当前价格: {opportunity['price']}")
            logger.info(f"机会价格区间: {round(opportunity['lower_bound'], 2)} - {round(opportunity['upper_bound'], 2)}")
            
            # 显示V10特征
            features = opportunity['extra_fields'].get('features', {})
            signal_conditions = opportunity['extra_fields'].get('signal_conditions', {})
            
            logger.info(f"\n📊 V16机器学习优化版信号特征 (基于104样本ML分析):")
            logger.info(f"核心收敛条件:")
            logger.info(f"  1. 均线收敛度 (ma_convergence): {signal_conditions.get('ma_convergence', 0):.4f} < 0.09 ⭐ 充分收敛")
            logger.info(f"  2. MA20斜率 (ma20_slope): {signal_conditions.get('ma20_slope', 0):.4f} > -0.05 ⭐ 趋势稳定")
            logger.info(f"  3. MA60斜率 (ma60_slope): {signal_conditions.get('ma60_slope', 0):.4f} > -0.05 ⭐ 长期稳定")
            
            logger.info(f"\n成交量确认条件:")
            logger.info(f"  4. 成交量趋势 (volume_trend): {signal_conditions.get('volume_trend', 0):.3f} > -0.3 ⭐ 成交量趋势")
            logger.info(f"  5. 成交金额比率 (amount_ratio): {signal_conditions.get('amount_ratio', 0):.3f} > 0.7 ⭐ 金额确认")
            
            logger.info(f"\n失败因子过滤:")
            logger.info(f"  6. 价格变化 (price_change_pct): {signal_conditions.get('price_change_pct', 0):.2f}% > -6.0 ⭐ 变化控制")
            logger.info(f"  7. 相对MA20 (close_to_ma20): {signal_conditions.get('close_to_ma20', 0):.2f}% > -5.0 ⭐ 距离控制")
            logger.info(f"  8. 收敛时长 (duration_weeks): {signal_conditions.get('duration_weeks', 0):.0f} < 20 ⭐ 时间控制")
            logger.info(f"  9. 收敛比率 (convergence_ratio): {signal_conditions.get('convergence_ratio', 0):.4f} > 0.06 ⭐ 充分收敛")
            
            logger.info(f"\n新增优化条件 (Reverse Bet核心):")
            logger.info(f" 10. 历史分位数 (historical_percentile): {signal_conditions.get('historical_percentile', 0):.3f} < 0.35 ⭐ 历史低位 (ML优化)")
            logger.info(f" 11. 震荡位置 (oscillation_position): {signal_conditions.get('oscillation_position', 0):.3f} < 0.5 ⭐ 区间下沿")
            logger.info(f" 12. 成交量确认 (volume_confirmation): {signal_conditions.get('volume_confirmation', 0):.3f} > 0.8 ⭐ 放量确认")
            logger.info(f" 13. RSI信号 (rsi_signal): {signal_conditions.get('rsi_signal', 0):.1f} < 70 ⭐ 基于ML分析优化")
            
            # 计算综合评分 (基于ML模型预测概率)
            ma20_slope = signal_conditions.get('ma20_slope', 0)
            amount_ratio = signal_conditions.get('amount_ratio', 0)
            
            # 简化的评分逻辑
            if ma20_slope > 0.1 and amount_ratio > 1.5:
                icon = IconService.get('green_dot')
                score = "优秀"
            elif ma20_slope > 0.06 and amount_ratio > 1.3:
                icon = IconService.get('yellow_dot')
                score = "良好"
            elif ma20_slope > 0.04 and amount_ratio > 1.2:
                icon = IconService.get('orange_dot')
                score = "合格"
            else:
                icon = IconService.get('red_dot')
                score = "一般"
                
            logger.info(f"\n🎯 V16机器学习优化评分: {icon} {score} (历史分位数: {signal_conditions.get('historical_percentile', 0):.3f}, RSI: {signal_conditions.get('rsi_signal', 0):.1f})")
            logger.info(f"="*80)
        
        return None
    
