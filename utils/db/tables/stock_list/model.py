"""
Stock List 自定义模型
与 stock_index 模型类似，但字段使用 isActive
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
        if not stock_data:
            return
        # 插入/更新活跃
        self.replace(stock_data, unique_keys=['id'])
        # 标记未出现为非活跃
        active_ids = [s['id'] for s in stock_data]
        if active_ids:
            placeholders = ','.join(['%s'] * len(active_ids))
            condition = f"id NOT IN ({placeholders}) AND isActive = 1"
            params = tuple(active_ids)
            # 用首条的 lastUpdate
            update_data = {
                'isActive': 0,
                'lastUpdate': stock_data[0]['lastUpdate']
            }
            self.update(update_data, condition, params)

    def load_filtered_stock_list(self, exclude_patterns: Optional[Dict[str, List[Any]]] = None, order_by: str = 'id') -> List[Dict[str, Any]]:
        """
        返回默认可用股票集合：
        - 只加载 isActive=1
        - 通用排除语法（来自 analyzer_settings.conf['stock_idx']['exclude']）
        - 允许传入 exclude_patterns（与默认结构一致）覆盖/追加
        """
        try:
            where_conditions = ["isActive = 1"]
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
        allowed_fields = { 'id', 'name', 'industry', 'type', 'exchangeCenter', 'market' }
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


