#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
市值规模标签计算器
"""

from typing import Optional
from loguru import logger
from .base_calculator import BaseLabelCalculator
from .label_mapping import LabelMapping


class MarketCapLabelCalculator(BaseLabelCalculator):
    """市值规模标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'market_cap'
    
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算市值规模标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            str: 标签ID (large_cap/mid_cap/small_cap)
        """
        try:
            # 获取股票K线数据
            klines = self.data_loader.load_klines(stock_id, start_date=target_date, end_date=target_date)
            
            if not klines or len(klines) == 0:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据")
                return None
            
            # 获取最新的市值数据
            latest_kline = klines[-1]
            market_cap = latest_kline.get('total_market_value', 0)
            
            if market_cap <= 0:
                logger.warning(f"{stock_id} 在 {target_date} 的市值数据无效: {market_cap}")
                return None
            
            # 根据市值确定标签
            if market_cap >= LabelMapping.MARKET_CAP_LABELS['large_cap']['threshold']:
                return 'large_cap'
            elif market_cap >= LabelMapping.MARKET_CAP_LABELS['mid_cap']['threshold_min']:
                return 'mid_cap'
            else:
                return 'small_cap'
                
        except Exception as e:
            logger.error(f"计算市值标签失败 {stock_id} {target_date}: {e}")
            return None


class IndustryLabelCalculator(BaseLabelCalculator):
    """行业分类标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'industry'
    
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算行业分类标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            str: 标签ID (finance/technology/consumer等)
        """
        try:
            # 获取股票基本信息
            stock_info = self.data_loader.get_stock_info(stock_id)
            
            if not stock_info:
                logger.warning(f"无法获取 {stock_id} 的股票信息")
                return None
            
            industry = stock_info.get('industry', '').strip()
            
            if not industry:
                logger.warning(f"{stock_id} 的行业信息为空")
                return None
            
            # 根据行业匹配标签
            for label_id, label_def in LabelMapping.INDUSTRY_LABELS.items():
                industries = label_def.get('industries', [])
                for industry_keyword in industries:
                    if industry_keyword in industry:
                        return label_id
            
            # 如果没有匹配到，返回默认标签
            logger.info(f"{stock_id} 的行业 {industry} 未匹配到具体分类，使用默认分类")
            return 'manufacturing'  # 默认归类为制造业
            
        except Exception as e:
            logger.error(f"计算行业标签失败 {stock_id} {target_date}: {e}")
            return None


class VolatilityLabelCalculator(BaseLabelCalculator):
    """波动性标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'volatility'
    
    def calculate_label(self, stock_id: str, target_date: str, lookback_days: int = 30, **kwargs) -> Optional[str]:
        """
        计算波动性标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            lookback_days: 回望天数，默认30天
            
        Returns:
            str: 标签ID (high_volatility/medium_volatility/low_volatility)
        """
        try:
            # 计算回望开始日期
            from datetime import datetime, timedelta
            target_datetime = datetime.strptime(target_date, '%Y%m%d')
            start_datetime = target_datetime - timedelta(days=lookback_days)
            start_date = start_datetime.strftime('%Y%m%d')
            
            # 获取历史K线数据
            klines = self.data_loader.load_klines(stock_id, start_date=start_date, end_date=target_date)
            
            if not klines or len(klines) < 10:  # 至少需要10天数据
                logger.warning(f"无法获取 {stock_id} 足够的历史数据来计算波动性")
                return None
            
            # 计算收益率
            closes = [k['close'] for k in klines if k['close'] > 0]
            if len(closes) < 2:
                logger.warning(f"{stock_id} 的有效价格数据不足")
                return None
            
            # 计算日收益率
            returns = []
            for i in range(1, len(closes)):
                if closes[i-1] > 0:
                    daily_return = (closes[i] - closes[i-1]) / closes[i-1]
                    returns.append(daily_return)
            
            if len(returns) < 5:  # 至少需要5个收益率数据点
                logger.warning(f"{stock_id} 的收益率数据点不足")
                return None
            
            # 计算波动率（年化）
            import numpy as np
            volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
            
            # 根据波动率确定标签
            if volatility >= LabelMapping.VOLATILITY_LABELS['high_volatility']['threshold']:
                return 'high_volatility'
            elif volatility >= LabelMapping.VOLATILITY_LABELS['medium_volatility']['threshold_min']:
                return 'medium_volatility'
            else:
                return 'low_volatility'
                
        except Exception as e:
            logger.error(f"计算波动性标签失败 {stock_id} {target_date}: {e}")
            return None


