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

    def renew_index(self, stock_data: List[Dict[str, Any]]):
        """
        一次性更新股票指数：插入/更新活跃股票，标记未出现的股票为非活跃
        
        Args:
            stock_data: 已经格式化好的股票数据列表，包含id, name, industry, type, exchangeCenter, isAlive, lastUpdate等字段
        """
        if not stock_data:
            return
            
        # 第一步：使用父类的replace方法插入/更新活跃股票
        primary_keys = ['id']
        self.replace(stock_data, primary_keys)
        
        # 第二步：使用父类的update方法标记未出现的股票为非活跃
        active_stock_ids = [stock['id'] for stock in stock_data]
        if active_stock_ids:
            placeholders = ','.join(['%s'] * len(active_stock_ids))
            condition = f"id NOT IN ({placeholders}) AND isAlive = 1"
            params = tuple(active_stock_ids)
            
            update_data = {
                'isAlive': 0,
                'lastUpdate': stock_data[0]['lastUpdate']  # 使用第一条数据的lastUpdate
            }
            
            self.update(update_data, condition, params)


    def load_index(self, 
                   load_type: str = 'all',
                   industry: str = None,
                   stock_type: str = None,
                   exchange_center: str = None,
                   exclude_patterns: List[str] = None,
                   order_by: str = 'id') -> List[Dict[str, Any]]:
        """
        统一的股票指数加载方法，根据参数决定加载方式
        
        Args:
            load_type: 加载类型
                - 'all': 返回所有数据库记录
                - 'alive': 返回所有isAlive=1的记录
                - 'inactive': 返回所有isAlive=0的记录
            industry: 按行业筛选
            stock_type: 按股票类型筛选
            exchange_center: 按交易所筛选
            exclude_patterns: 排除的模式列表（如科创板等）
            order_by: 排序字段，默认按id排序
            
        Returns:
            List[Dict[str, Any]]: 股票数据列表
        """
        try:
            # 构建WHERE条件
            where_conditions = []
            params = []
            
            # 根据load_type添加isAlive条件
            if load_type == 'alive':
                where_conditions.append("isAlive = 1")
            elif load_type == 'inactive':
                where_conditions.append("isAlive = 0")
            # load_type == 'all' 时不添加isAlive条件
            
            # 添加行业筛选
            if industry:
                where_conditions.append("industry = %s")
                params.append(industry)
            
            # 添加股票类型筛选
            if stock_type:
                where_conditions.append("type = %s")
                params.append(stock_type)
            
            # 添加交易所筛选
            if exchange_center:
                where_conditions.append("exchangeCenter = %s")
                params.append(exchange_center)
            
            # 添加排除模式
            if exclude_patterns:
                for pattern in exclude_patterns:
                    where_conditions.append("id NOT LIKE %s")
                    params.append(pattern)
            
            # 构建最终的WHERE子句
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 使用基类的load方法
            return self.load(
                condition=where_clause,
                params=tuple(params),
                order_by=order_by
            )
            
        except Exception as e:
            logger.error(f"加载股票指数失败: {e}")
            return []
    
    # 便捷方法，保持向后兼容
    def load_all(self, order_by: str = 'id') -> List[Dict[str, Any]]:
        """返回所有数据库记录"""
        return self.load_index(load_type='all', order_by=order_by)
    
    def load_all_alive(self, order_by: str = 'id') -> List[Dict[str, Any]]:
        """返回所有活跃股票"""
        return self.load_index(load_type='alive', order_by=order_by)
    
    def load_all_by_industry(self, industry: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按行业返回股票"""
        return self.load_index(load_type='all', industry=industry, order_by=order_by)
    
    def load_all_by_type(self, stock_type: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按股票类型返回股票"""
        return self.load_index(load_type='all', stock_type=stock_type, order_by=order_by)
    
    def load_all_by_exchange_center(self, exchange_center: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按交易所返回股票"""
        return self.load_index(load_type='all', exchange_center=exchange_center, order_by=order_by)

    def load_all_exclude(self, exclude_patterns: List[str] = None, order_by: str = 'id') -> List[Dict[str, Any]]:
        return self.load_index(load_type='all', exclude_patterns=exclude_patterns, order_by=order_by)
    
    def load_name_by_id(self, stock_id: str):
        """根据股票ID加载股票名称"""
        stock = self.load_one("id = %s", (stock_id,))
        return stock['name'] if stock else None

    def load_name_by_ids(self, stock_ids: List[str]):
        """根据股票ID加载股票名称"""
        if not stock_ids:
            return {}
        
        # 构建IN查询的占位符
        placeholders = ','.join(['%s'] * len(stock_ids))
        stocks = self.load_many(f"id IN ({placeholders})", tuple(stock_ids))
        return {stock['id']: stock['name'] for stock in stocks}
