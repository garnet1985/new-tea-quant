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
        return self.stock_list.load_active_stocks()
    
    def load_filtered_stock_list(
        self, 
        exclude_patterns: Optional[Dict[str, List[str]]] = None,
        order_by: str = 'id'
    ) -> List[Dict[str, Any]]:
        """
        加载过滤后的股票列表（排除ST、科创板等）
        
        默认过滤规则（参考 analyzer_settings.py）：
        - 排除 id 以 "688" 开头的（科创板）
        - 排除 name 以 "*ST"、"ST"、"退" 开头的（ST股票和退市股票）
        - 注意：北交所（BJ）不排除（根据用户要求）
        
        Args:
            exclude_patterns: 自定义排除规则（可选）
                {
                    "start_with": {
                        "id": ["688"],
                        "name": ["*ST", "ST", "退"]
                    },
                    "contains": {
                        "id": ["BJ"]  # 如果需要排除北交所，可以传入
                    }
                }
            order_by: 排序字段（默认 'id'）
            
        Returns:
            List[Dict]: 过滤后的股票列表
        """
        # 默认过滤规则
        default_exclude = {
            "start_with": {
                "id": ["688"],  # 科创板
                "name": ["*ST", "ST", "退"]  # ST股票和退市股票
            },
            "contains": {
                # 注意：北交所（BJ）不排除（根据用户要求）
            }
        }
        
        # 合并用户自定义规则
        if exclude_patterns:
            exclude = exclude_patterns.copy()
            # 合并 start_with
            if "start_with" in exclude_patterns:
                exclude["start_with"] = {
                    **default_exclude["start_with"],
                    **exclude_patterns["start_with"]
                }
            else:
                exclude["start_with"] = default_exclude["start_with"]
            # 合并 contains
            if "contains" in exclude_patterns:
                exclude["contains"] = {
                    **default_exclude["contains"],
                    **exclude_patterns["contains"]
                }
            else:
                exclude["contains"] = default_exclude["contains"]
        else:
            exclude = default_exclude
        
        # 加载所有活跃股票
        all_stocks = self.stock_list.load_active_stocks()
        
        # 应用过滤规则
        filtered_stocks = []
        for stock in all_stocks:
            stock_id = str(stock.get('id', ''))
            stock_name = str(stock.get('name', ''))
            
            # 检查是否应该排除
            should_exclude = False
            
            # 检查 start_with 规则
            for field, patterns in exclude.get("start_with", {}).items():
                value = stock_id if field == "id" else stock_name
                for pattern in patterns:
                    if value.startswith(pattern):
                        should_exclude = True
                        break
                if should_exclude:
                    break
            
            # 检查 contains 规则
            if not should_exclude:
                for field, patterns in exclude.get("contains", {}).items():
                    value = stock_id if field == "id" else stock_name
                    for pattern in patterns:
                        if pattern in value:
                            should_exclude = True
                            break
                    if should_exclude:
                        break
            
            if not should_exclude:
                filtered_stocks.append(stock)
        
        # 排序
        if order_by:
            try:
                filtered_stocks.sort(key=lambda x: x.get(order_by, ''))
            except Exception as e:
                logger.warning(f"排序失败，使用默认排序: {e}")
                filtered_stocks.sort(key=lambda x: x.get('id', ''))
        
        return filtered_stocks
    
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
    
    def save_stocks(self, stocks: List[Dict[str, Any]]) -> int:
        """
        批量保存股票列表（自动去重）
        
        Args:
            stocks: 股票数据列表
            
        Returns:
            影响的行数
        """
        return self.stock_list.save_stocks(stocks)
    
    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """
        批量保存K线数据（自动去重）
        
        Args:
            klines: K线数据列表
            
        Returns:
            影响的行数
        """
        return self.stock_kline.save_klines(klines)

