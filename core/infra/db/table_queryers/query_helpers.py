"""
QueryHelpers - 查询和格式化辅助工具

提供时序数据查询、DataFrame 支持、Schema 格式化等功能。
"""
from typing import List, Dict, Any, Optional
from loguru import logger


class TimeSeriesHelper:
    """时序数据查询辅助类（通过继承提供）"""
    
    def load_latest_date(self, date_field: str = None) -> Optional[str]:
        """
        加载表中最新的日期
        
        Args:
            date_field: 日期字段名（如果为None，从schema中自动获取）
            
        Returns:
            Optional[str]: 最新日期，如果表为空返回None
        """
        if date_field is None:
            date_field = self._get_date_field_from_schema()
        
        latest_record = self.load_one("1=1", order_by=f"{date_field} DESC")
        return latest_record.get(date_field) if latest_record else None
    
    def load_latest_records(self, date_field: str = None, primary_keys: List[str] = None) -> List[Dict[str, Any]]:
        """
        加载每个主键分组中最新日期的记录
        
        Args:
            date_field: 日期字段名（如果为None，从schema中自动获取）
            primary_keys: 主键列表（如果为None，从schema中自动获取）
            
        Returns:
            List[Dict]: 最新记录列表
        """
        if date_field is None:
            date_field = self._get_date_field_from_schema()
        
        if primary_keys is None:
            primary_keys = self._get_primary_keys_from_schema()
        
        # 过滤掉日期字段（日期字段不用于分组）
        group_keys = [k for k in primary_keys if k != date_field]
        
        if not group_keys:
            latest_record = self.load_one("1=1", order_by=f"{date_field} DESC")
            return [latest_record] if latest_record else []
        
        # 有分组键，查询每个分组的最新记录
        group_keys_str = ', '.join(group_keys)
        query = f"""
            SELECT t1.* 
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_keys_str}, MAX({date_field}) as max_date
                FROM {self.table_name}
                GROUP BY {group_keys_str}
            ) t2 
            ON {' AND '.join([f't1.{k} = t2.{k}' for k in group_keys])}
            AND t1.{date_field} = t2.max_date
        """
        
        try:
            result = self.db.execute_sync_query(query)
            return result
        except Exception as e:
            logger.error(f"加载最新记录失败 [{self.table_name}]: {e}")
            return []
    
    def load_first_records(self, date_field: str = None, primary_keys: List[str] = None) -> List[Dict[str, Any]]:
        """
        加载每个主键分组中最早日期的记录
        
        Args:
            date_field: 日期字段名（如果为None，从schema中自动获取）
            primary_keys: 主键列表（如果为None，从schema中自动获取）
            
        Returns:
            List[Dict]: 最早记录列表
        """
        if date_field is None:
            date_field = self._get_date_field_from_schema()
        
        if primary_keys is None:
            primary_keys = self._get_primary_keys_from_schema()
        
        group_keys = [k for k in primary_keys if k != date_field]
        
        if not group_keys:
            first_record = self.load_one("1=1", order_by=f"{date_field} ASC")
            return [first_record] if first_record else []
        
        group_keys_str = ', '.join(group_keys)
        query = f"""
            SELECT t1.*
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_keys_str}, MIN({date_field}) as min_date
                FROM {self.table_name}
                GROUP BY {group_keys_str}
            ) t2
            ON {' AND '.join([f't1.{k} = t2.{k}' for k in group_keys])}
            AND t1.{date_field} = t2.min_date
        """
        
        try:
            return self.db.execute_sync_query(query)
        except Exception as e:
            logger.error(f"加载最早记录失败 [{self.table_name}]: {e}")
            return []
    
    def _get_date_field_from_schema(self) -> str:
        """从schema中获取日期字段名"""
        if not hasattr(self, 'schema') or not self.schema:
            raise ValueError(f"表 {self.table_name} 没有schema信息")
        
        date_field_candidates = ['date', 'trade_date', 'quarter', 'end_date', 'ann_date']
        fields = self.schema.get('fields', [])
        for field in fields:
            if field['name'] in date_field_candidates:
                return field['name']
        
        raise ValueError(
            f"表 {self.table_name} 的schema中未找到日期字段。"
            f"请在schema中添加以下任一字段: {', '.join(date_field_candidates)}"
        )
    
    def _get_primary_keys_from_schema(self) -> List[str]:
        """从schema中获取主键列表"""
        if not hasattr(self, 'schema') or not self.schema:
            raise ValueError(f"表 {self.table_name} 没有schema信息")
        
        primary_key = self.schema.get('primaryKey')
        if not primary_key:
            raise ValueError(f"表 {self.table_name} 的schema中未配置主键")
        
        if isinstance(primary_key, str):
            return [primary_key]
        elif isinstance(primary_key, list):
            return primary_key
        else:
            raise ValueError(f"表 {self.table_name} 的主键格式不正确: {primary_key}")


