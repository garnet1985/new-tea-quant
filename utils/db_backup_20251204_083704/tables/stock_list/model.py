"""
Stock List 自定义模型
提供股票列表相关的特定方法（替代 stock_index）
"""
from utils.db.db_model import BaseTableModel
from typing import List, Dict, Any, Optional
from loguru import logger
from app.analyzer.analyzer_settings import conf


class StockListModel(BaseTableModel):
    """股票列表表自定义模型"""
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        self.is_base_table = True

    def renew_list(self, stock_data: List[Dict[str, Any]]):
        """
        一次性更新股票列表：插入/更新活跃股票，标记未出现的股票为非活跃
        
        Args:
            stock_data: 已经格式化好的股票数据列表，包含id, name, industry, type, exchange_center, is_active, last_update等字段
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
            condition = f"id NOT IN ({placeholders}) AND is_active = 1"
            params = tuple(active_stock_ids)
            
            update_data = {
                'is_active': 0,
                'last_update': stock_data[0]['last_update']  # 使用第一条数据的last_update
            }
            
            self.update(update_data, condition, params)

    def load_filtered_stock_list(self, exclude_patterns: Optional[Dict[str, List[Any]]] = None, order_by: str = 'id') -> List[Dict[str, Any]]:
        """
        返回默认可用股票集合：
        - 只加载 is_active =1
        - 通用排除语法（来自 analyzer_settings.conf['stock_idx']['exclude']）
        - 允许传入 exclude_patterns（与默认结构一致）覆盖/追加
        """
        try:
            where_conditions = ["is_active = 1"]
            params: List[Any] = []

            # 默认从全局配置引入排除规则
            default_exclude = (conf.get('stock_idx', {}) or {}).get('exclude', {})
            conds, prms = self._build_exclude_where_from_generic(default_exclude)
            where_conditions.extend(conds)
            params.extend(prms)

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
                if not isinstance(keywords, List):
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
    
    # ==================== 便捷方法 ====================
    
    def load_all_active(self, order_by: str = 'id') -> List[Dict[str, Any]]:
        """返回所有活跃股票"""
        return self.load("is_active = 1", order_by=order_by)
    
    def load_by_industry(self, industry: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按行业返回股票"""
        return self.load("is_active = 1 AND industry = %s", params=(industry,), order_by=order_by)
    
    def load_by_type(self, stock_type: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按股票类型返回股票"""
        return self.load("is_active = 1 AND type = %s", params=(stock_type,), order_by=order_by)
    
    def load_by_exchange_center(self, exchange_center: str, order_by: str = 'id') -> List[Dict[str, Any]]:
        """按交易所返回股票"""
        return self.load("is_active = 1 AND exchange_center = %s", params=(exchange_center,), order_by=order_by)
    
    def load_name_by_id(self, stock_id: str) -> Optional[str]:
        """根据股票ID加载股票名称"""
        stock = self.load_one("id = %s", (stock_id,))
        return stock['name'] if stock else None
    
    def load_stock_by_id(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """根据股票ID加载完整股票信息"""
        stock = self.load_one("id = %s", (stock_id,))
        if stock:
            return {
                'id': stock['id'],
                'name': stock['name'],
                'industry': stock.get('industry', ''),
                'type': stock.get('type', ''),
                'exchange_center': stock.get('exchange_center', ''),
                'is_active': stock.get('is_active', 0)
            }
        return None
    
    def load_stocks_by_ids(self, stock_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """根据股票ID列表加载完整股票信息映射"""
        if not stock_ids:
            return {}
        
        # 构建IN查询的占位符
        placeholders = ','.join(['%s'] * len(stock_ids))
        stocks = self.load_many(f"id IN ({placeholders})", tuple(stock_ids))
        
        result = {}
        for stock in stocks:
            result[stock['id']] = {
                'id': stock['id'],
                'name': stock['name'],
                'industry': stock.get('industry', ''),
                'type': stock.get('type', ''),
                'exchange_center': stock.get('exchange_center', ''),
                'is_active': stock.get('is_active', 0)
            }
        return result
    
    def load_name_by_ids(self, stock_ids: List[str]) -> Dict[str, str]:
        """根据股票ID列表加载股票名称映射"""
        if not stock_ids:
            return {}
        
        # 构建IN查询的占位符
        placeholders = ','.join(['%s'] * len(stock_ids))
        stocks = self.load_many(f"id IN ({placeholders})", tuple(stock_ids))
        return {stock['id']: stock['name'] for stock in stocks}
    
    def load_latest_last_update(self) -> Optional[str]:
        """获取最新的更新时间"""
        latest_record = self.load_one("1=1", order_by="last_update DESC")
        return latest_record.get('last_update') if latest_record else None


