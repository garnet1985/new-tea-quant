"""
股票数据服务（StockDataService）

职责：
- 封装股票相关的跨表查询和数据组装
- 提供领域级的业务方法

涉及的表：
- stock_list: 股票列表
- stock_kline: K线数据
- stock_labels: 股票标签
- adj_factor: 复权因子
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from .. import BaseDataService


class StockDataService(BaseDataService):
    """股票数据服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化股票数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model（通过 DataManager，自动绑定默认 db）
        self.stock_list = data_manager.get_model('stock_list')
        self.stock_kline = data_manager.get_model('stock_kline')
        self.stock_labels = data_manager.get_model('stock_labels')
        self.adj_factor = data_manager.get_model('adj_factor')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from utils.db import DatabaseManager
        self.db = DatabaseManager.get_default()
    
    # ==================== 股票基础信息 ====================
    
    def load_stock_info(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载股票基本信息
        
        Args:
            stock_id: 股票代码
            
        Returns:
            股票信息字典，如果不存在返回 None
        """
        return self.stock_list.load_one("id = %s", (stock_id,))
    
    def load_all_stocks(self) -> List[Dict[str, Any]]:
        """
        加载所有股票列表
        
        Returns:
            股票列表
        """
        return self.stock_list.load(order_by="id ASC")
    
    # ==================== K线数据 ====================
    
    def load_kline_series(
        self, 
        stock_id: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载K线序列
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            K线数据列表
        """
        if start_date and end_date:
            return self.stock_kline.load_by_date_range(stock_id, start_date, end_date)
        elif start_date:
            return self.stock_kline.load(
                "id = %s AND date >= %s",
                (stock_id, start_date),
                order_by="date ASC"
            )
        elif end_date:
            return self.stock_kline.load(
                "id = %s AND date <= %s",
                (stock_id, end_date),
                order_by="date ASC"
            )
        else:
            return self.stock_kline.load_by_stock(stock_id)
    
    def load_latest_kline(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载最新K线
        
        Args:
            stock_id: 股票代码
            
        Returns:
            最新K线数据，如果不存在返回 None
        """
        return self.stock_kline.load_latest(stock_id)
    
    def load_kline_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        加载指定日期的所有股票K线
        
        Args:
            date: 日期（格式：YYYYMMDD）
            
        Returns:
            K线数据列表
        """
        return self.stock_kline.load_by_date(date)
    
    # ==================== 跨表查询（SQL JOIN）====================
    
    def load_stock_with_latest_kline(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载股票信息 + 最新K线（SQL JOIN）
        
        Args:
            stock_id: 股票代码
            
        Returns:
            包含股票信息和最新K线的字典，如果不存在返回 None
        """
        sql = """
        SELECT 
            s.*,
            k.date as kline_date,
            k.open, k.high, k.low, k.close, k.volume, k.amount
        FROM stock_list s
        LEFT JOIN stock_kline k ON s.id = k.id
        WHERE s.id = %s
        ORDER BY k.date DESC
        LIMIT 1
        """
        results = self.db.execute_sync_query(sql, (stock_id,))
        return results[0] if results else None
    
    def load_stocks_with_kline_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        加载指定日期的所有股票信息 + K线（SQL JOIN）
        
        Args:
            date: 日期（格式：YYYYMMDD）
            
        Returns:
            股票信息 + K线数据列表
        """
        sql = """
        SELECT 
            s.*,
            k.open, k.high, k.low, k.close, k.volume, k.amount
        FROM stock_list s
        INNER JOIN stock_kline k ON s.id = k.id
        WHERE k.date = %s
        ORDER BY s.id ASC
        """
        return self.db.execute_sync_query(sql, (date,))
    
    def load_stock_with_labels(
        self, 
        stock_id: str, 
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载股票信息 + 标签（SQL JOIN）
        
        Args:
            stock_id: 股票代码
            date: 日期（可选，如果提供则只查询该日期的标签）
            
        Returns:
            包含股票信息和标签列表的字典
        """
        # 先获取股票信息
        stock_info = self.load_stock_info(stock_id)
        if not stock_info:
            return {}
        
        # 查询标签
        if date:
            labels = self.stock_labels.load(
                "id = %s AND date = %s",
                (stock_id, date)
            )
        else:
            labels = self.stock_labels.load("id = %s", (stock_id,))
        
        stock_info['labels'] = labels
        return stock_info
    
    # ==================== 批量操作 ====================
    
    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """
        批量保存K线数据（自动去重）
        
        Args:
            klines: K线数据列表
            
        Returns:
            影响的行数
        """
        return self.stock_kline.save_klines(klines)