class DataFrameHelper:
    """DataFrame 支持辅助类（通过继承提供）"""
    
    def load_many_df(self, condition: str = "1=1", params: tuple = (), 
                     limit: int = None, order_by: str = None, offset: int = None):
        """加载多条记录，返回DataFrame"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用load_many_df方法")
            return None
        
        records = self.load_many(condition, params, limit, order_by, offset)
        return pd.DataFrame(records) if records else pd.DataFrame()
    
    def load_all_df(self, condition: str = "1=1", params: tuple = (), order_by: str = None):
        """加载所有记录，返回DataFrame"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用load_all_df方法")
            return None
        
        records = self.load_all(condition, params, order_by)
        return pd.DataFrame(records) if records else pd.DataFrame()
    
    def insert_df(self, df) -> int:
        """插入DataFrame数据"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用insert_df方法")
            return 0
        
        if not isinstance(df, pd.DataFrame):
            logger.error(f"insert_df expects pandas DataFrame, got {type(df)}")
            return 0
        
        if df.empty:
            logger.debug("DataFrame is empty, skipping insert")
            return 0
        
        data_list = df.to_dict('records')
        return self.insert(data_list)
    
    def replace_df(self, df, unique_keys: List[str]) -> int:
        """Upsert DataFrame数据（基于主键更新或插入）"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用replace_df方法")
            return 0
        
        if not isinstance(df, pd.DataFrame):
            logger.error(f"replace_df expects pandas DataFrame, got {type(df)}")
            return 0
        
        if df.empty:
            logger.debug("DataFrame is empty, skipping replace")
            return 0
        
        data_list = df.to_dict('records')
        return self.replace(data_list, unique_keys)


class SchemaFormatter:
    """Schema 格式化工具类"""
    
    @staticmethod
    def format_table_description(schema: Dict, table_name: str, output: bool = True) -> str:
        """
        格式化表结构和描述
        
        Args:
            schema: Schema 字典
            table_name: 表名
            output: 是否直接打印到控制台（默认 True）
            
        Returns:
            格式化的表结构描述字符串
        """
        if not schema:
            msg = f"⚠️  表 '{table_name}' 的 schema 未找到"
            if output:
                print(msg)
            return msg
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"表名: {schema.get('name', table_name)}")
        
        if 'description' in schema:
            lines.append(f"描述: {schema['description']}")
        
        lines.append("=" * 80)
        lines.append("")
        
        # 主键
        primary_key = schema.get('primaryKey')
        if primary_key:
            pk_str = ', '.join(primary_key) if isinstance(primary_key, list) else str(primary_key)
            lines.append(f"主键: {pk_str}")
            lines.append("")
        
        # 字段列表
        fields = schema.get('fields', [])
        if fields:
            lines.append("字段列表:")
            lines.append("-" * 80)
            header = f"{'字段名':<20} {'类型':<25} {'必填':<8} {'默认值':<15} {'描述'}"
            lines.append(header)
            lines.append("-" * 80)
            
            for field in fields:
                name = field.get('name', '')
                field_type = field.get('type', '').upper()
                
                type_display = field_type
                if 'length' in field:
                    length = field['length']
                    type_display = f"{field_type}({length})"
                
                if field_type == 'ENUM' and 'values' in field:
                    values = field['values']
                    if isinstance(values, list) and len(values) > 0:
                        if len(values) <= 3:
                            values_str = ', '.join(values)
                        else:
                            values_str = ', '.join(values[:3]) + f", ... ({len(values)} 个值)"
                        type_display = f"ENUM({values_str})"
                
                is_required = "是" if field.get('isRequired', False) else "否"
                default = field.get('default', '')
                default_str = '' if default is None else (default if isinstance(default, str) else str(default))
                if len(default_str) > 13:
                    default_str = default_str[:10] + "..."
                
                description = field.get('description', '') or field.get('comment', '')
                if len(description) > 40:
                    description = description[:37] + "..."
                
                auto_inc = field.get('autoIncrement', False) or field.get('isAutoIncrement', False)
                if auto_inc:
                    type_display += " [AUTO_INC]"
                
                line = f"{name:<20} {type_display:<25} {is_required:<8} {default_str:<15} {description}"
                lines.append(line)
            
            lines.append("-" * 80)
            lines.append(f"共 {len(fields)} 个字段")
            lines.append("")
        
        # 索引列表
        indexes = schema.get('indexes', [])
        if indexes:
            lines.append("索引列表:")
            lines.append("-" * 80)
            
            for index in indexes:
                index_name = index.get('name', '')
                index_fields = index.get('fields', [])
                is_unique = index.get('unique', False) or index.get('isUnique', False)
                index_desc = index.get('description', '')
                
                fields_str = ', '.join(index_fields) if isinstance(index_fields, list) else str(index_fields)
                unique_str = " [UNIQUE]" if is_unique else ""
                
                if index_desc:
                    lines.append(f"  {index_name}{unique_str}: {fields_str} - {index_desc}")
                else:
                    lines.append(f"  {index_name}{unique_str}: {fields_str}")
            
            lines.append("-" * 80)
            lines.append(f"共 {len(indexes)} 个索引")
            lines.append("")
        
        lines.append("=" * 80)
        
        result = '\n'.join(lines)
        
        if output:
            print(result)
        
        return result
