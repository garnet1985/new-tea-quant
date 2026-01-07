"""
MeanReversion 策略实现
均值回归策略 - 基于价格偏离均线的历史分位数进行交易
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from loguru import logger

from app.core.modules.analyzer.components.base_strategy import BaseStrategy
from app.core.modules.analyzer.components.entity.opportunity import Opportunity


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略
    
    核心思想：
    1. 股票价格不会长期偏离均线太远
    2. 使用历史分位数动态定义"极端"偏离水平
    3. 当偏离达到极端水平时进行反向交易
    """
    
    def __init__(self, db=None, is_verbose=False):
        # 先设置version，再调用父类__init__
        self.version = "1.0.0"
        super().__init__(
            db=db,
            is_verbose=is_verbose,
            name="MeanReversion",
            description="均值回归策略 - 基于价格偏离均线的历史分位数进行交易",
            key="MeanReversion",
            version="1.0.0"
        )
        if db is not None:
            super().initialize()
    
    @staticmethod
    def scan_opportunity(stock_info: Dict[str, Any], data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描投资机会
        
        Args:
            stock_info: 股票信息字典
            data: 股票的历史K线数据
            settings: 策略设置
            
        Returns:
            Optional[Dict]: 如果发现投资机会则返回机会字典，否则返回None
        """
        try:
            # 获取核心参数
            core_params = settings.get('core', {})
            ma_period = core_params.get('ma_period', 20)
            std_period = core_params.get('std_period', 20)
            quantile_period = core_params.get('quantile_period', 120)
            lower_quantile = core_params.get('lower_quantile', 0.05)
            
            # 检查数据长度
            signal_term = settings.get('klines', {}).get('signal_base_term')
            klines = data.get('klines', {}).get(signal_term, [])

            
            if len(klines) < quantile_period:
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(klines)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 计算均线
            df['ma'] = df['close'].rolling(window=ma_period).mean()
            
            # 计算标准差（波动性指标）
            df['std'] = df['close'].rolling(window=std_period).std()
            
            # 计算相对偏离率
            df['deviation'] = (df['close'] - df['ma']) / df['ma']
            
            # 计算历史分位数边界
            upper_quantile = core_params.get('upper_quantile', 0.95)
            df['lower_bound'] = df['deviation'].rolling(window=quantile_period).quantile(lower_quantile)
            df['upper_bound'] = df['deviation'].rolling(window=quantile_period).quantile(upper_quantile)
            
            # 获取最新数据
            latest = df.iloc[-1]
            
            # 检查是否有足够的数据
            if pd.isna(latest['lower_bound']):
                return None
            
            # 生成买入信号：当前偏离率低于历史5%分位数
            if latest['deviation'] < latest['lower_bound']:
                # 将pandas Series转换为字典格式
                latest_record = latest.to_dict()
                
                # 创建机会对象
                # 使用价格修正边界（用于处理滑点），而不是策略信号边界
                current_price = latest['close']
                opportunity = Opportunity(
                    stock=stock_info,
                    record_of_today=latest_record,
                    extra_fields={
                        'strategy_name': 'MeanReversion',
                        'signal_type': 'buy',
                        'deviation': latest['deviation'],
                        'signal_lower_bound': latest['lower_bound'],  # 策略信号边界
                        'signal_upper_bound': latest['upper_bound'],  # 策略信号边界
                        'ma_value': latest['ma'],
                        'current_price': current_price,
                        'volatility': latest['std'],
                        'deviation_percentile': (df['deviation'] < latest['deviation']).sum() / len(df) * 100,
                    },
                    lower_bound=latest['lower_bound'],
                    upper_bound=latest['upper_bound'],
                )
                
                return opportunity
            
            return None
            
        except Exception as e:
            logger.error(f"MeanReversion扫描机会时出错: {e}")
            return None

    @staticmethod
    def create_customized_take_profit_targets(investment: Dict[str, Any], record_of_today: Dict[str, Any], extra_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        创建自定义止盈目标 - 均值回归策略
        
        Args:
            investment: 投资对象
            record_of_today: 当前交易日记录
            extra_fields: 额外字段（包含上界分位数等信息）
            
        Returns:
            List[InvestmentTarget]: 止盈目标列表
        """
        from app.core.modules.analyzer.components.entity.target import InvestmentTarget
        
        return [
            InvestmentTarget(
                target_type=InvestmentTarget.TargetType.TAKE_PROFIT,
                start_record=record_of_today,
                stage={
                    'name': 'mean_reversion_take_profit',
                    'ratio': 0,  # 动态止盈，不设固定比例
                    'close_invest': True,
                },
                extra_fields=extra_fields,
                is_customized=True,
                priority=InvestmentTarget.TargetPriority.CUSTOMIZED_TAKE_PROFIT_BASE.value,
            )
        ]

    @staticmethod
    def is_customized_take_profit_target_complete(
        target: Any,  # InvestmentTarget object
        record_of_today: Dict[str, Any],
        required_data: Dict[str, Any],
        remaining_investment_ratio: float,
        settings: Dict[str, Any],
    ) -> Tuple[bool, float]:
        """
        自定义止盈逻辑 - 基于价格偏离均线的动态止盈
        
        止盈条件：
        1. 当价格偏离率回归到历史上界以上时止盈（回归完成）
        2. 或者当收益率达到20%时止盈（保护利润）
        
        Args:
            target: InvestmentTarget 对象
            record_of_today: 当前交易日记录
            required_data: 所需数据
            remaining_investment_ratio: 剩余投资比例
            settings: 策略设置
            
        Returns:
            (是否触发止盈, 更新后的剩余投资比例)
        """
        try:
            # 获取当前价格
            current_price = record_of_today['close']
            purchase_price = target.start_record_ref.get('close', 0)
            
            if purchase_price <= 0:
                return False, remaining_investment_ratio
            
            # 计算基础收益率
            current_roi = (current_price - purchase_price) / purchase_price
            
            # 获取K线数据
            klines = required_data.get('klines', [])
            if isinstance(klines, dict):
                signal_term = settings.get('klines', {}).get('signal_base_term', 'daily')
                klines = klines.get(signal_term, [])
            
            if not klines or len(klines) < 20:  # 需要足够的数据计算均线
                return False, remaining_investment_ratio
            
            # 计算当前偏离率
            df = pd.DataFrame(klines)
            df['ma'] = df['close'].rolling(window=20).mean()
            df['deviation'] = (df['close'] - df['ma']) / df['ma']
            
            latest = df.iloc[-1]
            current_deviation = latest['deviation']
            
            # 从 extra_fields 获取买入时的上界
            extra_fields = target.tracker.get('extra_fields', {})
            upper_bound = extra_fields.get('signal_upper_bound', 0.05)  # 默认5%上界
            
            # 检查是否触发止盈
            # 条件1: 价格回归到上界以上（均值回归完成）
            # 条件2: 收益率达到20%（保护利润）
            if current_deviation > upper_bound or current_roi > 0.20:
                logger.info(
                    f"均值回归止盈触发 | 当前偏离率: {current_deviation:.4f} | "
                    f"上界: {upper_bound:.4f} | 当前ROI: {current_roi:.2%}"
                )
                return True, remaining_investment_ratio
            
            return False, remaining_investment_ratio
            
        except Exception as e:
            logger.error(f"MeanReversion自定义止盈检查出错: {e}")
            return False, remaining_investment_ratio
