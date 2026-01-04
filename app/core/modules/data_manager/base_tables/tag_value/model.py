"""
Tag Value Model - 标签值存储
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel
from utils.date.date_utils import DateUtils


class TagValueModel(DbBaseModel):
    """标签值 Model"""
    
    def __init__(self, db=None):
        super().__init__('tag_value', db)
    
    def get_entity_tags(self, entity_id: str, as_of_date: str) -> List[Dict[str, Any]]:
        """
        获取指定实体在指定日期的所有标签（策略回测核心查询）
        
        查询逻辑：
        - 查询 as_of_date = 指定日期的 tag
        - 或者查询 start_date <= 指定日期 <= end_date 的 tag（时间段 tag）
        
        Args:
            entity_id: 实体ID（可以是股票代码、指数代码等）
            as_of_date: 业务日期（YYYYMMDD 或 YYYY-MM-DD）
            
        Returns:
            List[Dict]: [{"tag_id": 1, "value": "0.23", "start_date": "2025-01-01", "end_date": "2025-01-31"}, ...]
        """
        normalized_date = DateUtils.normalize_date(as_of_date)
        if not normalized_date:
            return []
        
        # 转换为数据库 DATE 格式
        db_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized_date)
        
        # 查询：as_of_date = 指定日期 或者 (start_date <= 指定日期 <= end_date)
        sql = """
            SELECT * FROM tag_value 
            WHERE entity_id = %s 
            AND (
                as_of_date = %s 
                OR (start_date IS NOT NULL AND end_date IS NOT NULL 
                    AND start_date <= %s AND end_date >= %s)
            )
            ORDER BY tag_id ASC
        """
        
        try:
            rows = self.db.execute_sync_query(sql, (entity_id, db_date, db_date, db_date))
            return rows or []
        except Exception as e:
            logger.error(f"获取实体标签失败 {entity_id} {as_of_date}: {e}")
            return []
    
    def get_tag_value(self, entity_id: str, tag_id: int, as_of_date: str) -> Optional[Dict[str, Any]]:
        """
        获取指定实体、指定标签、指定日期的值
        
        Args:
            entity_id: 实体ID
            tag_id: 标签ID
            as_of_date: 业务日期
            
        Returns:
            Dict 或 None
        """
        normalized_date = DateUtils.normalize_date(as_of_date)
        if not normalized_date:
            return None
        
        db_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized_date)
        
        return self.load_one(
            "entity_id = %s AND tag_id = %s AND as_of_date = %s",
            (entity_id, tag_id, db_date)
        )
    
    def get_entities_with_tag(self, tag_id: int, as_of_date: str) -> List[str]:
        """
        获取在指定日期拥有某个标签的实体列表
        
        Args:
            tag_id: 标签ID
            as_of_date: 业务日期
            
        Returns:
            List[str]: 实体ID列表
        """
        normalized_date = DateUtils.normalize_date(as_of_date)
        if not normalized_date:
            return []
        
        db_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized_date)
        
        records = self.load(
            "tag_id = %s AND as_of_date = %s",
            (tag_id, db_date)
        )
        
        return [r['entity_id'] for r in records if r.get('entity_id')]
    
    def save_tag_value(self, tag_value_data: Dict[str, Any]) -> int:
        """保存标签值（自动去重）"""
        # 统一转换日期格式
        date_fields = ['as_of_date', 'start_date', 'end_date']
        for field in date_fields:
            if field in tag_value_data and tag_value_data[field]:
                normalized = DateUtils.normalize_date(tag_value_data[field])
                if normalized:
                    tag_value_data[field] = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized)
        
        return self.replace_one(
            tag_value_data,
            unique_keys=['entity_id', 'tag_id', 'as_of_date']
        )
    
    def batch_save_tag_values(self, tag_values: List[Dict[str, Any]]) -> int:
        """批量保存标签值（自动去重）"""
        # 统一转换日期格式
        date_fields = ['as_of_date', 'start_date', 'end_date']
        for tv in tag_values:
            for field in date_fields:
                if field in tv and tv[field]:
                    normalized = DateUtils.normalize_date(tv[field])
                    if normalized:
                        tv[field] = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized)
        
        return self.replace(
            tag_values,
            unique_keys=['entity_id', 'tag_id', 'as_of_date']
        )
