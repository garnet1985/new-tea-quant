#!/usr/bin/env python3
"""
ScanDateResolver - 扫描日期解析器

职责：
- 根据配置决定扫描日期（strict vs non-strict）
- 返回扫描日期和该日期有 K 线的股票列表
"""

from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScanDateResolver:
    """扫描日期解析器"""
    
    data_manager: any  # DataManager 实例
    
    def resolve_scan_date(
        self,
        use_strict: bool
    ) -> tuple[str, List[str]]:
        """
        解析扫描日期和股票列表
        
        Args:
            use_strict: 是否严格模式
                - True: 使用 CalendarService.get_latest_completed_trading_date()
                - False: 使用 DB 中最新 K 线日期
        
        Returns:
            (scan_date, stock_ids): 扫描日期（YYYYMMDD）和股票 ID 列表
        
        Raises:
            ValueError: 如果无法解析日期或没有股票数据
        """
        if use_strict:
            return self._resolve_strict_date()
        else:
            return self._resolve_non_strict_date()
    
    def _resolve_strict_date(self) -> tuple[str, List[str]]:
        """严格模式：使用最新已完成交易日"""
        try:
            # 获取最新已完成交易日
            scan_date = self.data_manager.service.calendar.get_latest_completed_trading_date()
            
            if not scan_date:
                raise ValueError(
                    "[ScanDateResolver] 无法获取最新已完成交易日，"
                    "请检查 CalendarService 是否正常工作"
                )
            
            logger.info(f"[ScanDateResolver] 严格模式：扫描日期 = {scan_date}")
            
            # 获取该日期有 K 线的股票列表
            stock_ids = self._get_stocks_with_kline(scan_date)
            
            if not stock_ids:
                raise ValueError(
                    f"[ScanDateResolver] 日期 {scan_date} 没有找到任何股票的 K 线数据"
                )
            
            logger.info(f"[ScanDateResolver] 找到 {len(stock_ids)} 只股票有 K 线数据")
            
            return scan_date, stock_ids
            
        except Exception as e:
            logger.error(f"[ScanDateResolver] 严格模式解析失败: {e}")
            raise
    
    def _resolve_non_strict_date(self) -> tuple[str, List[str]]:
        """非严格模式：使用 DB 中最新 K 线日期"""
        try:
            # 查询 DB 中最新 K 线日期
            kline_model = self.data_manager.get_table('stock_kline')
            if not kline_model:
                raise ValueError("[ScanDateResolver] 无法获取 stock_kline model")
            
            # 查询 MAX(date) FROM stock_kline WHERE term = 'daily'
            sql = """
                SELECT MAX(date) as max_date
                FROM stock_kline
                WHERE term = 'daily'
            """
            results = self.data_manager.db.execute_sync_query(sql)
            
            if not results or not results[0].get('max_date'):
                raise ValueError(
                    "[ScanDateResolver] DB 中没有找到任何 K 线数据"
                )
            
            scan_date = str(results[0]['max_date'])
            logger.info(f"[ScanDateResolver] 非严格模式：扫描日期 = {scan_date} (DB 最新)")
            
            # 获取该日期有 K 线的股票列表
            stock_ids = self._get_stocks_with_kline(scan_date)
            
            if not stock_ids:
                raise ValueError(
                    f"[ScanDateResolver] 日期 {scan_date} 没有找到任何股票的 K 线数据"
                )
            
            logger.info(f"[ScanDateResolver] 找到 {len(stock_ids)} 只股票有 K 线数据")
            
            return scan_date, stock_ids
            
        except Exception as e:
            logger.error(f"[ScanDateResolver] 非严格模式解析失败: {e}")
            raise
    
    def _get_stocks_with_kline(self, date: str) -> List[str]:
        """
        获取指定日期有 K 线的股票列表
        
        Args:
            date: 日期（YYYYMMDD）
        
        Returns:
            股票 ID 列表
        """
        kline_model = self.data_manager.get_table('stock_kline')
        if not kline_model:
            return []
        
        # 查询该日期所有股票的 K 线
        klines = kline_model.load_by_date(date)
        
        # 提取股票 ID（去重）
        stock_ids = list(set([k['id'] for k in klines if k.get('id')]))
        
        return sorted(stock_ids)
