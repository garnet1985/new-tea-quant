"""
Tag Value Model - 标签值存储
"""
import json
from typing import List, Dict, Any, Optional
from app.core.infra.db import DbBaseModel
from app.core.utils.date.date_utils import DateUtils


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
            List[Dict]: [{"tag_definition_id": 1, "json_value": {"momentum": 0.23}, "start_date": "2025-01-01", "end_date": "2025-01-31"}, ...]
            # 注意：json_value 字段如果是 JSON 格式会自动解析为 dict/list，否则保持字符串格式（向后兼容）
        """
        normalized_date = DateUtils.normalize_date(as_of_date)
        if not normalized_date:
            return []
        
        # 转换为数据库 DATE 格式
        db_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized_date)
        
        # 查询：as_of_date = 指定日期 或者 (start_date <= 指定日期 <= end_date)
        # 注意：使用 json_value 字段名
        sql = """
            SELECT * FROM tag_value 
            WHERE entity_id = %s 
            AND (
                as_of_date = %s 
                OR (start_date IS NOT NULL AND end_date IS NOT NULL 
                    AND start_date <= %s AND end_date >= %s)
            )
            ORDER BY tag_definition_id ASC
        """
        
        try:
            rows = self.db.execute_sync_query(sql, (entity_id, db_date, db_date, db_date))
            if rows:
                # 处理 JSON 字段：如果 json_value 是 JSON 字符串，尝试解析为 Python 对象
                for row in rows:
                    if 'json_value' in row and row['json_value']:
                        value = row['json_value']
                        if isinstance(value, str):
                            try:
                                # 尝试解析 JSON 字符串
                                row['json_value'] = json.loads(value)
                            except (json.JSONDecodeError, TypeError):
                                # 如果不是 JSON，保持原样（向后兼容）
                                pass
                    # 向后兼容：如果还有旧的 'value' 字段，也处理
                    if 'value' in row and row['value']:
                        value = row['value']
                        if isinstance(value, str):
                            try:
                                row['value'] = json.loads(value)
                            except (json.JSONDecodeError, TypeError):
                                pass
            return rows or []
        except Exception as e:
            logger.error(f"获取实体标签失败 {entity_id} {as_of_date}: {e}")
            return []
    
    def get_tag_value(self, entity_id: str, tag_definition_id: int, as_of_date: str) -> Optional[Dict[str, Any]]:
        """
        获取指定实体、指定标签、指定日期的值
        
        Args:
            entity_id: 实体ID
            tag_definition_id: 标签定义ID
            as_of_date: 业务日期
        
        Returns:
            Dict 或 None
        """
        normalized_date = DateUtils.normalize_date(as_of_date)
        if not normalized_date:
            return None
        
        db_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized_date)
        
        result = self.load_one(
            "entity_id = %s AND tag_definition_id = %s AND as_of_date = %s",
            (entity_id, tag_definition_id, db_date)
        )
        
        # 处理 JSON 字段：如果 json_value 是 JSON 字符串，尝试解析为 Python 对象
        if result and 'json_value' in result and result['json_value']:
            value = result['json_value']
            if isinstance(value, str):
                try:
                    # 尝试解析 JSON 字符串
                    result['json_value'] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # 如果不是 JSON，保持原样（向后兼容）
                    pass
        # 向后兼容：如果还有旧的 'value' 字段，也处理
        elif result and 'value' in result and result['value']:
            value = result['value']
            if isinstance(value, str):
                try:
                    result['value'] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return result
    
    def get_entities_with_tag(self, tag_definition_id: int, as_of_date: str) -> List[str]:
        """
        获取在指定日期拥有某个标签的实体列表
        
        Args:
            tag_definition_id: 标签定义ID
            as_of_date: 业务日期
        
        Returns:
            List[str]: 实体ID列表
        """
        normalized_date = DateUtils.normalize_date(as_of_date)
        if not normalized_date:
            return []
        
        db_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(normalized_date)
        
        records = self.load(
            "tag_definition_id = %s AND as_of_date = %s",
            (tag_definition_id, db_date)
        )
        
        # 注意：这里不需要解析 JSON，因为只返回 entity_id 列表
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
        
        # 处理 json_value 字段：如果是字典/列表，转换为 JSON 字符串；如果是字符串，尝试解析为 JSON
        # 向后兼容：同时支持 'value' 和 'json_value' 字段名
        value_key = 'json_value' if 'json_value' in tag_value_data else 'value'
        if value_key in tag_value_data:
            value = tag_value_data[value_key]
            if isinstance(value, (dict, list)):
                # 如果是字典或列表，转换为 JSON 字符串（MySQL JSON 类型会自动处理）
                tag_value_data['json_value'] = json.dumps(value, ensure_ascii=False)
                # 如果原来用的是 'value'，删除旧字段
                if value_key == 'value' and 'value' in tag_value_data:
                    del tag_value_data['value']
            elif isinstance(value, str) and value:
                # 如果是字符串，尝试验证是否为有效的 JSON
                # 如果不是 JSON 格式，保持原样（向后兼容）
                try:
                    json.loads(value)  # 验证是否为有效 JSON
                    # 如果是有效 JSON，保持原样
                    tag_value_data['json_value'] = value
                    if value_key == 'value' and 'value' in tag_value_data:
                        del tag_value_data['value']
                except (json.JSONDecodeError, TypeError):
                    # 如果不是 JSON，可以转换为简单的 JSON 对象，或者保持原样
                    # 为了向后兼容，我们保持原样，让用户自己决定格式
                    tag_value_data['json_value'] = value
                    if value_key == 'value' and 'value' in tag_value_data:
                        del tag_value_data['value']
        
        # 主键字段：entity_id, tag_definition_id, as_of_date（与 schema.json 一致）
        return self.replace_one(
            tag_value_data,
            unique_keys=['entity_id', 'tag_definition_id', 'as_of_date']
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
            
            # 处理 json_value 字段：如果是字典/列表，转换为 JSON 字符串；如果是字符串，尝试解析为 JSON
            # 向后兼容：同时支持 'value' 和 'json_value' 字段名
            value_key = 'json_value' if 'json_value' in tv else 'value'
            if value_key in tv:
                value = tv[value_key]
                if isinstance(value, (dict, list)):
                    # 如果是字典或列表，转换为 JSON 字符串（MySQL JSON 类型会自动处理）
                    tv['json_value'] = json.dumps(value, ensure_ascii=False)
                    # 如果原来用的是 'value'，删除旧字段
                    if value_key == 'value' and 'value' in tv:
                        del tv['value']
                elif isinstance(value, str) and value:
                    # 如果是字符串，尝试验证是否为有效的 JSON
                    # 如果不是 JSON 格式，保持原样（向后兼容）
                    try:
                        json.loads(value)  # 验证是否为有效 JSON
                        # 如果是有效 JSON，保持原样
                        tv['json_value'] = value
                        if value_key == 'value' and 'value' in tv:
                            del tv['value']
                    except (json.JSONDecodeError, TypeError):
                        # 如果不是 JSON，可以转换为简单的 JSON 对象，或者保持原样
                        # 为了向后兼容，我们保持原样，让用户自己决定格式
                        tv['json_value'] = value
                        if value_key == 'value' and 'value' in tv:
                            del tv['value']
        
        # 主键字段：entity_id, tag_definition_id, as_of_date（与 schema.json 一致）
        return self.replace(
            tag_values,
            unique_keys=['entity_id', 'tag_definition_id', 'as_of_date']
        )
