#!/usr/bin/env python3
"""
Waly 策略 - 寻找市盈率小于 1/国债利率*2 and asset debt ratio < 0.5 的股票
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from ...components.base_strategy import BaseStrategy
from ...components.entity.opportunity import Opportunity

class Waly(BaseStrategy):
    """Waly 策略实现"""
    
    def __init__(self, db=None, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="Waly",
            key="Waly",
            version="1.0.0"
        )
        if db is not None:
            super().initialize()

    @staticmethod
    def _get_latest_record_by_date(records: List[Dict], target_date: str, date_field: str = 'date') -> Optional[Dict]:
        """
        从记录列表中找到小于等于目标日期的最近一条记录（向前fallback）
        
        Args:
            records: 记录列表，应该按日期排序
            target_date: 目标日期（YYYYMMDD格式）
            date_field: 日期字段名
            
        Returns:
            Optional[Dict]: 找到的记录，如果没有则返回None
        """
        if not records:
            return None
        
        # 从后往前查找，找到第一个小于等于目标日期的记录
        for record in reversed(records):
            record_date = record.get(date_field, '')
            if record_date and record_date <= target_date:
                return record
        
        # 如果都没找到，返回第一条记录（作为最后的fallback）
        return records[0] if records else None
    
    @staticmethod
    def _get_latest_quarter_record(records: List[Dict], target_date: str) -> Optional[Dict]:
        """
        从季度记录列表中找到小于等于目标日期的最近一条记录
        
        Args:
            records: 季度记录列表，格式为YYYYQ[1-4]
            target_date: 目标日期（YYYYMMDD格式）
            
        Returns:
            Optional[Dict]: 找到的记录，如果没有则返回None
        """
        if not records:
            return None
        
        # 将目标日期转换为季度格式
        year = target_date[:4]
        month = int(target_date[4:6])
        target_quarter = f"{year}Q{(month - 1) // 3 + 1}"
        
        # 从后往前查找
        for record in reversed(records):
            quarter = record.get('quarter', '')
            if quarter and quarter <= target_quarter:
                return record
        
        # 如果都没找到，返回第一条记录
        return records[0] if records else None

    @staticmethod
    def scan_opportunity(stock_info: Dict[str, Any], data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描单只股票的投资机会
        
        Args:
            stock_info: 股票信息字典
            data: 包含klines、macro、corporate_finance等数据的字典
            settings: 策略设置
            
        Returns:
            Optional[Dict]: 如果发现投资机会则返回Opportunity对象，否则返回None
        """
        try:
            # 获取日线K线数据
            daily_klines = data.get('klines', {}).get('daily', [])
            if not daily_klines:
                return None
            
            # 获取最新K线记录
            latest_kline = daily_klines[-1]
            current_date = latest_kline.get('date', '')
            
            if not current_date:
                return None
            
            # 获取PE（市盈率）
            pe = latest_kline.get('pe', 0) or 0
            if pe <= 0:
                return None
            
            # 获取债券利率（优先使用Shibor一年期，如果没有则使用LPR一年期）
            bond_rate = 0
            shibor_data = data.get('macro', {}).get('shibor', [])
            if shibor_data:
                # 使用向前fallback找到最近的有效Shibor记录
                latest_shibor = Waly._get_latest_record_by_date(shibor_data, current_date, 'date')
                if latest_shibor:
                    bond_rate = latest_shibor.get('one_year', 0) or 0
            
            if bond_rate <= 0:
                # 如果没有Shibor，尝试使用LPR一年期
                lpr_data = data.get('macro', {}).get('lpr', [])
                if lpr_data:
                    # 使用向前fallback找到最近的有效LPR记录
                    latest_lpr = Waly._get_latest_record_by_date(lpr_data, current_date, 'date')
                    if latest_lpr:
                        bond_rate = latest_lpr.get('lpr_1_y', 0) or 0
            
            if bond_rate <= 0:
                # 详细日志，帮助调试
                shibor_count = len(data.get('macro', {}).get('shibor', []))
                lpr_count = len(data.get('macro', {}).get('lpr', []))
                logger.warning(
                    f"无法获取债券利率数据，股票: {stock_info.get('id')}, 日期: {current_date}, "
                    f"Shibor数据: {shibor_count}条, LPR数据: {lpr_count}条"
                )
                return None
            
            # 将百分比转换为小数（LPR和Shibor都是百分比，如3.45表示3.45%）
            bond_rate = bond_rate / 100.0
            
            # 检查PE条件
            if not Waly.is_PE_reached_condition(pe, bond_rate):
                return None
            
            # 获取资产负债率（从企业财务数据中获取）
            asset_debt_ratio = 0
            solvency_data = data.get('corporate_finance', {}).get('solvency', [])
            if solvency_data:
                # 使用向前fallback找到最近的有效季度财务数据
                latest_solvency = Waly._get_latest_quarter_record(solvency_data, current_date)
                if latest_solvency:
                    asset_debt_ratio = latest_solvency.get('debt_to_assets', 0) or 0
                    # 注意：debt_to_assets在数据库中可能是百分比形式（如91.318表示91.318%），需要转换为小数
                    if asset_debt_ratio > 1:
                        asset_debt_ratio = asset_debt_ratio / 100.0
            
            # 检查资产负债率条件
            if not Waly.is_asset_debt_ratio_reached_condition(asset_debt_ratio):
                return None
            
            # 创建投资机会
            return Opportunity(
                stock=stock_info,
                record_of_today=latest_kline,
                extra_fields={
                    'pe': pe,
                    'bond_rate': bond_rate,
                    'asset_debt_ratio': asset_debt_ratio,
                }
            )
            
        except Exception as e:
            logger.error(f"Waly策略扫描机会失败 {stock_info.get('id')}: {e}")
            return None

    @staticmethod
    def is_PE_reached_condition(pe: float, bond_rate: float) -> bool:
        """
        检查PE是否满足条件：PE < 1 / bond_rate * 2
        
        Args:
            pe: 市盈率
            bond_rate: 债券利率（小数形式，如0.0345表示3.45%）
            
        Returns:
            bool: 是否满足条件
        """
        if bond_rate <= 0:
            return False
        return pe < 1 / bond_rate * 2

    @staticmethod
    def is_asset_debt_ratio_reached_condition(asset_debt_ratio: float) -> bool:
        """
        检查资产负债率是否满足条件：asset_debt_ratio < 0.5
        
        Args:
            asset_debt_ratio: 资产负债率（小数形式，如0.3表示30%）
            
        Returns:
            bool: 是否满足条件
        """
        if asset_debt_ratio <= 0:
            # 如果没有数据，默认不满足条件
            return False
        return asset_debt_ratio < 0.5