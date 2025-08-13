"""
Adjust Factor 模型
提供复权因子相关的特定方法
"""
from utils.db.db_model import BaseTableModel
from loguru import logger
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple


class AdjustFactor(BaseTableModel):
    """复权因子表自定义模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    def get_adj_factor(self, ts_code: str, type: str = 'qfq', date: str = None) -> Optional[Dict]:
        """
        获取指定日期的复权因子
        
        Args:
            ts_code: 股票代码
            type: 复权类型 ('qfq' 或 'hfq')
            date: 查询日期，如果为None则返回最新的因子
        """
        factor_type = type
        
        if date:
            # 查询指定日期之前最近的复权因子
            query = f"""
                SELECT {factor_type}, date, last_update
                FROM adj_factor 
                WHERE id = %s AND date <= %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (ts_code, date))
        else:
            # 查询最新的复权因子
            query = f"""
                SELECT {factor_type}, date, last_update
                FROM adj_factor 
                WHERE id = %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (ts_code,))
            
        if result:
            return {
                'type': type,
                'value': float(result[0][factor_type]),
                'date': result[0]['date'],
                'last_update': result[0]['last_update']
            }
        return None

    def get_all_adj_factors(self, ts_code: str) -> List[Dict]:
        query = """
            SELECT * 
            FROM adj_factor
            WHERE id = %s
            ORDER BY date DESC
        """
        return self.execute_raw_query(query, (ts_code,))
    
    def get_all_stocks_latest_update_dates(self) -> List[Dict]:
        """
        获取所有股票的复权因子更新状态
        只负责数据查询，不包含业务逻辑
        
        Returns:
            所有股票的更新状态列表，包含：
            - ts_code: 股票代码
            - last_factor_date: 最近的因子变化日期
            - last_update: 系统最后更新时间
        """
        try:
            # 查询每只股票的因子状态
            query = """
                SELECT MAX(date) AS last_factor_date, id, last_update
                FROM adj_factor 
                GROUP BY id
            """
            
            result = self.execute_raw_query(query)
            return result if result else []
            
        except Exception as e:
            logger.error(f"获取股票更新状态失败: {e}")
            return []
    

