#!/usr/bin/env python3
"""
标签计算器

职责：
- 实现各种标签的计算算法
- 提供标签计算的核心逻辑
- 支持不同维度的标签计算
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader


class LabelCalculator:
    """
    标签计算器
    
    职责：
    - 市值标签计算
    - 行业标签计算
    - 波动性标签计算
    - 成交量标签计算
    - 综合标签计算
    """
    
    # 标签分类映射
    LABEL_CATEGORIES = {
        'MARKET_CAP': {
            'LARGE_CAP': '大盘股',
            'MID_CAP': '中盘股', 
            'SMALL_CAP': '小盘股'
        },
        'INDUSTRY': {
            'GROWTH': '成长股',
            'VALUE': '价值股',
            'CYCLE': '周期股',
            'DEFENSIVE': '防御股'
        },
        'VOLATILITY': {
            'HIGH_VOL': '高波动',
            'MID_VOL': '中波动',
            'LOW_VOL': '低波动'
        },
        'VOLUME': {
            'HIGH_ACTIVE': '高活跃',
            'MID_ACTIVE': '中活跃',
            'LOW_ACTIVE': '低活跃'
        }
    }
    
    def __init__(self, db: DatabaseManager):
        """
        初始化标签计算器
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
        self.data_loader = DataLoader(db)
    
    def calculate_all_labels(self, stock_id: str, target_date: str) -> List[str]:
        """
        计算股票的所有标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)
            
        Returns:
            List[str]: 标签ID列表
        """
        labels = []
        
        try:
            # 计算市值标签
            market_cap_label = self.calculate_market_cap_label(stock_id, target_date)
            if market_cap_label:
                labels.append(market_cap_label)
            
            # 计算行业标签
            industry_label = self.calculate_industry_label(stock_id, target_date)
            if industry_label:
                labels.append(industry_label)
            
            # 计算波动性标签
            volatility_label = self.calculate_volatility_label(stock_id, target_date)
            if volatility_label:
                labels.append(volatility_label)
            
            # 计算成交量标签
            volume_label = self.calculate_volume_label(stock_id, target_date)
            if volume_label:
                labels.append(volume_label)
            
            logger.debug(f"计算标签完成: {stock_id}, {target_date}, {labels}")
            return labels
            
        except Exception as e:
            logger.error(f"计算标签失败: {stock_id}, {target_date}, {e}")
            return []
    
    def calculate_market_cap_label(self, stock_id: str, target_date: str) -> Optional[str]:
        """
        计算市值标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            str: 市值标签ID
        """
        try:
            # 获取目标日期的K线数据
            klines = self.data_loader.load_klines(stock_id, 'daily', adjust='qfq', as_dataframe=True)
            
            if klines.empty:
                return None
            
            # 找到目标日期或最近的数据
            target_dt = pd.to_datetime(target_date)
            available_data = klines[klines.index <= target_dt]
            
            if available_data.empty:
                return None
            
            latest_data = available_data.iloc[-1]
            
            # 获取市值（万元）
            market_cap = latest_data.get('total_market_value', 0)
            
            if market_cap == 0:
                return None
            
            # 根据市值分类
            if market_cap >= 1000000:  # 100亿
                return 'LARGE_CAP'
            elif market_cap >= 300000:  # 30亿
                return 'MID_CAP'
            else:
                return 'SMALL_CAP'
                
        except Exception as e:
            logger.error(f"计算市值标签失败: {stock_id}, {target_date}, {e}")
            return None
    
    def calculate_industry_label(self, stock_id: str, target_date: str) -> Optional[str]:
        """
        计算行业标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            str: 行业标签ID
        """
        try:
            # 获取股票基本信息
            stock_list_table = self.db.get_table_instance('stock_list')
            stock_info = stock_list_table.get_stock_by_id(stock_id)
            
            if not stock_info:
                return None
            
            industry = stock_info.get('industry', '').upper()
            
            # 根据行业分类
            if any(keyword in industry for keyword in ['科技', 'TECH', '软件', '电子', '通信']):
                return 'GROWTH'
            elif any(keyword in industry for keyword in ['银行', '保险', '地产', 'BANK', 'INSURANCE']):
                return 'VALUE'
            elif any(keyword in industry for keyword in ['钢铁', '煤炭', '化工', '有色金属', 'STEEL', 'COAL']):
                return 'CYCLE'
            elif any(keyword in industry for keyword in ['食品', '饮料', '公用事业', 'FOOD', 'UTILITY']):
                return 'DEFENSIVE'
            else:
                # 默认根据PE等指标判断
                return self._classify_by_financial_metrics(stock_id, target_date)
                
        except Exception as e:
            logger.error(f"计算行业标签失败: {stock_id}, {target_date}, {e}")
            return None
    
    def calculate_volatility_label(self, stock_id: str, target_date: str) -> Optional[str]:
        """
        计算波动性标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            str: 波动性标签ID
        """
        try:
            # 获取最近6个月的日线数据
            klines = self.data_loader.load_klines(stock_id, 'daily', adjust='qfq', as_dataframe=True)
            
            if klines.empty:
                return None
            
            # 找到目标日期或最近的数据
            target_dt = pd.to_datetime(target_date)
            available_data = klines[klines.index <= target_dt]
            
            if len(available_data) < 30:  # 至少需要30天数据
                return None
            
            # 取最近6个月的数据
            six_months_ago = target_dt - timedelta(days=180)
            recent_data = available_data[available_data.index >= six_months_ago]
            
            if len(recent_data) < 30:
                recent_data = available_data.tail(30)
            
            # 计算日收益率
            returns = recent_data['close'].pct_change().dropna()
            
            # 计算年化波动率
            volatility = returns.std() * np.sqrt(252)  # 年化
            
            # 根据波动率分类
            if volatility > 0.3:  # 30%
                return 'HIGH_VOL'
            elif volatility > 0.15:  # 15%
                return 'MID_VOL'
            else:
                return 'LOW_VOL'
                
        except Exception as e:
            logger.error(f"计算波动性标签失败: {stock_id}, {target_date}, {e}")
            return None
    
    def calculate_volume_label(self, stock_id: str, target_date: str) -> Optional[str]:
        """
        计算成交量标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            str: 成交量标签ID
        """
        try:
            # 获取最近3个月的日线数据
            klines = self.data_loader.load_klines(stock_id, 'daily', adjust='qfq', as_dataframe=True)
            
            if klines.empty:
                return None
            
            # 找到目标日期或最近的数据
            target_dt = pd.to_datetime(target_date)
            available_data = klines[klines.index <= target_dt]
            
            if len(available_data) < 20:  # 至少需要20天数据
                return None
            
            # 取最近3个月的数据
            three_months_ago = target_dt - timedelta(days=90)
            recent_data = available_data[available_data.index >= three_months_ago]
            
            if len(recent_data) < 20:
                recent_data = available_data.tail(20)
            
            # 计算平均成交金额（万元）
            avg_amount = recent_data['amount'].mean()
            
            # 根据成交金额分类
            if avg_amount > 50000:  # 5亿
                return 'HIGH_ACTIVE'
            elif avg_amount > 10000:  # 1亿
                return 'MID_ACTIVE'
            else:
                return 'LOW_ACTIVE'
                
        except Exception as e:
            logger.error(f"计算成交量标签失败: {stock_id}, {target_date}, {e}")
            return None
    
    def _classify_by_financial_metrics(self, stock_id: str, target_date: str) -> Optional[str]:
        """
        根据财务指标分类行业标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            str: 行业标签ID
        """
        try:
            # 获取目标日期的K线数据
            klines = self.data_loader.load_klines(stock_id, 'daily', adjust='qfq', as_dataframe=True)
            
            if klines.empty:
                return None
            
            # 找到目标日期或最近的数据
            target_dt = pd.to_datetime(target_date)
            available_data = klines[klines.index <= target_dt]
            
            if available_data.empty:
                return None
            
            latest_data = available_data.iloc[-1]
            
            # 获取PE、PB等指标
            pe_ratio = latest_data.get('pe', 0)
            pb_ratio = latest_data.get('pb', 0)
            
            # 根据财务指标分类
            if pe_ratio > 0 and pe_ratio < 20 and pb_ratio > 0 and pb_ratio < 2:
                return 'VALUE'  # 低PE低PB，价值股
            elif pe_ratio > 30 or pb_ratio > 5:
                return 'GROWTH'  # 高PE高PB，成长股
            else:
                return 'CYCLE'  # 其他情况，周期股
                
        except Exception as e:
            logger.error(f"根据财务指标分类失败: {stock_id}, {target_date}, {e}")
            return None
