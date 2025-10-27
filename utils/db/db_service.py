from typing import Any, Dict, List, Tuple
from utils.db.db_config import DB_CONFIG


class DBService:

    @staticmethod
    def parse_db_schema(schema_data: dict, custom_table_name: str = None):
        """根据schema数据生成CREATE TABLE SQL语句"""
        table_name = custom_table_name if custom_table_name else schema_data['name']
        primary_key = schema_data.get('primaryKey', 'id')
        fields = schema_data['fields']
        indexes = schema_data.get('indexes', [])
        
        # 构建字段定义
        field_definitions = []
        for field in fields:
            field_name = field['name']
            field_type = field['type'].upper()
            is_required = field.get('isRequired', False)
            auto_increment = field.get('autoIncrement', False)
            
            # 处理字段类型和长度
            if field_type == 'VARCHAR' and 'length' in field:
                field_def = f"`{field_name}` {field_type}({field['length']})"
            elif field_type == 'TEXT':
                field_def = f"`{field_name}` {field_type}"
            elif field_type == 'JSON':
                field_def = f"`{field_name}` {field_type}"
            elif field_type == 'TINYINT':
                field_def = f"`{field_name}` {field_type}(1)"
            elif field_type == 'DATETIME':
                field_def = f"`{field_name}` {field_type}"
            elif field_type == 'DECIMAL' and 'length' in field:
                # 若仍有老schema定义为DECIMAL，按DOUBLE创建，避免Decimal进入DB
                field_def = f"`{field_name}` DOUBLE"
            elif field_type == 'BIGINT':
                field_def = f"`{field_name}` {field_type}"
            else:
                # 将任何残留的DECIMAL类型映射为DOUBLE，防止Decimal
                if field_type == 'DECIMAL':
                    field_def = f"`{field_name}` DOUBLE"
                else:
                    field_def = f"`{field_name}` {field_type}"
            
            # 添加约束
            if is_required:
                field_def += " NOT NULL"
            else:
                field_def += " NULL"
            
            # 添加自增约束
            if auto_increment:
                field_def += " AUTO_INCREMENT"
            
            field_definitions.append(field_def)
        
        # 添加主键约束
        if primary_key:
            if isinstance(primary_key, list):
                # 联合主键
                pk_fields = ', '.join([f"`{pk}`" for pk in primary_key])
                field_definitions.append(f"PRIMARY KEY ({pk_fields})")
            else:
                # 单字段主键
                field_definitions.append(f"PRIMARY KEY (`{primary_key}`)")
        
        # 添加索引
        for index in indexes:
            index_name = index['name']
            index_fields = ', '.join([f"`{field}`" for field in index['fields']])
            is_unique = index.get('unique', False)
            
            if is_unique:
                field_definitions.append(f"UNIQUE KEY `{index_name}` ({index_fields})")
            else:
                field_definitions.append(f"KEY `{index_name}` ({index_fields})")
        
        # 生成完整的CREATE TABLE语句
        field_definitions_str = ',\n            '.join(field_definitions)
        sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {field_definitions_str}
        ) ENGINE=InnoDB DEFAULT CHARSET={DB_CONFIG['base']['charset']} COLLATE={DB_CONFIG['base']['charset']}_general_ci;
        """
        return sql

    @staticmethod
    def to_columns_and_values(data_list: List[Dict[str, Any]]) -> Tuple[List[str], List[Tuple]]:
        """将数据列表转换为插入语句的列名和值列表"""
        if not data_list:
            return [], []
        
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        return columns, placeholders

    @staticmethod
    def to_upsert_params(data_list: List[Dict[str, Any]], unique_keys: List[str]) -> Tuple[List[str], List[Tuple], str]:
        """将数据列表转换为 upsert 语句的列名、值列表和 update 子句"""
        if not data_list:
            return [], [], ""
        
        columns = list(data_list[0].keys())
        
        # 检查 unique_keys 是否都在数据列中存在
        missing_keys = [k for k in unique_keys if k not in columns]
        if missing_keys:
            raise ValueError(f"主键字段在数据中缺失: {missing_keys}")
        
        # 构建 update 子句（排除 unique_keys 中的字段）
        update_fields = [k for k in columns if k not in unique_keys]
        update_clause = ', '.join([f"{k} = VALUES({k})" for k in update_fields])
        
        # 构建值列表
        values = [tuple(data[col] for col in columns) for data in data_list]
        
        return columns, values, update_clause



