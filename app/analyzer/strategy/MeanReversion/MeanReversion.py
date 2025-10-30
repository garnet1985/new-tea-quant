"""
MeanReversion 策略实现
均值回归策略 - 基于价格偏离均线的历史分位数进行交易
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from loguru import logger

from app.analyzer.components.base_strategy import BaseStrategy


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
            key="MR"
        )
    
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
                opportunity = BaseStrategy.create_opportunity(
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
                    }
                )
                
                return opportunity
            
            return None
            
        except Exception as e:
            logger.error(f"MeanReversion扫描机会时出错: {e}")
            return None

    @staticmethod
    def should_take_profit(stock_info: Dict[str, Any], record_of_today: Dict[str, Any], investment: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        自定义止盈逻辑 - 基于价格偏离均线的动态止盈
        
        Args:
            stock_info: 股票信息
            record_of_today: 当前交易日记录
            investment: 投资对象
            required_data: 所需数据
            settings: 策略设置
            
        Returns:
            (是否触发止盈, 更新后的投资对象)
        """
        try:
            # 获取当前价格
            current_price = record_of_today['close']
            purchase_price = investment['purchase_price']
            
            # 计算基础收益率
            current_roi = (current_price - purchase_price) / purchase_price
            
            # 获取K线数据
            klines = required_data.get('klines', [])
            if isinstance(klines, dict):
                signal_term = settings.get('klines', {}).get('signal_base_term', 'daily')
                klines = klines.get(signal_term, [])
            elif isinstance(klines, list):
                pass
            else:
                return False, investment
            
            if len(klines) < 20:  # 需要足够的数据计算均线
                return False, investment
            
            # 计算当前偏离率
            df = pd.DataFrame(klines)
            df['ma'] = df['close'].rolling(window=20).mean()
            df['deviation'] = (df['close'] - df['ma']) / df['ma']
            
            latest = df.iloc[-1]
            current_deviation = latest['deviation']
            
            # 动态止盈：当价格偏离率高于历史上界时止盈
            # 或者当收益率达到一定阈值时止盈
            upper_bound = latest.get('upper_bound', 0.05)  # 默认5%上界
            
            # 检查是否触发止盈
            if current_deviation > upper_bound or current_roi > 0.20:  # 20%止盈
                # 使用BaseStrategy的结算方法
                investment = BaseStrategy.to_settled_investment(
                    investment=investment,
                    exit_price=current_price,
                    exit_date=record_of_today['date'],
                    sell_ratio=1.0,
                    target_type="customized_take_profit"
                )
                return True, investment
            return False, investment
            
        except Exception as e:
            logger.error(f"MeanReversion自定义止盈检查出错: {e}")
            return False, investment
