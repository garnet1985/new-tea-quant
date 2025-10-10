"""
Stock Index 自定义模型
提供股票指数相关的特定方法
"""
from utils.db.db_config import DB_CONFIG
from app.analyzer.analyzer_settings import conf
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
            condition = f"id NOT IN ({placeholders}) AND is_alive = 1"
            params = tuple(active_stock_ids)
            
            update_data = {
                'is_alive': 0,
                'last_update': stock_data[0]['last_update']  # 使用第一条数据的lastUpdate
            }
            
            self.update(update_data, condition, params)


    def load_index(self, 
                   load_type: str = 'alive',
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
                where_conditions.append("is_alive = 1")
            elif load_type == 'inactive':
                where_conditions.append("is_alive = 0")
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
                where_conditions.append("exchange_center = %s")
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
        return self.load_index(load_type='alive', industry=industry, order_by=order_by)
    
    def load_all_by_type(self, stock_type: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按股票类型返回股票"""
        return self.load_index(load_type='alive', stock_type=stock_type, order_by=order_by)
    
    def load_all_by_exchange_center(self, exchange_center: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按交易所返回股票"""
        return self.load_index(load_type='alive', exchange_center=exchange_center, order_by=order_by)
    
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
    
    def load_latest_last_update(self) -> Optional[str]:
        # 使用基类的load_one方法，按lastUpdate降序排序取第一条
        latest_record = self.load_one("1=1", order_by="lastUpdate DESC")
        return latest_record.get('last_update') if latest_record else None

    def load_filtered_index(self, exclude_patterns: Optional[Dict[str, List[Any]]] = None, order_by: str = 'id') -> List[Dict[str, Any]]:
        """
        返回默认可用股票集合：
        - 只加载 is_alive =1
        - 通用排除语法（来自 analyzer_settings.conf['stock_idx']['exclude']）：
            exclude = {
                [how_to_exclude]: {  # start_with | contains | end_with | equals | in
                    [which_field]: [keywords]
                }
            }
          若 which_field 不存在于表字段，则忽略
        - 允许传入 exclude_patterns（同上结构）覆盖/追加默认规则
        """
        try:
            # 基础条件：仅活跃
            where_conditions = ["is_alive = 1"]
            params: List[Any] = []

            # 从设置读取通用 exclude 配置
            default_exclude = (conf.get('stock_idx', {}) or {}).get('exclude', {})
            conds, prms = self._build_exclude_where_from_generic(default_exclude)
            where_conditions.extend(conds)
            params.extend(prms)

            # 传入的覆盖/追加规则（与默认结构一致）
            if isinstance(exclude_patterns, dict):
                ext_conds, ext_prms = self._build_exclude_where_from_generic(exclude_patterns)
                where_conditions.extend(ext_conds)
                params.extend(ext_prms)

            where_clause = " AND ".join(where_conditions)
            return self.load(condition=where_clause, params=tuple(params), order_by=order_by)
        except Exception as e:
            logger.error(f"加载可用股票失败: {e}")
            return []

    def _build_exclude_where_from_generic(self, exclude_conf: Dict[str, Dict[str, List[Any]]]) -> (List[str], List[Any]):
        """
        将通用排除配置转换为 SQL 条件（全部为 NOT 条件）。
        支持 how_to_exclude:
          - start_with: field NOT LIKE 'kw%'
          - contains:   field NOT LIKE '%kw%'
          - end_with:   field NOT LIKE '%kw'
          - equals:     field <> kw
          - in:         field NOT IN (...)
        未知字段或空关键词被忽略。
        """
        if not isinstance(exclude_conf, dict):
            return [], []

        allowed_fields = { 'id', 'name', 'industry', 'type', 'exchange_center', 'market' }
        conditions: List[str] = []
        params: List[Any] = []

        for how, field_map in (exclude_conf or {}).items():
            if not isinstance(field_map, dict):
                continue
            for field, keywords in field_map.items():
                if field not in allowed_fields:
                    continue
                if not keywords:
                    continue
                if not isinstance(keywords, list):
                    keywords = [keywords]

                clean_words = [str(k).strip() for k in keywords if str(k).strip()]
                if not clean_words:
                    continue

                if how == 'start_with':
                    for kw in clean_words:
                        conditions.append(f"{field} NOT LIKE %s")
                        params.append(f"{kw}%")
                elif how == 'contains':
                    for kw in clean_words:
                        conditions.append(f"{field} NOT LIKE %s")
                        params.append(f"%{kw}%")
                elif how == 'end_with':
                    for kw in clean_words:
                        conditions.append(f"{field} NOT LIKE %s")
                        params.append(f"%{kw}")
                elif how == 'equals':
                    for kw in clean_words:
                        conditions.append(f"{field} <> %s")
                        params.append(kw)
                elif how == 'in':
                    placeholders = ','.join(['%s'] * len(clean_words))
                    conditions.append(f"{field} NOT IN ({placeholders})")
                    params.extend(clean_words)
                else:
                    continue

        return conditions, params