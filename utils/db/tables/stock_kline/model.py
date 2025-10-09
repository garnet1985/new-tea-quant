"""
Stock Kline 模型
提供股票K线相关的特定方法
"""
from typing import Any, Dict, List
from utils.db.db_model import BaseTableModel
from loguru import logger


class StockKlineModel(BaseTableModel):
    """股票K线表自定义模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    def get_all_k_lines_by_term(self, stock_id: str, term: str, order: str = 'ASC'):
        """
        获取某只股票某个term的所有K线数据
        
        Args:
            stock_id: 股票代码，如 '000001.SZ'
            term: K线周期，'daily', 'weekly', 'monthly'
            order: 排序方式，'ASC' 或 'DESC'
            
        Returns:
            List[Dict]: K线数据列表
        """
        return self.load("id = %s AND term = %s", (stock_id, term), order_by=f"date {order}")

    def get_most_recent_one_by_term(self, stock_id: str, term: str):
        """
        获取某只股票某个term的最新一条K线数据
        
        Args:
            stock_id: 股票代码
            term: K线周期
            
        Returns:
            Dict: 最新的K线记录
        """
        return self.load_one("id = %s AND term = %s", (stock_id, term), order_by="date DESC")
    
    def get_by_dates(self, stock_id: str, trade_dates: List[str], term: str = 'daily'):
        """
        根据日期列表获取K线数据
        
        Args:
            stock_id: 股票代码
            trade_dates: 日期列表，如 ['20250930', '20251001']
            term: K线周期
            
        Returns:
            List[Dict]: K线数据列表
        """
        if not trade_dates:
            return []
        
        # 构建 IN 查询的占位符
        placeholders = ','.join(['%s'] * len(trade_dates))
        condition = f"id = %s AND term = %s AND date IN ({placeholders})"
        
        # 构建参数：stock_id + term + 所有日期
        params = [stock_id, term] + trade_dates
        
        return self.load(condition, params, order_by="date")    
    
    def get_by_date(self, stock_id: str, trade_date: str, term: str = 'daily'):
        """
        获取某只股票某个日期的K线数据
        
        Args:
            stock_id: 股票代码
            trade_date: 交易日期
            term: K线周期
            
        Returns:
            Dict: K线记录
        """
        return self.load_one("id = %s AND term = %s AND date = %s", (stock_id, term, trade_date))

    def get_most_recent_k_lines_by_term(self, stock_id: str, term: str, limit: int) -> List[Dict[str, Any]]:
        """
        获取某只股票某个term的最近N条K线数据
        
        Args:
            stock_id: 股票代码
            term: K线周期
            limit: 获取的记录数
            
        Returns:
            List[Dict]: K线数据列表（按日期升序）
        """
        try:
            # 一个query搞定：直接获取最新的K线数据
            condition = "id = %s AND term = %s"
            params = (stock_id, term)
            
            # 使用DESC + LIMIT获取最近的N条数据，然后按时间升序返回
            recent_records = self.load(condition, params, order_by="date DESC", limit=limit)
            
            # 对结果按日期升序排列
            return sorted(recent_records, key=lambda x: x['date'])
            
        except Exception as e:
            logger.error(f"获取最新K线数据失败: {e}")
            return []
    
    def get_every_stock_latest_update_by_term(self, stock_ids: List[str], term: str = 'daily') -> Dict[str, str]:
        """
        获取每只股票在指定周期下的最新更新日期
        
        业务逻辑：
        - 查询指定股票列表中每只股票在指定周期(term)下的最新数据日期
        - 只返回有数据的股票，没有数据的股票不会出现在结果中
        - 用于判断哪些股票需要更新数据
        
        Args:
            stock_ids: 股票代码列表，如 ['000001.SZ', '000002.SZ']
            term: 数据周期，支持 'daily', 'weekly', 'monthly'，默认为 'daily'
            
        Returns:
            Dict[str, str]: 股票代码到最新日期的映射
            例如: {'000001.SZ': '20250930', '000002.SZ': '20250930'}
            注意：只有存在数据的股票才会出现在结果中
        """
        if not stock_ids:
            logger.debug("股票代码列表为空，返回空结果")
            return {}
        
        try:
            # 构建安全的 IN 查询
            placeholders = ','.join(['%s'] * len(stock_ids))
            query = f"""
                SELECT id, MAX(date) as latest_date 
                FROM {self.table_name} 
                WHERE id IN ({placeholders}) AND term = %s
                GROUP BY id
                ORDER BY id
            """
            
            # 参数：股票代码列表 + term
            params = stock_ids + [term]
            
            # 执行查询
            results = self.execute_raw_query(query, params)
            
            # 创建股票代码到最新日期的映射
            latest_dates = {row['id']: row['latest_date'] for row in results}
            return latest_dates
                
        except Exception as e:
            logger.error(f"获取股票最新更新日期失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {}