class VolumeLabelCalculator(BaseLabelCalculator):
    """成交量标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'volume'
    
    def calculate_label(self, stock_id: str, target_date: str, lookback_days: int = 30, **kwargs) -> Optional[str]:
        """
        计算成交量标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            lookback_days: 回望天数，默认30天
            
        Returns:
            str: 标签ID (high_volume/medium_volume/low_volume)
        """
        try:
            # 计算回望开始日期
            from datetime import datetime, timedelta
            target_datetime = datetime.strptime(target_date, '%Y%m%d')
            start_datetime = target_datetime - timedelta(days=lookback_days)
            start_date = start_datetime.strftime('%Y%m%d')
            
            # 获取历史K线数据
            klines = self.data_loader.load_klines(stock_id, start_date=start_date, end_date=target_date)
            
            if not klines or len(klines) < 10:
                logger.warning(f"无法获取 {stock_id} 足够的历史数据来计算成交量比率")
                return None
            
            # 计算成交量比率
            volumes = [k['volume'] for k in klines if k['volume'] > 0]
            if len(volumes) < 2:
                logger.warning(f"{stock_id} 的有效成交量数据不足")
                return None
            
            # 计算平均成交量
            avg_volume = sum(volumes) / len(volumes)
            
            # 获取最新成交量
            latest_volume = volumes[-1]
            
            # 计算成交量比率
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
            
            # 根据成交量比率确定标签
            if volume_ratio >= LabelMapping.VOLUME_LABELS['high_volume']['threshold']:
                return 'high_volume'
            elif volume_ratio >= LabelMapping.VOLUME_LABELS['medium_volume']['threshold_min']:
                return 'medium_volume'
            else:
                return 'low_volume'
                
        except Exception as e:
            logger.error(f"计算成交量标签失败 {stock_id} {target_date}: {e}")
            return None


class FinancialLabelCalculator(BaseLabelCalculator):
    """财务指标标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'financial'
    
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算财务指标标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            str: 标签ID (high_pe/medium_pe/low_pe等)
        """
        try:
            # 获取股票K线数据
            klines = self.data_loader.load_klines(stock_id, start_date=target_date, end_date=target_date)
            
            if not klines or len(klines) == 0:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据")
                return None
            
            # 获取最新的财务指标数据
            latest_kline = klines[-1]
            pe_ratio = latest_kline.get('pe', 0)
            pb_ratio = latest_kline.get('pb', 0)
            
            # 优先返回PE标签
            if pe_ratio > 0:
                if pe_ratio >= LabelMapping.FINANCIAL_LABELS['high_pe']['threshold']:
                    return 'high_pe'
                elif pe_ratio >= LabelMapping.FINANCIAL_LABELS['medium_pe']['threshold_min']:
                    return 'medium_pe'
                else:
                    return 'low_pe'
            
            # 如果PE无效，使用PB
            elif pb_ratio > 0:
                if pb_ratio >= LabelMapping.FINANCIAL_LABELS['high_pb']['threshold']:
                    return 'high_pb'
                elif pb_ratio >= LabelMapping.FINANCIAL_LABELS['medium_pb']['threshold_min']:
                    return 'medium_pb'
                else:
                    return 'low_pb'
            
            else:
                logger.warning(f"{stock_id} 在 {target_date} 的财务指标数据无效")
                return None
                
        except Exception as e:
            logger.error(f"计算财务标签失败 {stock_id} {target_date}: {e}")
            return None
