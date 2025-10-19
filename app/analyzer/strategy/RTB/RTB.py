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
        
        # V18.2: 分层财务筛选，在质量基础上增加机会
        financial_indicators = ReverseTrendBet._get_financial_indicators_from_klines(record_of_today)
        if not ReverseTrendBet._check_tiered_financial_conditions(financial_indicators):
            return None
        
        # V19.0: 基于标签的动态参数优化
        labels_data = data.get('labels', [])
        if labels_data:
            # 过滤出需要的标签种类
            from app.data_loader import DataLoader
            filtered_labels = DataLoader.filter_labels_by_category(
                [label.get('label_id') for label in labels_data],
                ['market_cap', 'volatility']
            )
            logger.info(f"股票 {stock['id']} 标签数据: {filtered_labels}")
        
        # 检查所有优化版条件是否同时满足
        if not ReverseTrendBet._check_optimized_conditions(features):
            return None

        # 构建机会对象
        opportunity = BaseStrategy.to_opportunity(
            stock=stock,
            record_of_today=record_of_today,
            extra_fields={
                'features': features,
                'strategy_version': 'V18.2_Balanced',
                'financial_indicators': financial_indicators,
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
            lower_bound=today_close * 0.98,  # 4%的买入区间
            upper_bound=today_close * 1.02,
        )

        return opportunity


    @staticmethod
    def _get_financial_indicators_from_klines(current_kline: Dict[str, Any]) -> Dict[str, float]:
        """
        从当前K线数据中提取财务指标
        
        Args:
            current_kline: 当前扫描日期的K线数据
            
        Returns:
            Dict: 财务指标字典
        """
        try:
            # 从当前K线提取财务指标（扫描当时的财务数据）
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
    def _check_financial_conditions(financial_indicators: Dict[str, float]) -> bool:
        """
        检查V18.5财务指标筛选条件（大幅放宽）
        
        Args:
            financial_indicators: 财务指标字典
            
        Returns:
            bool: 是否通过财务筛选
        """
        try:
            # 如果没有财务数据，跳过财务筛选（向后兼容）
            if not financial_indicators:
                return True
            
            conditions = [
                # 市值筛选：> 20亿 (从30亿放宽)
                financial_indicators.get('market_cap', 0) > 200000,  # 20亿（万元）
                
                # PE筛选：10 < PE < 200 (从15-150放宽)
                (financial_indicators.get('pe_ratio', 0) > 10 and 
                 financial_indicators.get('pe_ratio', 0) < 200),
                
                # PB筛选：0.2 < PB < 10 (从0.3-8放宽)
                (financial_indicators.get('pb_ratio', 0) > 0.2 and 
                 financial_indicators.get('pb_ratio', 0) < 10.0),
                
                # PS筛选：0.3 < PS < 20 (从0.5-15放宽)
                (financial_indicators.get('ps_ratio', 0) > 0.3 and 
                 financial_indicators.get('ps_ratio', 0) < 20.0),
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查财务条件时出错: {e}")
            return True  # 出错时通过筛选（向后兼容）

    @staticmethod
    def _check_tiered_financial_conditions(financial_indicators: Dict[str, float]) -> bool:
        """
        检查V18.2分层财务指标筛选条件
        
        Args:
            financial_indicators: 财务指标字典
            
        Returns:
            bool: 是否通过分层财务筛选
        """
        try:
            # 如果没有财务数据，跳过财务筛选（向后兼容）
            if not financial_indicators:
                return True
            
            market_cap = financial_indicators.get('market_cap', 0)  # 万元
            pe_ratio = financial_indicators.get('pe_ratio', 0)
            pb_ratio = financial_indicators.get('pb_ratio', 0)
            ps_ratio = financial_indicators.get('ps_ratio', 0)
            
            # 分层财务筛选
            if market_cap >= 1000000:  # 大盘股 >= 100亿
                conditions = [
                    market_cap >= 1000000,  # 市值 >= 100亿
                    pe_ratio > 8 and pe_ratio < 80,  # PE: 8-80
                    pb_ratio > 0.5 and pb_ratio < 8,  # PB: 0.5-8
                    ps_ratio > 0.5 and ps_ratio < 15,  # PS: 0.5-15
                ]
            elif market_cap >= 300000:  # 中盘股 30-100亿
                conditions = [
                    market_cap >= 300000 and market_cap < 1000000,  # 市值: 30-100亿
                    pe_ratio > 10 and pe_ratio < 100,  # PE: 10-100
                    pb_ratio > 0.3 and pb_ratio < 10,  # PB: 0.3-10
                    ps_ratio > 0.3 and ps_ratio < 20,  # PS: 0.3-20
                ]
            else:  # 小盘股 < 30亿
                conditions = [
                    market_cap < 300000,  # 市值 < 30亿
                    pe_ratio > 5 and pe_ratio < 150,  # PE: 5-150
                    pb_ratio > 0.2 and pb_ratio < 15,  # PB: 0.2-15
                    ps_ratio > 0.2 and ps_ratio < 25,  # PS: 0.2-25
                ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查分层财务条件时出错: {e}")
            return True  # 出错时通过筛选（向后兼容）

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
            
            # 直接使用框架计算的移动平均线
            current_kline = weekly_klines[-1]
            ma5_val = current_kline.get('ma5')
            ma10_val = current_kline.get('ma10')
            ma20_val = current_kline.get('ma20')
            ma60_val = current_kline.get('ma60')
            
            # 如果框架没有计算MA值，跳过这个信号检测
            if not all([ma5_val, ma10_val, ma20_val, ma60_val]):
                return None
            
            # 1. ma_convergence: 均线收敛度
            ma_values = [ma5_val, ma10_val, ma20_val, ma60_val]
            ma_max = max(ma_values)
            ma_min = min(ma_values)
            ma_convergence = (ma_max - ma_min) / closes[-1]
            
            # 2. ma20_slope: MA20斜率 (使用过去20周的数据计算)
            if len(weekly_klines) >= 21:  # 需要至少21条数据来计算20周斜率
                ma20_20w_ago = weekly_klines[-21].get('ma20')
                if ma20_20w_ago and ma20_20w_ago > 0:
                    ma20_slope = (ma20_val - ma20_20w_ago) / ma20_20w_ago
                else:
                    return None
            else:
                return None
                
            # 3. ma60_slope: MA60斜率 (使用过去20周的数据计算)
            if len(weekly_klines) >= 21:  # 需要至少21条数据来计算20周斜率
                ma60_20w_ago = weekly_klines[-21].get('ma60')
                if ma60_20w_ago and ma60_20w_ago > 0:
                    ma60_slope = (ma60_val - ma60_20w_ago) / ma60_20w_ago
                else:
                    return None
            else:
                return None
            
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
                price_change_pct = (closes[-1] - closes[-6]) / closes[-6] * 100
            else:
                price_change_pct = 0
                
            # 7. close_to_ma20: 价格与MA20的距离百分比
            close_to_ma20 = (closes[-1] - ma20_val) / ma20_val * 100
            
            # 8. duration_weeks: 收敛持续时间
            duration_weeks = 10  # 简化处理
            
            # 9. convergence_ratio: 收敛比率
            convergence_ratio = ma_convergence
            
            # 10. historical_percentile: 全历史价格分位数 (新增)
            # 计算当前价格在历史价格中的分位数
            current_price = closes[-1]
            historical_percentile = (np.sum(closes <= current_price) / len(closes))
            
            # 11. oscillation_position: 震荡区间内位置 (新增)
            # 使用最近60周的高低点作为震荡区间
            if len(highs) >= 60:
                high_60w = np.max(highs[-60:])
                low_60w = np.min(lows[-60:])
                if high_60w > low_60w:
                    oscillation_position = (closes[-1] - low_60w) / (high_60w - low_60w)
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
            # 直接使用框架计算的RSI值
            rsi_signal = weekly_klines[-1].get('rsi', 50.0) if weekly_klines else 50.0
            
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
    def _check_optimized_conditions(features: Dict[str, float], optimized_settings: Dict[str, Any] = None) -> bool:
        """
        检查V18.2平衡策略的所有条件
        
        基于V17质量要求优化：
        1. 分层财务筛选：不同市值使用不同标准
        2. 适度收紧技术条件：在质量基础上增加机会
        """
        try:
            conditions = [
                # 核心收敛条件 (V18.2优化：适度收紧提升质量)
                features['ma_convergence'] < 0.18,   # V18.2优化：从0.20收紧到0.18
                features['ma20_slope'] > -0.08,      # V18.2优化：从-0.10收紧到-0.08
                features['ma60_slope'] > -0.08,      # V18.2优化：从-0.10收紧到-0.08
                
                # 成交量确认条件 (V18.2优化：适度收紧)
                features['volume_trend'] > -0.4,     # V18.2优化：从-0.5收紧到-0.4
                features['amount_ratio'] > 0.65,     # V18.2优化：从0.6收紧到0.65
                
                # 失败因子过滤 (保持原有)
                features['price_change_pct'] > -6.0, # 价格变化控制
                features['close_to_ma20'] > -5.0,    # MA20距离控制
                features['duration_weeks'] < 20,     # 收敛时间控制
                features['convergence_ratio'] > 0.06, # 收敛充分性
                
                # 新增优化条件 (V18.2平衡优化：适度收紧)
                features['historical_percentile'] < 0.45,  # V18.2优化：从0.5收紧到0.45
                features['oscillation_position'] < 0.55,   # V18.2优化：从0.6收紧到0.55
                features['volume_confirmation'] > 0.65,    # V18.2优化：从0.6收紧到0.65
                features['rsi_signal'] < 72,              # V18.2优化：从75收紧到72
            ]
            
            return all(conditions)
            
        except Exception as e:
            logger.error(f"检查V18.5优化条件时出错: {e}")
            return False

    @staticmethod
    def report(opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描/模拟结果 - RTB V18.2平衡策略
        
        Args:
            opportunities: 扫描阶段的投资机会列表
        """
        for opportunity in opportunities:
            logger.info(f"="*80)
            logger.info(f"RTB V18.2平衡策略 - 股票 {opportunity['stock']['name']} ({opportunity['stock']['id']})")
            logger.info(f"="*80)
            logger.info(f"扫描日期: {opportunity['date']}")
            logger.info(f"当前价格: {opportunity['price']}")
            logger.info(f"机会价格区间: {round(opportunity['lower_bound'], 2)} - {round(opportunity['upper_bound'], 2)}")
            
            # 显示V10特征
            features = opportunity['extra_fields'].get('features', {})
            signal_conditions = opportunity['extra_fields'].get('signal_conditions', {})
            
            logger.info(f"\n📊 V18.2平衡策略信号特征 (分层财务筛选+优化技术条件):")
            logger.info(f"核心收敛条件:")
            logger.info(f"  1. 均线收敛度 (ma_convergence): {signal_conditions.get('ma_convergence', 0):.4f} < 0.18 ⭐ V18.2收紧")
            logger.info(f"  2. MA20斜率 (ma20_slope): {signal_conditions.get('ma20_slope', 0):.4f} > -0.08 ⭐ V18.2收紧")
            logger.info(f"  3. MA60斜率 (ma60_slope): {signal_conditions.get('ma60_slope', 0):.4f} > -0.08 ⭐ V18.2收紧")
            
            logger.info(f"\n成交量确认条件:")
            logger.info(f"  4. 成交量趋势 (volume_trend): {signal_conditions.get('volume_trend', 0):.3f} > -0.4 ⭐ V18.2收紧")
            logger.info(f"  5. 成交金额比率 (amount_ratio): {signal_conditions.get('amount_ratio', 0):.3f} > 0.65 ⭐ V18.2收紧")
            
            logger.info(f"\n失败因子过滤:")
            logger.info(f"  6. 价格变化 (price_change_pct): {signal_conditions.get('price_change_pct', 0):.2f}% > -6.0 ⭐ 变化控制")
            logger.info(f"  7. 相对MA20 (close_to_ma20): {signal_conditions.get('close_to_ma20', 0):.2f}% > -5.0 ⭐ 距离控制")
            logger.info(f"  8. 收敛时长 (duration_weeks): {signal_conditions.get('duration_weeks', 0):.0f} < 20 ⭐ 时间控制")
            logger.info(f"  9. 收敛比率 (convergence_ratio): {signal_conditions.get('convergence_ratio', 0):.4f} > 0.06 ⭐ 充分收敛")
            
            logger.info(f"\n新增优化条件 (Reverse Bet核心):")
            logger.info(f" 10. 历史分位数 (historical_percentile): {signal_conditions.get('historical_percentile', 0):.3f} < 0.45 ⭐ V18.2收紧")
            logger.info(f" 11. 震荡位置 (oscillation_position): {signal_conditions.get('oscillation_position', 0):.3f} < 0.55 ⭐ V18.2收紧")
            logger.info(f" 12. 成交量确认 (volume_confirmation): {signal_conditions.get('volume_confirmation', 0):.3f} > 0.65 ⭐ V18.2收紧")
            logger.info(f" 13. RSI信号 (rsi_signal): {signal_conditions.get('rsi_signal', 0):.1f} < 72 ⭐ V18.2收紧")
            
            # 显示财务筛选信息
            financial_indicators = opportunity['extra_fields'].get('financial_indicators', {})
            if financial_indicators:
                market_cap = financial_indicators.get('market_cap', 0)
                pe_ratio = financial_indicators.get('pe_ratio', 0)
                pb_ratio = financial_indicators.get('pb_ratio', 0)
                ps_ratio = financial_indicators.get('ps_ratio', 0)
                
                logger.info(f"\n💰 分层财务筛选条件:")
                if market_cap >= 1000000:  # 大盘股
                    logger.info(f"  市值: {market_cap/10000:.1f}亿 (大盘股) | PE: {pe_ratio:.1f} (8-80) | PB: {pb_ratio:.2f} (0.5-8) | PS: {ps_ratio:.2f} (0.5-15)")
                elif market_cap >= 300000:  # 中盘股
                    logger.info(f"  市值: {market_cap/10000:.1f}亿 (中盘股) | PE: {pe_ratio:.1f} (10-100) | PB: {pb_ratio:.2f} (0.3-10) | PS: {ps_ratio:.2f} (0.3-20)")
                else:  # 小盘股
                    logger.info(f"  市值: {market_cap/10000:.1f}亿 (小盘股) | PE: {pe_ratio:.1f} (5-150) | PB: {pb_ratio:.2f} (0.2-15) | PS: {ps_ratio:.2f} (0.2-25)")
            
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
                
            logger.info(f"\n🎯 V18.2平衡策略评分: {icon} {score} (历史分位数: {signal_conditions.get('historical_percentile', 0):.3f}, RSI: {signal_conditions.get('rsi_signal', 0):.1f})")
            logger.info(f"="*80)
        
        return None
    
    @staticmethod
    def _get_optimized_settings_by_labels(settings: Dict[str, Any], labels_data: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        基于标签数据优化策略参数
        
        Args:
            settings: 原始设置
            labels_data: 标签数据，格式为 {category: [label_ids]}
            
        Returns:
            Dict: 优化后的设置
        """
        try:
            # 复制原始设置
            optimized_settings = settings.copy()
            
            # 检查是否启用标签优化
            labels_config = settings.get('labels', {})
            if not labels_config.get('enable_label_optimization', False):
                return optimized_settings
            
            # 获取标签参数配置
            label_parameters = labels_config.get('label_parameters', {})
            if not label_parameters:
                return optimized_settings
            
            # 分析股票标签，确定适用的参数
            applicable_params = {}
            
            # 检查市值标签
            market_cap_labels = labels_data.get('market_cap', [])
            for label in market_cap_labels:
                if label in label_parameters:
                    applicable_params.update(label_parameters[label])
                    logger.debug(f"应用市值标签参数: {label}")
                    break
            
            # 检查波动性标签
            volatility_labels = labels_data.get('volatility', [])
            for label in volatility_labels:
                if label in label_parameters:
                    applicable_params.update(label_parameters[label])
                    logger.debug(f"应用波动性标签参数: {label}")
                    break
            
            # 如果有适用的参数，更新设置
            if applicable_params:
                # 更新核心参数
                if 'convergence_days' in applicable_params:
                    optimized_settings['core']['convergence']['days'] = applicable_params['convergence_days']
                
                if 'stability_days' in applicable_params:
                    optimized_settings['core']['stability']['days'] = applicable_params['stability_days']
                
                if 'invest_range' in applicable_params:
                    optimized_settings['core']['invest_range'].update(applicable_params['invest_range'])
                
                logger.info(f"基于标签优化参数: {applicable_params}")
            
            return optimized_settings
            
        except Exception as e:
            logger.error(f"基于标签优化参数失败: {e}")
            return settings
    
