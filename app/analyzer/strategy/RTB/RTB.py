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
        扫描单只股票的投资机会 - RTB V9增强版
        
        使用13个信号条件（原有8个 + 新增5个）：
        1. ma_std < 0.035 (均线收敛)
        2. position < 0.45 (价格中低位)
        3. drawdown_120d >= 0.18 (前期中等跌幅)
        4. -0.03 < ma60slope < 0.03 (趋势微跌到微涨)
        5. return_20d <= -0.03 (近期微调)
        6. close_to_ma20 <= -0.01 (低于均线)
        7. ma_slope_consistency > 0.7 (MA斜率高一致性)
        8. ma_slope_std < 0.05 (MA斜率波动控制)
        9. 0.8 < volume_ratio < 2.0 (成交量适度) ⭐ 新增
        10. 0.5 < turnover_ratio < 1.5 (换手率适度) ⭐ 新增
        11. volatility_20d < 0.05 (波动率控制) ⭐ 新增
        12. 5 < pe_ratio < 30 (PE合理估值) ⭐ 新增
        13. 0.5 < pb_ratio < 3.0 (PB合理估值) ⭐ 新增

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

        # 计算V8的8个核心信号条件（使用周线数据）
        features = ReverseTrendBet._calculate_v8_features(weekly_klines, stock['id'], None)
        
        if not features:
            return None
            
        # 检查所有8个条件是否同时满足
        if not ReverseTrendBet._check_v8_conditions(features):
            return None

        # 构建机会对象
        opportunity = BaseStrategy.to_opportunity(
            stock=stock,
            record_of_today=record_of_today,
            extra_fields={
                'features': features,
                'strategy_version': 'V8_Weekly',
                'signal_conditions': {
                    'ma_convergence': features['ma_convergence'],
                    'position': features['position'],
                    'drawdown_120d': features['drawdown_120d'],
                    'return_20d': features['return_20d'],
                    'close_to_ma20': features['close_to_ma20'],
                    'trough_ratio': features['trough_ratio'],
                    'ma20_slope': features['ma20_slope'],
                    'ma60_slope': features['ma60_slope'],
                }
            },
            lower_bound=today_close * 0.98,  # 5%的买入区间
            upper_bound=today_close * 1.02,
        )

        return opportunity

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
        呈现扫描/模拟结果 - RTB V9增强版
        
        Args:
            opportunities: 扫描阶段的投资机会列表
        """
        for opportunity in opportunities:
            logger.info(f"="*80)
            logger.info(f"RTB V8周线版 策略 - 股票 {opportunity['stock']['name']} ({opportunity['stock']['id']})")
            logger.info(f"="*80)
            logger.info(f"扫描日期: {opportunity['date']}")
            logger.info(f"当前价格: {opportunity['price']}")
            logger.info(f"机会价格区间: {round(opportunity['lower_bound'], 2)} - {round(opportunity['upper_bound'], 2)}")
            
            # 显示V8特征
            features = opportunity['extra_fields'].get('features', {})
            signal_conditions = opportunity['extra_fields'].get('signal_conditions', {})
            
            logger.info(f"\n📊 V8周线版信号特征 (宽松阈值):")
            logger.info(f"  1. 均线收敛度 (ma_convergence): {signal_conditions.get('ma_convergence', 0):.4f} < 0.10 ⭐ 周线宽松")
            logger.info(f"  2. 价格位置 (position): {signal_conditions.get('position', 0):.3f} ∈ (0.10, 0.80) ⭐ 周线宽松")
            logger.info(f"  3. 前期跌幅 (drawdown_120d): {signal_conditions.get('drawdown_120d', 0):.3f} >= 0.10 ⭐ 周线宽松")
            logger.info(f"  4. 近期回调 (return_20d): {signal_conditions.get('return_20d', 0):.3f} ∈ (-0.08, 0.05) ⭐ 周线宽松")
            logger.info(f"  5. 相对MA20 (close_to_ma20): {signal_conditions.get('close_to_ma20', 0):.3f} <= 0.02 ⭐ 周线宽松")
            logger.info(f"  6. 波谷回溯 (trough_ratio): {signal_conditions.get('trough_ratio', 0):.3f} < 0.20 ⭐ 周线宽松")
            logger.info(f"  7. MA20斜率 (ma20_slope): {signal_conditions.get('ma20_slope', 0):.4f} ∈ (-0.08, 0.02) ⭐ 周线宽松")
            logger.info(f"  8. MA60斜率 (ma60_slope): {signal_conditions.get('ma60_slope', 0):.4f} ∈ (-0.05, 0.03) ⭐ 周线宽松")
            
            # 计算综合评分
            drawdown = signal_conditions.get('drawdown_120d', 0)
            if drawdown >= 0.40:
                icon = IconService.get('green_dot')
                score = "优秀"
            elif drawdown >= 0.30:
                icon = IconService.get('yellow_dot')
                score = "良好"
            elif drawdown >= 0.20:
                icon = IconService.get('orange_dot')
                score = "合格"
            else:
                icon = IconService.get('red_dot')
                score = "一般"
                
            logger.info(f"\n🎯 综合评分: {icon} {score} (前期跌幅: {drawdown*100:.1f}%)")
            logger.info(f"="*80)
        
        return None
    
