"""
Tag Data Service - Tag 系统数据服务

职责：
- 封装 Tag 相关的跨表查询和数据操作
- 提供领域级的业务方法

涉及的表：
- tag_scenario: 业务场景表
- tag_definition: 标签定义表
- tag_value: 标签值表
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from app.core.utils.date.date_utils import DateUtils

from ... import BaseDataService


class TagDataService(BaseDataService):
    """Tag 数据服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化 Tag 数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model（通过 DataManager，自动绑定默认 db）- 私有属性，不对外暴露
        self._tag_scenario_model = data_manager.get_table('tag_scenario')
        self._tag_definition_model = data_manager.get_table('tag_definition')
        self._tag_value_model = data_manager.get_table('tag_value')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from app.core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default()
    
    # ========================================================================
    # Scenario 相关 API
    # ========================================================================
    
    def load_scenario(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """
        加载指定名称的 scenario
        
        Args:
            scenario_name: Scenario 名称
        
        Returns:
            Dict[str, Any]: Scenario 记录（包含 id, name, display_name, description, created_at 等）
            None: 如果不存在
        """
        return self._tag_scenario_model.load_by_name(scenario_name)
    
    
    def save_scenario(
        self,
        scenario_name: str,
        display_name: str = None,
        description: str = None
    ) -> Dict[str, Any]:
        """
        创建新的 scenario
        
        Args:
            scenario_name: Scenario 名称
            display_name: 显示名称（可选，默认使用 scenario_name）
            description: 描述（可选，默认空字符串）
        
        Returns:
            Dict[str, Any]: 新创建的 scenario 记录
        """
        scenario_data = {
            'name': scenario_name,
            'display_name': display_name or scenario_name,
            'description': description or ''
        }
        
        self._tag_scenario_model.save_scenario(scenario_data)
        
        # 返回新创建的 scenario
        return self.load_scenario(scenario_name)
    
    
    def update_scenario(
        self,
        scenario_id: int,
        scenario_name: str = None,
        display_name: str = None,
        description: str = None,
        current_scenario: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        更新 scenario 信息
        
        Args:
            scenario_id: Scenario ID
            scenario_name: Scenario 名称（可选）
            display_name: 显示名称（可选）
            description: 描述（可选）
            current_scenario: 当前的 scenario 数据（可选，如果提供则避免额外查询）
        
        Returns:
            Dict[str, Any]: 更新后的 scenario 记录
        """
        update_data = {}
        if scenario_name is not None:
            update_data['name'] = scenario_name
        if display_name is not None:
            update_data['display_name'] = display_name
        if description is not None:
            update_data['description'] = description
        
        return self._update_entity(
            model=self._tag_scenario_model,
            entity_id=scenario_id,
            update_data=update_data,
            current_entity=current_scenario,
            update_method=lambda: self._tag_scenario_model.update_scenario(scenario_id, update_data)
        )
    
    def list_scenarios(
        self,
        scenario_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有 scenarios（支持按名称过滤）
        
        Args:
            scenario_name: Scenario 名称（可选，如果提供则只返回该名称的 scenario）
        
        Returns:
            List[Dict[str, Any]]: Scenario 列表
        """
        if scenario_name:
            scenario = self.load_scenario(scenario_name)
            return [scenario] if scenario else []
        else:
            return self._tag_scenario_model.load_all()
    
    def delete_scenario(self, scenario_id: int, cascade: bool = False) -> None:
        """
        删除 scenario（可选级联删除 tag definitions 和 tag values）
        
        Args:
            scenario_id: Scenario ID
            cascade: 是否级联删除（默认 False）
        
        Returns:
            None
        """
        if cascade:
            # 级联删除：先删除 tag values，再删除 tag definitions，最后删除 scenario
            self.delete_tag_values_by_scenario(scenario_id)
            self.delete_tag_definitions_by_scenario(scenario_id)
        
        self._tag_scenario_model.delete_scenario(scenario_id)
    
    # ========================================================================
    # Tag Definition 相关 API
    # ========================================================================
    
    def load(
        self,
        tag_name: str,
        scenario_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        加载指定名称的 tag definition
        
        Args:
            tag_name: Tag 名称
            scenario_id: Scenario ID
        
        Returns:
            Dict[str, Any]: Tag definition 记录（包含 id, name, scenario_id, display_name, description 等）
            None: 如果不存在
        """
        return self._tag_definition_model.load_by_name_and_scenario(
            tag_name, scenario_id
        )
    
    def save(
        self,
        tag_name: str,
        scenario_id: int,
        display_name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建新的 tag definition
        
        Args:
            tag_name: Tag 名称
            scenario_id: Scenario ID
            display_name: 显示名称
            description: 描述（可选，默认空字符串）
        
        Returns:
            Dict[str, Any]: 新创建的 tag definition 记录
        """
        tag_data = {
            'scenario_id': scenario_id,
            'name': tag_name,
            'display_name': display_name,
            'description': description or ''
        }
        
        self._tag_definition_model.save_tag_definition(tag_data)
        
        # 返回新创建的 tag definition
        return self.load(tag_name, scenario_id)
    
    
    def get_tag_definitions(
        self,
        scenario_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        获取 tag definitions 列表
        
        Args:
            scenario_id: Scenario ID（可选，如果提供则只返回该 scenario 下的 tags）
        
        Returns:
            List[Dict[str, Any]]: Tag definition 列表
        """
        if scenario_id:
            return self._tag_definition_model.load_by_scenario_id(scenario_id)
        else:
            # 查询所有 tag definitions
            return self._tag_definition_model.load("1=1", order_by="scenario_id ASC, name ASC")
    
    
    def update_tag_definition(
        self,
        tag_definition_id: int,
        display_name: str = None,
        description: str = None,
        current_tag: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        更新 tag definition 的非关键字段
        
        Args:
            tag_definition_id: Tag definition ID
            display_name: 显示名称（可选）
            description: 描述（可选）
            current_tag: 当前的 tag 数据（可选，如果提供则避免额外查询）
        
        Returns:
            Dict[str, Any]: 更新后的 tag definition 记录
        """
        update_data = {}
        if display_name is not None:
            update_data['display_name'] = display_name
        if description is not None:
            update_data['description'] = description
        
        return self._update_entity(
            model=self._tag_definition_model,
            entity_id=tag_definition_id,
            update_data=update_data,
            current_entity=current_tag,
            update_method=lambda: self._tag_definition_model.update("id = %s", (tag_definition_id,), update_data)
        )
    
    def batch_update_tag_definitions(
        self,
        updates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量更新 tag definitions 的非关键字段
        
        使用 MySQL 的 CASE WHEN 语句实现批量更新，减少数据库访问次数。
        
        Args:
            updates: 更新列表，每个元素包含：
                - 'tag_definition_id': int (必需)
                - 'display_name': str (可选)
                - 'description': str (可选)
                - 'current_tag': Dict[str, Any] (可选，用于返回更新后的数据)
        
        Returns:
            List[Dict[str, Any]]: 更新后的 tag definition 列表
        """
        if not updates:
            return []
        
        # 提取所有 tag_ids
        tag_ids = [item['tag_definition_id'] for item in updates]
        
        # 检查需要更新的字段
        updateable_fields = ['display_name', 'description']
        has_updates = {field: any(field in u and u[field] is not None for u in updates) 
                      for field in updateable_fields}
        
        if not any(has_updates.values()):
            logger.warning("batch_update_tag_definitions: 没有提供任何更新字段")
            return self._get_updated_entities(updates, self._tag_definition_model)
        
        # 构建批量更新的 SQL
        set_clauses, params = self._build_batch_update_sql(updates, tag_ids, updateable_fields, has_updates)
        
        # 执行批量更新
        placeholders = ', '.join(['%s'] * len(tag_ids))
        where_clause = f"id IN ({placeholders})"
        params.extend(tag_ids)
        query = f"UPDATE tag_definition SET {', '.join(set_clauses)} WHERE {where_clause}"
        
        try:
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, params)
                cursor.connection.commit()
                logger.info(f"批量更新 tag definitions: 更新了 {cursor.rowcount} 条记录")
        except Exception as e:
            logger.error(f"批量更新 tag definitions 失败: {e}")
            raise
        
        # 返回更新后的 tag definitions
        return self._get_updated_entities(updates, self._tag_definition_model)
    
    def delete_tag_definition(self, tag_definition_id: int) -> None:
        """
        删除指定的 tag definition
        
        Args:
            tag_definition_id: Tag definition ID
        
        Returns:
            None
        """
        self._tag_definition_model.delete("id = %s", (tag_definition_id,))
    
    def delete_tag_definitions_by_scenario(self, scenario_id: int) -> None:
        """
        删除指定 scenario 下的所有 tag definitions
        
        Args:
            scenario_id: Scenario ID
        
        Returns:
            None
        """
        self._tag_definition_model.delete_by_scenario_id(scenario_id)
    
    # ========================================================================
    # Tag Value 相关 API
    # ========================================================================
    
    def save_value(self, tag_value_data: Dict[str, Any]) -> int:
        """
        保存单个 tag value
        
        Args:
            tag_value_data: Tag value 数据字典，包含：
                - entity_id: str - 实体ID
                - tag_definition_id: int - Tag definition ID
                - as_of_date: str - 业务日期（YYYYMMDD）
                - value: str - 标签值（字符串）
                - start_date: str (可选) - 起始日期（YYYYMMDD）
                - end_date: str (可选) - 结束日期（YYYYMMDD）
                - entity_type: str (可选) - 实体类型（默认 "stock"）
        
        Returns:
            int: 保存的记录数（通常是 1）
        """
        return self._tag_value_model.save_tag_value(tag_value_data)
    
    def save_batch(self, tag_values: List[Dict[str, Any]]) -> int:
        """
        批量保存 tag values
        
        Args:
            tag_values: Tag value 数据列表（每个元素格式同 save_tag_value 的 tag_value_data）
        
        Returns:
            int: 保存的记录数
        """
        return self._tag_value_model.batch_save_tag_values(tag_values)
    
    def delete_tag_values_by_scenario(self, scenario_id: int) -> None:
        """
        删除指定 scenario 下的所有 tag values
        
        注意：需要通过 tag_definition_id 关联删除，因为 tag_value 表中没有直接的 scenario_id
        
        Args:
            scenario_id: Scenario ID
        
        Returns:
            None
        """
        # 1. 获取该 scenario 下的所有 tag_definition_ids
        tag_defs = self.get_tag_definitions(scenario_id=scenario_id)
        tag_definition_ids = [tag_def['id'] for tag_def in tag_defs]
        
        if not tag_definition_ids:
            logger.debug(f"Scenario {scenario_id} 下没有 tag definitions，无需删除 tag values")
            return
        
        # 2. 删除这些 tag_definition_id 对应的所有 tag values
        placeholders = ','.join(['%s'] * len(tag_definition_ids))
        sql = f"DELETE FROM tag_value WHERE tag_definition_id IN ({placeholders})"
        
        try:
            self.db.execute_sync_query(sql, tuple(tag_definition_ids))
            logger.info(f"已删除 scenario {scenario_id} 下的 {len(tag_definition_ids)} 个 tag definitions 对应的所有 tag values")
        except Exception as e:
            logger.error(f"删除 tag values 失败: scenario_id={scenario_id}, error={e}")
            raise
    
    def get_max_as_of_date(self, tag_definition_ids: List[int]) -> Optional[str]:
        """
        获取指定 tag definitions 的最大 as_of_date（用于增量计算）
        
        Args:
            tag_definition_ids: Tag definition ID 列表
        
        Returns:
            Optional[str]: 最大 as_of_date（YYYYMMDD 格式），如果没有数据则返回 None
        """
        if not tag_definition_ids:
            return None
        
        try:
            # 构建查询：查询这些 tag_definition_id 的最大 as_of_date
            placeholders = ','.join(['%s'] * len(tag_definition_ids))
            sql = f"""
                SELECT MAX(as_of_date) as max_date
                FROM tag_value
                WHERE tag_definition_id IN ({placeholders})
            """
            
            result = self.db.execute_sync_query(sql, tuple(tag_definition_ids))
            if result and result[0].get('max_date'):
                max_date = result[0]['max_date']
                # 转换为 YYYYMMDD 格式
                return self._normalize_date_to_yyyymmdd(max_date)
            
            return None
        except Exception as e:
            logger.warning(f"查询最大 as_of_date 失败: {e}")
            return None
    
    # ========================================================================
    # 辅助 API
    # ========================================================================
    
    def get_tag_value_last_update_info(self, scenario_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取 scenario 下所有 tag values 的最后更新信息（按 entity 分组）
        
        Args:
            scenario_name: Scenario 名称
        
        Returns:
            Dict[str, Dict[str, Any]]: 每个 entity_id 对应的最后更新信息
                {
                    "entity_id": {
                        "max_as_of_date": "20250101",  # 最大 as_of_date
                        "tag_definition_ids": [1, 2, 3]  # 相关的 tag definition IDs
                    }
                }
        """
        scenario = self.load_scenario(scenario_name)
        if not scenario:
            return {}
        
        scenario_id = scenario.get('id')
        
        # 获取该 scenario 下的所有 tag definitions
        tag_defs = self.get_tag_definitions(scenario_id)
        tag_definition_ids = [tag_def['id'] for tag_def in tag_defs]
        
        if not tag_definition_ids:
            return {}
        
        # 查询每个 entity 的最大 as_of_date
        placeholders = ','.join(['%s'] * len(tag_definition_ids))
        sql = f"""
            SELECT 
                entity_id,
                MAX(as_of_date) as max_as_of_date
            FROM tag_value
            WHERE tag_definition_id IN ({placeholders})
            GROUP BY entity_id
        """
        
        try:
            results = self.db.execute_sync_query(sql, tuple(tag_definition_ids))
            result = {}
            for row in results:
                entity_id = row.get('entity_id')
                max_date = row.get('max_as_of_date')
                if entity_id and max_date:
                    result[entity_id] = {
                        "max_as_of_date": self._normalize_date_to_yyyymmdd(max_date),
                        "tag_definition_ids": tag_definition_ids
                    }
            return result
        except Exception as e:
            logger.error(f"查询 tag value 最后更新信息失败: {e}")
            return {}
    
    def get_next_trading_date(self, date: str) -> str:
        """
        获取下一个交易日
        
        Args:
            date: 当前日期（YYYYMMDD 格式）
        
        Returns:
            str: 下一个交易日（YYYYMMDD 格式）
        
        注意：此方法应该委托给 CalendarService，当前为简单实现
        """
        # TODO: 委托给 CalendarService.get_next_trading_date() 实现
        # 当前使用简单逻辑：日期 + 1 天
        try:
            from datetime import datetime, timedelta
            date_obj = datetime.strptime(date, '%Y%m%d')
            next_date = date_obj + timedelta(days=1)
            return next_date.strftime('%Y%m%d')
        except Exception as e:
            logger.warning(f"获取下一个交易日失败: {e}, 使用原日期: {date}")
            return date
    
    # ==================== 私有辅助方法 ====================
    
    def _update_entity(
        self,
        model: Any,
        entity_id: int,
        update_data: Dict[str, Any],
        current_entity: Optional[Dict[str, Any]],
        update_method: callable
    ) -> Dict[str, Any]:
        """
        通用实体更新方法（提取 update_scenario 和 update_tag_definition 的公共逻辑）
        
        Args:
            model: Model 实例
            entity_id: 实体 ID
            update_data: 更新数据字典
            current_entity: 当前实体数据（可选）
            update_method: 执行更新的方法（lambda 函数）
        
        Returns:
            Dict[str, Any]: 更新后的实体记录
        """
        if not update_data:
            logger.warning(f"没有提供任何更新字段，entity_id={entity_id}")
            if current_entity:
                return current_entity
            return model.load_one("id = %s", (entity_id,))
        
        update_method()
        
        # 如果提供了 current_entity，直接在内存中更新，避免额外查询
        if current_entity:
            updated_entity = current_entity.copy()
            updated_entity.update(update_data)
            return updated_entity
        
        # 如果没有提供 current_entity，查询一次
        return model.load_one("id = %s", (entity_id,))
    
    def _build_batch_update_sql(
        self,
        updates: List[Dict[str, Any]],
        tag_ids: List[int],
        updateable_fields: List[str],
        has_updates: Dict[str, bool]
    ) -> tuple[List[str], List[Any]]:
        """
        构建批量更新的 SQL 语句
        
        Args:
            updates: 更新列表
            tag_ids: Tag ID 列表
            updateable_fields: 可更新字段列表
            has_updates: 字段是否有更新的字典
        
        Returns:
            (set_clauses, params): SET 子句列表和参数列表
        """
        set_clauses = []
        params = []
        
        for field in updateable_fields:
            if has_updates.get(field):
                case_when_parts = []
                case_params = []
                for update_item in updates:
                    tag_id = update_item['tag_definition_id']
                    if field in update_item and update_item[field] is not None:
                        case_when_parts.append("WHEN id = %s THEN %s")
                        case_params.extend([tag_id, update_item[field]])
                if case_when_parts:
                    set_clauses.append(f"{field} = CASE {' '.join(case_when_parts)} ELSE {field} END")
                    params.extend(case_params)
        
        return set_clauses, params
    
    def _get_updated_entities(
        self,
        updates: List[Dict[str, Any]],
        model: Any
    ) -> List[Dict[str, Any]]:
        """
        获取更新后的实体列表（从 current_tag 或数据库查询）
        
        Args:
            updates: 更新列表
            model: Model 实例
        
        Returns:
            List[Dict[str, Any]]: 更新后的实体列表
        """
        result = []
        for update_item in updates:
            tag_id = update_item['tag_definition_id']
            if 'current_tag' in update_item:
                # 在内存中更新
                updated_tag = update_item['current_tag'].copy()
                updated_tag.update({k: v for k, v in update_item.items() 
                                  if k in ['display_name', 'description'] and v is not None})
                result.append(updated_tag)
            else:
                # 查询数据库
                tag = model.load_one("id = %s", (tag_id,))
                if tag:
                    result.append(tag)
        return result
    
    @staticmethod
    def _normalize_date_to_yyyymmdd(date_value: Any) -> Optional[str]:
        """
        将日期值统一转换为 YYYYMMDD 格式
        
        Args:
            date_value: 日期值（可能是 str、date 对象等）
        
        Returns:
            YYYYMMDD 格式的日期字符串，如果转换失败返回 None
        """
        if not date_value:
            return None
        
        try:
            if isinstance(date_value, str):
                # 如果是 YYYY-MM-DD 格式，转换为 YYYYMMDD
                if '-' in date_value:
                    return DateUtils.yyyy_mm_dd_to_yyyymmdd(date_value)
                return date_value
            else:
                # 如果是 date/datetime 对象，转换为字符串
                return date_value.strftime('%Y%m%d')
        except Exception as e:
            logger.warning(f"日期格式转换失败: {date_value}, error={e}")
            return None
