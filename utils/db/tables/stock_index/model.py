"""
Stock Index 自定义模型
提供股票指数相关的特定方法
"""
from utils.db.db_config import DB_CONFIG
from utils.db.db_model import BaseTableModel
from typing import List, Dict, Any, Optional
from loguru import logger


class StockIndexModel(BaseTableModel):
    """股票指数表自定义模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    def get_index(self, exclude_expressions: List[str] = None) -> List[Dict[str, Any]]:
        """获取股票指数"""
        idx = self.load_many()
        if exclude_expressions:
            for exclude_expression in exclude_expressions:
                idx = [stock for stock in idx if not exclude_expression.match(stock['id'])]
        return idx

    def get_stock_by_id(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """根据股票ID获取股票信息"""
        return self.load_one("id = %s", (stock_id,))
    
    def get_stocks_by_industry(self, industry: str) -> List[Dict[str, Any]]:
        """根据行业获取股票列表"""
        return self.load_many("industry = %s", (industry,))
    
    def get_alive_stocks(self) -> List[Dict[str, Any]]:
        """获取所有活跃股票"""
        return self.load_many("isAlive = 1")
    
    def update_stock_status(self, stock_id: str, is_alive: bool) -> int:
        """更新股票状态"""
        return self.update(
            {"isAlive": 1 if is_alive else 0},
            "id = %s",
            (stock_id,)
        )
    
    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索股票（按ID或名称）"""
        return self.load_many(
            "id LIKE %s OR name LIKE %s",
            (f"%{keyword}%", f"%{keyword}%")
        )
    
    def get_stock_index(self, ts_code_exclude_list = DB_CONFIG['stock_index']['ts_code_exclude_list']) -> List[Dict[str, Any]]:
        """获取股票列表，排除科创板等"""
        try:
            # 构建动态的 WHERE 条件
            where_conditions = []
            params = []
            
            for exclude_pattern in ts_code_exclude_list:
                where_conditions.append("id NOT LIKE %s")
                params.append(exclude_pattern)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 使用基类的 load 方法，指定需要的字段和排序
            return self.load(
                condition=where_clause,
                params=tuple(params),
                order_by="id"
            )
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []

    def get_all_k_lines_by_term(self, stock_id: str, term: str, order_by: str = 'ASC'):
        # 使用基类的 load 方法
        return self.load("id = %s AND term = %s", (stock_id, term), order_by=f"date {order_by}")

    def get_most_recent_one_by_term(self, stock_id: str, term: str):
        # 使用基类的 load_one 方法
        return self.load_one("id = %s AND term = %s ORDER BY date DESC LIMIT 1", (stock_id, term))