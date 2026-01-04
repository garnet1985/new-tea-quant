"""
股票标签 Model
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from app.core.infra.db import DbBaseModel
from app.core.utils.date.date_utils import DateUtils


class StockLabelsModel(DbBaseModel):
    """股票标签 Model"""
    
    def __init__(self, db=None):
        super().__init__('stock_labels', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有标签"""
        return self.load("id = %s", (stock_id,), order_by="date DESC")
    
    def load_by_date(
        self, 
        stock_id: str, 
        date: str
    ) -> Optional[Dict[str, Any]]:
        """查询指定股票指定日期的标签"""
        return self.load_one("id = %s AND date = %s", (stock_id, date))
    
    def load_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的标签"""
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
    
    def save_labels(self, labels: List[Dict[str, Any]]) -> int:
        """批量保存标签（自动去重）"""
        return self.replace(labels, unique_keys=['id', 'date'])

    # ==================== 新版标签接口（与 LabelDataService 对齐） ====================

    # 为了兼容旧表结构，这里动态检测字段名（支持 id/date 或 stock_id/label_date）

    @property
    def _stock_id_field(self) -> str:
        """返回股票ID字段名（stock_id 或 id）"""
        try:
            if self.schema and 'fields' in self.schema:
                field_names = {f.get('name') for f in self.schema.get('fields', [])}
                if 'stock_id' in field_names:
                    return 'stock_id'
                if 'id' in field_names:
                    return 'id'
        except Exception:
            pass
        # 默认按新设计
        return 'stock_id'

    @property
    def _date_field(self) -> str:
        """返回日期字段名（label_date 或 date）"""
        try:
            if self.schema and 'fields' in self.schema:
                field_names = {f.get('name') for f in self.schema.get('fields', [])}
                if 'label_date' in field_names:
                    return 'label_date'
                if 'date' in field_names:
                    return 'date'
        except Exception:
            pass
        # 默认按新设计
        return 'label_date'

    # -------- 工具方法 --------

    def _normalize_to_yyyymmdd(self, date_val) -> Optional[str]:
        """将任意日期值转换为 YYYYMMDD 字符串"""
        if date_val is None:
            return None
        if isinstance(date_val, str):
            return DateUtils.normalize_date(date_val)
        # 可能是 date/datetime
        return DateUtils.normalize_date(str(date_val))

    def _to_db_date_str(self, date_str: str) -> str:
        """
        将外部传入的日期字符串转换为数据库字段可接受的格式。
        - 如果字段是 DATE 类型（通常为 label_date），传入 'YYYY-MM-DD' 更友好
        - 这里简单处理：如果是 YYYYMMDD 则转成 YYYY-MM-DD，否则保持原样
        """
        if not date_str:
            return date_str
        date_str = str(date_str)
        if '-' in date_str:
            return date_str
        # 视为 YYYYMMDD
        try:
            return DateUtils.yyyymmdd_to_yyyy_mm_dd(date_str)
        except Exception:
            return date_str

    def _parse_labels_string(self, labels_str: str) -> List[str]:
        """解析逗号分隔的标签字符串为列表"""
        if not labels_str:
            return []
        return [label.strip() for label in str(labels_str).split(',') if label and str(label).strip()]

    # -------- 供 LabelDataService 使用的接口实现 --------

    def get_all_stocks_last_update_dates(
        self,
        stock_ids: List[str]
    ) -> Dict[str, str]:
        """
        批量获取股票的最后标签更新日期

        Returns:
            Dict[str, str]: 股票代码 -> 最新标签日期（YYYYMMDD）
        """
        if not stock_ids:
            return {}

        stock_ids = [str(s) for s in stock_ids]
        stock_field = self._stock_id_field
        date_field = self._date_field

        # 使用聚合查询获取每只股票的最大日期
        placeholders = ','.join(['%s'] * len(stock_ids))
        sql = (
            f"SELECT {stock_field} AS stock_id, MAX({date_field}) AS last_date "
            f"FROM {self.table_name} "
            f"WHERE {stock_field} IN ({placeholders}) "
            f"GROUP BY {stock_field}"
        )

        try:
            rows = self.db.execute_sync_query(sql, tuple(stock_ids))
        except Exception as e:
            logger.error(f"获取股票最后标签更新日期失败: {e}")
            return {}

        result: Dict[str, str] = {}
        for row in rows or []:
            sid = str(row.get('stock_id'))
            last_date_raw = row.get('last_date')
            norm = self._normalize_to_yyyymmdd(last_date_raw)
            if sid and norm:
                result[sid] = norm

        return result

    def get_stock_labels_by_date_range(
        self,
        stock_id: str,
        target_date: str,
        max_days_back: int = 90
    ) -> Dict[str, Any]:
        """
        获取股票在 [target_date - max_days_back, target_date] 区间内最近一次的标签记录。

        返回结构与 LabelDataService.get_stock_labels 文档保持一致：
            {
                'labels': [...],
                'label_date': 'YYYYMMDD',
                'days_back': int,
                'is_valid': bool
            }
        """
        try:
            stock_field = self._stock_id_field
            date_field = self._date_field

            target_ymd = DateUtils.normalize_date(target_date)
            if not target_ymd:
                raise ValueError(f"无法解析目标日期: {target_date}")

            start_ymd = DateUtils.get_date_before_days(target_ymd, max_days_back)

            db_start_date = self._to_db_date_str(start_ymd)
            db_target_date = self._to_db_date_str(target_ymd)

            sql = (
                f"SELECT {date_field} AS label_date, labels "
                f"FROM {self.table_name} "
                f"WHERE {stock_field} = %s "
                f"AND {date_field} >= %s AND {date_field} <= %s "
                f"ORDER BY {date_field} DESC "
                f"LIMIT 1"
            )

            rows = self.db.execute_sync_query(sql, (stock_id, db_start_date, db_target_date))
            if not rows:
                return {
                    'labels': [],
                    'label_date': None,
                    'days_back': None,
                    'is_valid': False
                }

            row = rows[0]
            label_date_norm = self._normalize_to_yyyymmdd(row.get('label_date'))
            if not label_date_norm:
                return {
                    'labels': [],
                    'label_date': None,
                    'days_back': None,
                    'is_valid': False
                }

            days_back = DateUtils.get_duration_in_days(label_date_norm, target_ymd)
            labels_list = self._parse_labels_string(row.get('labels', ''))

            return {
                'labels': labels_list,
                'label_date': label_date_norm,
                'days_back': days_back,
                'is_valid': days_back <= max_days_back
            }
        except Exception as e:
            logger.error(f"获取股票标签区间数据失败 {stock_id} {target_date}: {e}")
            return {
                'labels': [],
                'label_date': None,
                'days_back': None,
                'is_valid': False
            }

    def get_stock_labels_by_date(
        self,
        stock_id: str,
        target_date: str
    ) -> List[str]:
        """获取指定股票在指定日期的标签列表"""
        try:
            stock_field = self._stock_id_field
            date_field = self._date_field
            db_date = self._to_db_date_str(DateUtils.normalize_date(target_date) or target_date)

            condition = f"{stock_field} = %s AND {date_field} = %s"
            row = self.load_one(condition, (stock_id, db_date))
            if not row or not row.get('labels'):
                return []
            return self._parse_labels_string(row['labels'])
        except Exception as e:
            logger.error(f"获取股票标签失败 {stock_id} {target_date}: {e}")
            return []

    def get_stocks_with_label(
        self,
        label_id: str,
        target_date: str
    ) -> List[str]:
        """
        获取在指定日期拥有某个标签的股票列表
        """
        stock_field = self._stock_id_field
        date_field = self._date_field
        target_ymd = DateUtils.normalize_date(target_date) or target_date
        db_date = self._to_db_date_str(target_ymd)

        sql = (
            f"SELECT {stock_field} AS stock_id "
            f"FROM {self.table_name} "
            f"WHERE {date_field} = %s "
            f"AND FIND_IN_SET(%s, labels) > 0"
        )

        try:
            rows = self.db.execute_sync_query(sql, (db_date, label_id))
            return [str(row['stock_id']) for row in rows or [] if row.get('stock_id') is not None]
        except Exception as e:
            logger.error(f"获取具有标签的股票失败 {label_id} {target_date}: {e}")
            return []

    def get_label_statistics(self, target_date: str) -> Dict[str, Any]:
        """
        获取指定日期的标签统计信息：
            - stock_count: 有标签的股票数量
            - label_count: 标签记录总数（行数）
            - unique_labels: 不同标签ID数量（粗略估计）
        """
        date_field = self._date_field
        target_ymd = DateUtils.normalize_date(target_date) or target_date
        db_date = self._to_db_date_str(target_ymd)

        sql = f"""
        SELECT 
            COUNT(DISTINCT {self._stock_id_field}) as stock_count,
            COUNT(*) as label_count,
            COUNT(DISTINCT SUBSTRING_INDEX(labels, ',', 1)) as unique_labels
        FROM {self.table_name}
        WHERE {date_field} = %s
        """

        try:
            rows = self.db.execute_sync_query(sql, (db_date,))
            if rows:
                stats = rows[0]
                stats['target_date'] = DateUtils.normalize_date(db_date) or db_date
                return stats
            return {
                'target_date': DateUtils.normalize_date(db_date) or db_date,
                'stock_count': 0,
                'label_count': 0,
                'unique_labels': 0
            }
        except Exception as e:
            logger.error(f"获取标签统计信息失败 {target_date}: {e}")
            return {
                'target_date': DateUtils.normalize_date(db_date) or db_date,
                'stock_count': 0,
                'label_count': 0,
                'unique_labels': 0
            }

    def upsert_stock_label(
        self,
        stock_id: str,
        label_date: str,
        labels: List[str]
    ) -> bool:
        """
        插入或更新单条股票标签记录
        """
        stock_field = self._stock_id_field
        date_field = self._date_field
        db_date = self._to_db_date_str(DateUtils.normalize_date(label_date) or label_date)

        labels_str = ','.join(labels) if isinstance(labels, list) else str(labels or '')
        data = {
            stock_field: stock_id,
            date_field: db_date,
            'labels': labels_str
        }
        try:
            affected = self.replace_one(data, unique_keys=[stock_field, date_field])
            return affected > 0
        except Exception as e:
            logger.error(f"保存股票标签失败 {stock_id} {label_date}: {e}")
            return False

    def batch_upsert_stock_labels(
        self,
        labels_to_save: List[Dict[str, Any]]
    ) -> bool:
        """
        批量插入或更新股票标签记录
        """
        if not labels_to_save:
            return True

        stock_field = self._stock_id_field
        date_field = self._date_field

        data_list: List[Dict[str, Any]] = []
        for item in labels_to_save:
            try:
                stock_id = item.get('stock_id') or item.get(stock_field)
                label_date = item.get('label_date') or item.get(date_field)
                labels_val = item.get('labels', [])

                if not stock_id or not label_date:
                    continue

                db_date = self._to_db_date_str(DateUtils.normalize_date(label_date) or label_date)

                if isinstance(labels_val, list):
                    labels_str = ','.join(labels_val)
                else:
                    labels_str = str(labels_val or '')

                data_list.append({
                    stock_field: stock_id,
                    date_field: db_date,
                    'labels': labels_str
                })
            except Exception as e:
                logger.error(f"构建批量标签数据失败: {e}")
                continue

        if not data_list:
            return True

        try:
            affected = self.replace(data_list, unique_keys=[stock_field, date_field])
            return affected > 0
        except Exception as e:
            logger.error(f"批量保存股票标签失败: {e}")
            return False

