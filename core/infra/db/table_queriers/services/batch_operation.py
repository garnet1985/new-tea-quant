"""
BatchOperation - 批量操作核心逻辑

统一处理批量插入的 SQL 生成和执行逻辑。
"""
import json
import math
from typing import List, Any, Tuple, Optional
from datetime import datetime, date
import logging


logger = logging.getLogger(__name__)


class BatchOperation:
    """批量操作核心类"""
    
    @staticmethod
    def format_value_for_sql(value: Any) -> str:
        """
        格式化单个值为 SQL 字符串
        
        Args:
            value: 要格式化的值
            
        Returns:
            格式化后的 SQL 字符串（不包含引号，除非是字符串类型）
        """
        if value is None:
            return 'NULL'
        elif isinstance(value, str):
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                return 'NULL'
            else:
                return str(value)
        elif isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        elif isinstance(value, (datetime, date)):
            if isinstance(value, datetime):
                return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
            else:
                return f"'{value.strftime('%Y-%m-%d')}'"
        elif isinstance(value, (dict, list)):
            # PostgreSQL json/jsonb 列需要合法 JSON 字符串（双引号），单引号需转义
            s = json.dumps(value, ensure_ascii=False)
            s = s.replace("\\", "\\\\").replace("'", "''")
            return f"'{s}'"
        else:
            escaped_val = str(value).replace("'", "''")
            return f"'{escaped_val}'"
    
    @staticmethod
    def format_batch_values(values_list: List[Tuple[Any, ...]]) -> List[str]:
        """
        格式化批量值为 SQL VALUES 列表
        
        Args:
            values_list: 值元组列表，每个元组代表一行数据
            
        Returns:
            格式化后的 VALUES 列表，每个元素是 "(val1, val2, ...)" 格式
        """
        formatted_list = []
        for val_tuple in values_list:
            formatted_values = [BatchOperation.format_value_for_sql(v) for v in val_tuple]
            formatted_list.append(f"({', '.join(formatted_values)})")
        return formatted_list
    
    @staticmethod
    def build_batch_insert_sql(
        table_name: str,
        columns: List[str],
        values_list: List[str],
        *,
        database_type: str = "postgresql",
        unique_keys: Optional[List[str]] = None,
        update_clause: Optional[str] = None
    ) -> str:
        """
        构建批量插入 SQL 语句
        
        Args:
            table_name: 表名
            columns: 列名列表
            values_list: 格式化后的 VALUES 列表（已包含括号）
            unique_keys: 唯一键列表（用于 ON CONFLICT，可选）
            update_clause: UPDATE 子句（用于 ON CONFLICT DO UPDATE，可选）
            
        Returns:
            完整的 SQL 语句
        """
        # 引用列名（避免 key/text/json 等保留字在 MySQL 报错）
        from core.infra.db.helpers.db_helpers import DBHelper

        dt = DBHelper.normalize_database_type({"database_type": database_type})
        qcols = [DBHelper.quote_identifier_for_dialect(dt, c) for c in columns]
        columns_sql = ", ".join(qcols)
        values_sql = ', '.join(values_list)
        
        if unique_keys:
            if dt == "mysql":
                # MySQL/MariaDB：ON DUPLICATE KEY UPDATE
                # update_clause 形如：col = EXCLUDED.col, ...
                update_fields: List[str] = []
                if update_clause:
                    for part in update_clause.split(","):
                        left = part.split("=", 1)[0].strip()
                        if left:
                            update_fields.append(left)
                else:
                    update_fields = [c for c in columns if c not in unique_keys]

                if update_fields:
                    assigns = ", ".join(
                        f"{DBHelper.quote_identifier_for_dialect(dt, f)} = VALUES({DBHelper.quote_identifier_for_dialect(dt, f)})"
                        for f in update_fields
                    )
                else:
                    # 没有可更新列时，用“主键自赋值”模拟 DO NOTHING
                    uk = unique_keys[0]
                    quk = DBHelper.quote_identifier_for_dialect(dt, uk)
                    assigns = f"{quk} = {quk}"

                return (
                    f"INSERT INTO {table_name} ({columns_sql}) VALUES {values_sql} "
                    f"ON DUPLICATE KEY UPDATE {assigns}"
                )

            # PostgreSQL：ON CONFLICT
            conflict_cols = ", ".join(DBHelper.quote_identifier_for_dialect(dt, k) for k in unique_keys)
            if update_clause:
                # update_clause 由 DBHelper.to_upsert_params 生成，仍为未引用列名；这里补引用
                assigns: List[str] = []
                for part in update_clause.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    left, right = part.split("=", 1)
                    col = left.strip()
                    assigns.append(
                        f"{DBHelper.quote_identifier_for_dialect(dt, col)} = EXCLUDED.{DBHelper.quote_identifier_for_dialect(dt, col)}"
                    )
                update_sql = ", ".join(assigns)
                return (
                    f"INSERT INTO {table_name} ({columns_sql}) VALUES {values_sql} "
                    f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_sql}"
                )
            else:
                return (
                    f"INSERT INTO {table_name} ({columns_sql}) VALUES {values_sql} "
                    f"ON CONFLICT ({conflict_cols}) DO NOTHING"
                )
        else:
            return f"INSERT INTO {table_name} ({columns_sql}) VALUES {values_sql}"
    
    @staticmethod
    def execute_batch_insert(
        executor,
        table_name: str,
        columns: List[str],
        values: List[Tuple[Any, ...]],
        batch_size: int = 5000,
        *,
        database_type: str = "postgresql",
        unique_keys: Optional[List[str]] = None,
        update_clause: Optional[str] = None
    ) -> int:
        """
        执行批量插入（自动分批处理，避免 SQL 语句过长）
        
        Args:
            executor: 执行器对象（可以是 cursor 或 connection，需要有 execute 方法）
            table_name: 表名
            columns: 列名列表
            values: 值元组列表
            batch_size: 每批处理的记录数（默认 5000）
            unique_keys: 唯一键列表（用于 ON CONFLICT，可选）
            update_clause: UPDATE 子句（用于 ON CONFLICT DO UPDATE，可选）
            
        Returns:
            插入的记录数
        """
        if not values:
            return 0
        
        total_inserted = 0
        
        # 分批处理
        for i in range(0, len(values), batch_size):
            batch_values = values[i:i+batch_size]
            
            # 格式化批量值
            formatted_values = BatchOperation.format_batch_values(batch_values)
            
            # 构建 SQL
            sql = BatchOperation.build_batch_insert_sql(
                table_name=table_name,
                columns=columns,
                values_list=formatted_values,
                database_type=database_type,
                unique_keys=unique_keys,
                update_clause=update_clause
            )
            
            # 执行 SQL
            try:
                executor.execute(sql)
                total_inserted += len(batch_values)
            except Exception as e:
                # 如果 ON CONFLICT 失败（unique_keys 不匹配主键/唯一索引），回退到纯 INSERT
                if unique_keys and ("conflict target" in str(e).lower() or "unique" in str(e).lower()):
                    logger.warning(
                        f"表 {table_name} 的 unique_keys {unique_keys} 不匹配主键/唯一索引，"
                        f"回退到纯 INSERT（可能产生重复数据）: {e}"
                    )
                    # 回退到纯 INSERT
                    sql_fallback = BatchOperation.build_batch_insert_sql(
                        table_name=table_name,
                        columns=columns,
                        values_list=formatted_values,
                        database_type=database_type,
                        unique_keys=None,
                        update_clause=None
                    )
                    executor.execute(sql_fallback)
                    total_inserted += len(batch_values)
                else:
                    # 其他错误直接抛出
                    raise
        
        return total_inserted
