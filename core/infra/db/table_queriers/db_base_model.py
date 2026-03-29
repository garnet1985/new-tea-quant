from __future__ import annotations

"""
DbBaseModel - 数据库表操作的通用基类

这是一个纯粹的工具类，封装了常见的数据库表操作，提供：
- 基础 CRUD（增删改查）
- 统计行数（count，支持 WHERE 条件）
- 分页查询
- 时序数据特有的查询（最新日期、最新记录等）
- Upsert（插入或更新）
- 批量操作
- 重试机制

特点：
- 基于 JSON Schema 自动创建表
- 支持参数化查询（防 SQL 注入）
- 针对时序数据优化
- 性能优先（直接 SQL，无 ORM 开销）

使用方式：
    # 方式 1: 直接使用（简单场景）
    from core.infra.db import DbBaseModel
    from core.infra.db import DatabaseManager
    
    db = DatabaseManager()
    db.initialize()
    
    model = DbBaseModel('stock_kline', db)
    records = model.load("id = %s", ('000001.SZ',))
    
    # 方式 2: 继承使用（推荐，业务场景）
    class StockKlineModel(DbBaseModel):
        def __init__(self, db=None):
            super().__init__('stock_kline', db)
        
        def load_by_date_range(self, stock_id, start_date, end_date):
            return self.load(
                "id = %s AND date BETWEEN %s AND %s",
                (stock_id, start_date, end_date),
                order_by="date ASC"
            )

更新日期：2024-12-04
"""
import ast
import math
import logging
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal

from core.infra.db.helpers.db_helpers import DBHelper
from core.infra.db.table_queriers.services.batch_operation import BatchOperation
from core.utils.io import csv_io
from core.utils.io import file_io


logger = logging.getLogger(__name__)


class ExportTemplateKind(Enum):
    """
    导出模板类型：

    - FULL_TABLE: 整表导出，不切块
    - ROW_CHUNK: 按行数切块（预留，当前实现等同于 FULL_TABLE）
    """

    FULL_TABLE = "full_table"
    ROW_CHUNK = "row_chunk"


@dataclass
class ExportTemplate:
    """导出模板元数据（plan 阶段的输出之一）"""

    kind: ExportTemplateKind
    # ROW_CHUNK：每块的行数上限；当前实现暂未按块拆分，仅作为未来扩展预留
    chunk_rows: Optional[int] = None


class DbBaseModel:
    """
    通用表操作模型基类（顶层类，不继承 Helper）

    所有基础表的 Model 类都继承自此类，提供单表的 CRUD 操作。
    """
    
    def __init__(self, table_name: str, db=None):
        """
        初始化表模型

        Args:
            table_name: 表名
            db: DatabaseManager 实例（可选，测试时传入；默认使用 get_default）
        """
        from core.infra.db import DatabaseManager
        self.db = db if db is not None else DatabaseManager.get_default(auto_init=True)
        self.table_name = table_name
        self.schema = self.load_schema()
        self.verbose = False
        self.is_base_table = False

    # ***********************************
    #        table operations
    # ***********************************
    
    def load_schema(self) -> dict:
        """
        加载表的 schema。由基类统一实现：通过 SchemaManager 按 self.table_name
        从 core/tables 下各表目录的 schema.py 加载（按 schema["name"] 索引）；
        子类无需覆盖，只需在 __init__ 中传入正确的 table_name 即可。
        """
        from core.infra.db.schema_management.schema_manager import SchemaManager
        
        # 使用 SchemaManager 加载 schema
        schema_manager = SchemaManager()
        schema = schema_manager.get_table_schema(self.table_name)
        
        if schema:
            return schema
        
        # 如果不存在，可能是策略自定义表（暂不处理）
        logger.warning(f"Schema not found for table {self.table_name}")
        return None

    def create_table(self, custom_table_name: str = None) -> None:
        if not self.schema:
            logger.error(f"Failed create table: {self.table_name}, because schema is not found")
            return

        # 使用 SchemaManager 生成 SQL
        from core.infra.db.schema_management.schema_manager import SchemaManager
        schema_manager = SchemaManager(database_type=self.db.config.get('database_type', 'postgresql'))
        
        # 如果有自定义表名，修改 schema
        schema_to_use = self.schema.copy()
        if custom_table_name:
            schema_to_use['name'] = custom_table_name
        
        sql = schema_manager.generate_create_table_sql(schema_to_use)

        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
            # 详细日志由 logging 配置控制
            logger.debug(f"Table '{self.table_name}' is ready")

    def drop_table(self) -> None:
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            logger.debug(f"Table '{self.table_name}' is dropped")

    def clear_table(self) -> int:
        """清空表数据"""
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.table_name}")
            return cursor.rowcount

    def is_table_empty(self) -> bool:
        """检查表是否为空"""
        return self.count() == 0

    def _validate_column_name(self, name: str) -> None:
        """校验列名，防止 SQL 注入（仅允许字母、数字、下划线）"""
        import re
        if not name or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise ValueError(f"无效的列名: {name!r}，仅允许字母、数字、下划线")

    def _validate_column_type(self, column_type: str) -> None:
        """校验列类型，防止 SQL 注入（允许常见类型如 VARCHAR(255)、DECIMAL(10,2)）"""
        import re
        if not column_type or not re.match(r'^[a-zA-Z0-9_(),\s]+$', column_type.strip()):
            raise ValueError(f"无效的列类型: {column_type!r}")

    def add_column(self, column_name: str, column_type: str) -> None:
        """
        添加列

        Args:
            column_name: 列名
            column_type: 列类型（如 VARCHAR(255)、INTEGER、TEXT、DECIMAL(10,2)）
        """
        self._validate_column_name(column_name)
        self._validate_column_type(column_type)
        sql = f"ALTER TABLE {self.table_name} ADD COLUMN {column_name} {column_type.strip()}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        logger.debug(f"表 {self.table_name} 已添加列: {column_name}")

    def drop_column(self, column_name: str) -> None:
        """
        删除列

        Args:
            column_name: 列名
        """
        self._validate_column_name(column_name)
        sql = f"ALTER TABLE {self.table_name} DROP COLUMN {column_name}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        logger.debug(f"表 {self.table_name} 已删除列: {column_name}")

    def rename_column(self, old_column_name: str, new_column_name: str) -> None:
        """
        重命名列

        Args:
            old_column_name: 原列名
            new_column_name: 新列名
        """
        self._validate_column_name(old_column_name)
        self._validate_column_name(new_column_name)
        sql = f"ALTER TABLE {self.table_name} RENAME COLUMN {old_column_name} TO {new_column_name}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        logger.debug(f"表 {self.table_name} 已将列 {old_column_name} 重命名为 {new_column_name}")

    def modify_column(self, column_name: str, column_type: str) -> None:
        """
        修改列类型

        Args:
            column_name: 列名
            column_type: 新的列类型

        Raises:
            NotImplementedError: SQLite 不支持 ALTER COLUMN，需重建表
        """
        self._validate_column_name(column_name)
        self._validate_column_type(column_type)
        database_type = self.db.config.get('database_type', 'postgresql')
        if database_type == 'sqlite':
            raise NotImplementedError(
                "SQLite 不支持修改列类型。请使用 execute_raw_update 手动重建表，"
                "或迁移到 PostgreSQL/MySQL。"
            )
        if database_type == 'postgresql':
            sql = f"ALTER TABLE {self.table_name} ALTER COLUMN {column_name} TYPE {column_type.strip()}"
        else:
            sql = f"ALTER TABLE {self.table_name} MODIFY COLUMN `{column_name}` {column_type.strip()}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        logger.debug(f"表 {self.table_name} 已将列 {column_name} 类型修改为 {column_type}")

    def get_primary_keys(self) -> List[str]:
        """从 schema 中获取主键列表"""
        if not hasattr(self, 'schema') or not self.schema:
            raise ValueError(f"表 {self.table_name} 没有 schema 信息")
        primary_key = self.schema.get('primaryKey')
        if not primary_key:
            raise ValueError(f"表 {self.table_name} 的 schema 中未配置主键")
        if isinstance(primary_key, str):
            return [primary_key]
        if isinstance(primary_key, list):
            return primary_key
        raise ValueError(f"表 {self.table_name} 的主键格式不正确: {primary_key}")

    # ***********************************
    #        generic export / import
    # ***********************************

    def _default_export_template(self) -> ExportTemplate:
        """
        返回当前表的默认导出模板。

        策略：
        - 默认使用 FULL_TABLE
        - 如行数超过一定阈值，则改用 ROW_CHUNK（按行数分块导出）
        """
        try:
            total = self.count()
        except Exception:
            total = 0

        # 行数较大时，使用按行数分块导出的模板（预留接口，当前实现仍生成多文件）
        ROW_CHUNK_THRESHOLD = 500_000
        DEFAULT_CHUNK_ROWS = 500_000

        if total > ROW_CHUNK_THRESHOLD:
            return ExportTemplate(kind=ExportTemplateKind.ROW_CHUNK, chunk_rows=DEFAULT_CHUNK_ROWS)

        return ExportTemplate(kind=ExportTemplateKind.FULL_TABLE)

    def _rows_to_csv_bytes(self, rows: List[Dict[str, Any]]) -> bytes:
        """
        将行列表序列化为 CSV（二进制），使用 DictWriter。
        """
        return csv_io.dicts_to_csv_bytes(rows)

    def export_data(
        self,
        output_dir: str | Path,
        *,
        archive_format: Literal["tar.gz", "zip"] = "tar.gz",
        template: Optional[ExportTemplate] = None,
        condition: str = "1=1",
        params: tuple = (),
    ) -> List[Path]:
        """
        通用导出：把当前表的数据导出为一个或多个归档文件。

        - condition / params: 过滤条件（WHERE 子句 + 参数），默认为全表
        - FULL_TABLE: 符合条件的全部数据导出为单个归档
        - ROW_CHUNK: 符合条件的数据按行数分块导出，每块一个归档文件
        """
        tpl = template or self._default_export_template()
        if tpl.kind not in (ExportTemplateKind.FULL_TABLE, ExportTemplateKind.ROW_CHUNK):
            raise ValueError(f"不支持的导出模板类型: {tpl.kind}")

        # 目标目录
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        paths: List[Path] = []

        # 导出排序：优先按主键稳定排序，避免不同批次/不同执行计划下行序不一致。
        export_order_by: Optional[str] = None
        try:
            pks = self.get_primary_keys()
            if pks:
                export_order_by = ", ".join([f"{k} ASC" for k in pks])
        except Exception:
            export_order_by = None

        if tpl.kind == ExportTemplateKind.FULL_TABLE or not tpl.chunk_rows:
            # 整表（或条件过滤后的全集）一次性导出
            try:
                rows = self.load(
                    condition=condition,
                    params=params,
                    order_by=export_order_by,
                )
            except Exception as e:
                logger.error("导出表 %s 失败（FULL_TABLE 导出）: %s", self.table_name, e)
                raise

            csv_bytes = self._rows_to_csv_bytes(rows)
            archive_path = file_io.write_archive(
                out_dir,
                archive_name=self.table_name,
                files={f"{self.table_name}.csv": csv_bytes},
                format="tar.gz" if archive_format == "tar.gz" else "zip",
            )
            logger.info("导出表 %s -> %s (行数=%d)", self.table_name, archive_path.name, len(rows))
            paths.append(archive_path)
            return paths

        # ROW_CHUNK: 按行数切块导出
        # 使用 LIMIT/OFFSET 方案分批拉取，生成多个归档文件
        try:
            total_rows = self.count(condition=condition, params=params)
        except Exception as e:
            logger.error("统计表 %s 行数失败，无法分块导出: %s", self.table_name, e)
            raise

        chunk_size = max(1, int(tpl.chunk_rows))
        if total_rows <= 0:
            # 无数据，直接返回空列表
            logger.info("表 %s 无数据可导出（分块导出跳过）", self.table_name)
            return paths

        total_parts = (total_rows + chunk_size - 1) // chunk_size
        offset = 0
        part_index = 1

        while offset < total_rows:
            try:
                rows = self.load(
                    condition=condition,
                    params=params,
                    order_by=export_order_by,
                    limit=chunk_size,
                    offset=offset,
                )
            except Exception as e:
                logger.error(
                    "分块导出表 %s 失败（offset=%d, chunk_size=%d）: %s",
                    self.table_name,
                    offset,
                    chunk_size,
                    e,
                )
                raise

            if not rows:
                break

            csv_bytes = self._rows_to_csv_bytes(rows)
            archive_name = f"{self.table_name}_part{part_index}"
            archive_path = file_io.write_archive(
                out_dir,
                archive_name=archive_name,
                files={f"{self.table_name}.csv": csv_bytes},
                format="tar.gz" if archive_format == "tar.gz" else "zip",
            )
            logger.info(
                "分块导出表 %s -> %s (part=%d/%d, 行数=%d, offset=%d)",
                self.table_name,
                archive_path.name,
                part_index,
                total_parts,
                len(rows),
                offset,
            )
            paths.append(archive_path)

            offset += len(rows)
            part_index += 1

        return paths

    def _read_csv_rows_from_archive(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        从 .tar.gz/.zip/.csv 文件中读取当前表的 CSV 行。
        """
        file_path = Path(file_path)
        if file_path.suffix.lower() == ".csv":
            return csv_io.read_csv_to_dicts(file_path)

        # 归档文件：tar.gz / zip
        files_bytes = file_io.read_archive_files(file_path, filter_ext=".csv")
        if not files_bytes:
            return []

        # 优先匹配与表名一致的 CSV，其次取第一个
        target_name = f"{self.table_name}.csv"
        if target_name in files_bytes:
            data = files_bytes[target_name]
        else:
            # 任取一个 CSV
            _, data = next(iter(files_bytes.items()))

        return csv_io.csv_bytes_to_dicts(data)

    def _ensure_import_target_with_cursor(
        self,
        cursor,
        source_sql: str,
        target_sql: str,
    ) -> None:
        """
        当目标与源不是同一张表时，按源表结构创建空目标表（PostgreSQL 会先 DROP 再建）。
        """
        if source_sql == target_sql:
            return
        db_type = DBHelper.normalize_database_type(self.db.config)
        if db_type == "postgresql":
            cursor.execute(f"DROP TABLE IF EXISTS {target_sql}")
            cursor.execute(
                f"CREATE TABLE {target_sql} AS SELECT * FROM {source_sql} WHERE 1=0"
            )
        elif db_type == "mysql":
            cursor.execute(f"DROP TABLE IF EXISTS {target_sql}")
            cursor.execute(f"CREATE TABLE {target_sql} LIKE {source_sql}")
        elif db_type == "sqlite":
            cursor.execute(f"DROP TABLE IF EXISTS {target_sql}")
            cursor.execute(
                f"CREATE TABLE {target_sql} AS SELECT * FROM {source_sql} WHERE 1=0"
            )
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        logger.info("已为目标表建立结构: %s <- %s", target_sql, source_sql)

    def _normalize_json_for_import(self, value: Any) -> Any:
        """
        CSV 中 json 列常见：空串、合法 JSON、或 Python repr（单引号，非标准 JSON）。
        PostgreSQL json/jsonb 需要合法 JSON 文本或 NULL。
        """
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, bool):
            return json.dumps(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return json.dumps(value)
        if isinstance(value, str):
            s = value.strip()
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(s)
                except (ValueError, SyntaxError, MemoryError) as e:
                    logger.warning(
                        "JSON 列无法解析，将写入 NULL: %r (%s)", value, e
                    )
                    return None
            if parsed is None:
                return None
            if isinstance(parsed, (dict, list)):
                return json.dumps(parsed, ensure_ascii=False)
            if isinstance(parsed, (str, int, float, bool)):
                return json.dumps(parsed, ensure_ascii=False)
            logger.warning("JSON 列解析为非常规类型 %s，将写入 NULL", type(parsed))
            return None
        logger.warning("JSON 列不支持的类型 %s，将写入 NULL", type(value))
        return None

    # CSV 空串对 PG 数值/时间/布尔列非法，须映射为 NULL（varchar/text 可保留 ''）
    _PG_EMPTY_TO_NULL_TYPES = frozenset(
        {
            "float",
            "double",
            "decimal",
            "numeric",
            "real",
            "int",
            "integer",
            "bigint",
            "smallint",
            "tinyint",
            "serial",
            "bigserial",
            "boolean",
            "bool",
            "date",
            "datetime",
            "time",
            "timestamp",
            "timestamptz",
        }
    )

    def _coerce_import_cell_value(self, field_name: str, value: Any) -> Any:
        """
        按 schema 规范导入值：
        - json/jsonb：空串→NULL，Python repr→合法 JSON 字符串
        - 数值/日期/布尔：空串→NULL（PostgreSQL 不接受 '' 作为 double precision 等）
        """
        if not self.schema:
            return value
        type_map = {
            f["name"]: str(f.get("type", "")).lower()
            for f in self.schema.get("fields", [])
        }
        t = type_map.get(field_name, "")
        if t in ("json", "jsonb"):
            return self._normalize_json_for_import(value)
        if (
            isinstance(value, str)
            and not value.strip()
            and t in self._PG_EMPTY_TO_NULL_TYPES
        ):
            return None
        return value

    def _compute_insert_batch_size(self, num_columns: int) -> int:
        """
        多行一条 INSERT 时的行数上限。

        PostgreSQL / MySQL：单语句占位符有上限（PG 约 65535），故实际为
        min(目标上限, 65535 // 列数)。列很多时批次会低于目标上限，属正常。
        SQLite：受 SQLITE_MAX_VARIABLE_NUMBER（默认 999）约束。
        """
        nc = max(num_columns, 1)
        t = DBHelper.normalize_database_type(self.db.config)
        # 目标：宽表自动缩小批次；窄表可一次合并上万行
        _cap_pg_mysql = 10_000
        if t == "sqlite":
            return max(1, min(400, 999 // nc))
        if t == "postgresql":
            return max(1, min(_cap_pg_mysql, 65535 // nc))
        return max(1, min(_cap_pg_mysql, 65535 // nc))

    def _import_log_progress_after_chunk(
        self,
        *,
        n: int,
        processed: int,
        last_logged_pct: int,
        large_hint_threshold: int,
        target_sql: str,
        archive_name: str,
    ) -> int:
        if n < large_hint_threshold:
            return last_logged_pct

        pct = int((processed * 100) // n)
        # 仅在每 10% 节点打印一次，避免日志刷屏
        next_mark = ((last_logged_pct // 10) + 1) * 10
        while next_mark <= min(pct, 100):
            m = int((next_mark / 100.0) * n)
            pct_text = f"{float(next_mark):.1f}%"
            logger.info(
                "导入进度 %s -> %s [%s]: %d/%d 行 (%s)",
                self.table_name,
                target_sql,
                archive_name,
                m if next_mark < 100 else n,
                n,
                pct_text,
            )
            next_mark += 10

        if pct >= 100:
            return 100
        return max(last_logged_pct, (pct // 10) * 10)

    def _insert_rows_batched(
        self,
        cursor,
        target_sql: str,
        field_names: List[str],
        rows: List[Dict[str, Any]],
        *,
        batch_size: int,
        large_hint_threshold: int,
        archive_name: str,
    ) -> int:
        """多行 VALUES 批量插入；返回插入行数。"""
        col_list = ", ".join(field_names)
        one_row = "(" + ", ".join(["%s"] * len(field_names)) + ")"
        n = len(rows)
        if n == 0:
            return 0

        if n >= large_hint_threshold:
            logger.info(
                "表 %s 本归档「%s」共 %d 行，使用批量 INSERT（每批约 %d 行），"
                "大表仍可能耗时数分钟（每 10%% 输出进度）",
                self.table_name,
                archive_name,
                n,
                batch_size,
            )

        last_logged_pct = 0
        for start in range(0, n, batch_size):
            chunk = rows[start : start + batch_size]
            values_clause = ", ".join([one_row] * len(chunk))
            insert_sql = f"INSERT INTO {target_sql} ({col_list}) VALUES {values_clause}"
            flat: List[Any] = []
            for row in chunk:
                for col in field_names:
                    flat.append(self._coerce_import_cell_value(col, row.get(col)))
            cursor.execute(insert_sql, tuple(flat))

            processed = start + len(chunk)
            last_logged_pct = self._import_log_progress_after_chunk(
                n=n,
                processed=processed,
                last_logged_pct=last_logged_pct,
                large_hint_threshold=large_hint_threshold,
                target_sql=target_sql,
                archive_name=archive_name,
            )
        return n

    def _insert_rows_execute_values(
        self,
        pg_cursor,
        target_sql: str,
        field_names: List[str],
        rows: List[Dict[str, Any]],
        *,
        batch_size: int,
        large_hint_threshold: int,
        archive_name: str,
    ) -> int:
        """PostgreSQL：psycopg2.extras.execute_values 批量展开 VALUES，减少客户端拼接与往返。"""
        from psycopg2.extras import execute_values

        col_list = ", ".join(field_names)
        sql = f"INSERT INTO {target_sql} ({col_list}) VALUES %s"
        n = len(rows)
        if n == 0:
            return 0

        if n >= large_hint_threshold:
            logger.info(
                "表 %s 本归档「%s」共 %d 行，使用 execute_values（每批约 %d 行），"
                "大表仍可能耗时数分钟（每 10%% 输出进度）",
                self.table_name,
                archive_name,
                n,
                batch_size,
            )

        last_logged_pct = 0
        for start in range(0, n, batch_size):
            chunk = rows[start : start + batch_size]
            tuples = [
                tuple(
                    self._coerce_import_cell_value(col, row.get(col))
                    for col in field_names
                )
                for row in chunk
            ]
            execute_values(pg_cursor, sql, tuples, page_size=len(tuples))

            processed = start + len(chunk)
            last_logged_pct = self._import_log_progress_after_chunk(
                n=n,
                processed=processed,
                last_logged_pct=last_logged_pct,
                large_hint_threshold=large_hint_threshold,
                target_sql=target_sql,
                archive_name=archive_name,
            )
        return n

    def _import_data_file_loop(
        self,
        cursor,
        target_sql: str,
        files: List[str | Path],
        insert_batch_size: Optional[int],
        *,
        pg_execute_values: bool,
    ) -> int:
        """在已清空的目标表上逐文件读 CSV 并批量插入。"""
        _LARGE_IMPORT_HINT = 20_000
        field_names: Optional[List[str]] = None
        total_rows = 0
        for file in files:
            path = Path(file)
            rows = self._read_csv_rows_from_archive(path)
            if not rows:
                continue
            if field_names is None:
                field_names = list(rows[0].keys())

            # 覆盖导入时，归档内若存在重复主键会触发 UNIQUE 约束错误；
            # 这里按主键去重（保留最后一条），避免单包脏数据中断整表导入。
            try:
                pks = self.get_primary_keys()
            except Exception:
                pks = []
            if pks and all(pk in rows[0] for pk in pks):
                dedup_map: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
                for row in rows:
                    k = tuple(row.get(pk) for pk in pks)
                    dedup_map[k] = row
                if len(dedup_map) < len(rows):
                    removed = len(rows) - len(dedup_map)
                    rows = list(dedup_map.values())
                    logger.warning(
                        "导入前按主键去重: %s [%s] 移除重复行 %d（主键=%s）",
                        self.table_name,
                        path.name,
                        removed,
                        ",".join(pks),
                    )

            bs = insert_batch_size
            if bs is None:
                bs = self._compute_insert_batch_size(len(field_names))

            if pg_execute_values:
                total_rows += self._insert_rows_execute_values(
                    cursor,
                    target_sql,
                    field_names,
                    rows,
                    batch_size=bs,
                    large_hint_threshold=_LARGE_IMPORT_HINT,
                    archive_name=path.name,
                )
            else:
                total_rows += self._insert_rows_batched(
                    cursor,
                    target_sql,
                    field_names,
                    rows,
                    batch_size=bs,
                    large_hint_threshold=_LARGE_IMPORT_HINT,
                    archive_name=path.name,
                )
        return total_rows

    def _import_data_overwrite_run(
        self,
        cursor,
        source_sql: str,
        target_sql: str,
        files: List[str | Path],
        insert_batch_size: Optional[int],
        *,
        pg_execute_values: bool,
    ) -> int:
        self._ensure_import_target_with_cursor(cursor, source_sql, target_sql)
        cursor.execute(f"DELETE FROM {target_sql}")
        logger.info("已清空表: %s", target_sql)
        return self._import_data_file_loop(
            cursor,
            target_sql,
            files,
            insert_batch_size,
            pg_execute_values=pg_execute_values,
        )

    def import_data(
        self,
        files: List[str | Path],
        *,
        mode: Literal["overwrite", "replace"] = "overwrite",
        target_table: Optional[str] = None,
        insert_batch_size: Optional[int] = None,
    ) -> None:
        """
        overwrite：按需建目标表、DELETE 清空、再导入。target 与源不同名时见
        `_ensure_import_target_with_cursor`。insert_batch_size 默认按列数与驱动占位符上限估算。

        PG：adapter 事务 + execute_values；MySQL：事务 + 多行 VALUES；SQLite：DatabaseCursor + 多行 VALUES（999 变量上限）。
        """
        if mode not in ("overwrite", "replace"):
            raise ValueError(f"未知导入模式: {mode}")

        if mode == "replace":
            raise NotImplementedError("replace 模式（按主键替换行）尚未实现")

        if not files:
            logger.info("未提供任何文件，跳过导入表 %s", self.table_name)
            return

        source_sql = DBHelper.sql_qualify_table_name(self.db.config, self.table_name)
        target_logical = (target_table or self.table_name).strip()
        target_sql = DBHelper.sql_qualify_table_name(self.db.config, target_logical)

        db_type = DBHelper.normalize_database_type(self.db.config)
        pg_ev = db_type == "postgresql"
        ctx = (
            self.db.connection_manager.transaction
            if db_type in ("postgresql", "mysql")
            else self.db.get_sync_cursor
        )
        with ctx() as cursor:
            total_rows = self._import_data_overwrite_run(
                cursor,
                source_sql,
                target_sql,
                files,
                insert_batch_size,
                pg_execute_values=pg_ev,
            )

        logger.info("导入表 %s -> %s 完成，共导入 %d 行", self.table_name, target_sql, total_rows)


    # ***********************************
    #        data count & exists operations
    # ***********************************

    def count(self, condition: str = "1=1", params: tuple = ()) -> int:
        """
        统计表记录数（支持条件过滤）。

        Args:
            condition: WHERE 条件，默认 "1=1" 表示全表统计。须使用占位符时用 %s，与 params 配合。
            params: 条件参数元组，与 condition 中的 %s 一一对应。

        Returns:
            int: 满足条件的行数；表不存在或查询失败时返回 0。

        示例:
            model.count()                    # 全表行数
            model.count("term = %s", ("daily",))  # term=daily 的行数
        """
        try:
            query = f"SELECT COUNT(*) AS cnt FROM {self.table_name} WHERE {condition}"
            result = self.db.execute_sync_query(query, params)
            if not result or len(result) == 0:
                return 0
            row = result[0]
            # 兼容不同驱动返回的列名（cnt / count / COUNT 等）
            n = row.get("cnt") if "cnt" in row else row.get("count", 0)
            if n is None:
                return 0
            return int(n)
        except Exception as e:
            logger.error(f"Failed to count records from {self.table_name}: {e}")
            return 0

    def is_exists(self, condition: str, params: tuple = ()) -> bool:
        """检查记录是否存在"""
        return self.count(condition, params) > 0

    # ***********************************
    #        data get operations
    # ***********************************

    def load(self, condition: str = "1=1", params: tuple = (), order_by: str = None, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """查找记录"""
        query = f"SELECT * FROM {self.table_name} WHERE {condition}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        try:
            return self.db.execute_sync_query(query, params)
        except Exception as e:
            logger.error(f"Failed to load records from {self.table_name}: {e}")
            return []

    def load_one(self, condition: str = "1=1", params: tuple = (), order_by: str = None) -> Optional[Dict[str, Any]]:
        result = self.load(condition, params, order_by, limit=1)
        return result[0] if result else None

    def load_all(self, condition: str = "1=1", params: tuple = (), order_by: str = None) -> List[Dict[str, Any]]:
        return self.load(condition, params, order_by)
    
    def load_many(self, condition: str = "1=1", params: tuple = (), limit: int = None, order_by: str = None, offset: int = None) -> List[Dict[str, Any]]:
        return self.load(condition, params, order_by, limit, offset)

    def load_paginated(self, page: int = 1, page_size: int = 20, order_by: str = None) -> Dict[str, Any]:
        """分页获取记录"""
        offset = (page - 1) * page_size
        
        # 获取总数
        total = self.count()
        
        # 获取当前页数据（直接使用 load）
        data = self.load(
            condition="1=1",
            params=(),
            order_by=order_by,
            limit=page_size,
            offset=offset,
        )
        
        return {
            'data': data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    def load_first(self, date_field: str) -> Optional[Dict[str, Any]]:
        """
        加载最早一条记录
        
        Args:
            date_field: 用于排序的日期字段名（例如 'date'、'trade_date' 等）
        """
        return self.load_one("1=1", order_by=f"{date_field} ASC")

    def load_firsts(self, date_field: str, group_fields: List[str]) -> List[Dict[str, Any]]:
        """
        加载每个分组中最早日期的记录

        Args:
            date_field: 日期字段名（用于取 MIN）
            group_fields: 分组字段列表（GROUP BY 的字段）
        """
        if not group_fields:
            raise ValueError("group_fields 不能为空，需传入至少一个分组字段")
        group_fields_str = ', '.join(group_fields)
        query = f"""
            SELECT t1.*
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_fields_str}, MIN({date_field}) as min_date
                FROM {self.table_name}
                GROUP BY {group_fields_str}
            ) t2
            ON {' AND '.join([f't1.{f} = t2.{f}' for f in group_fields])}
            AND t1.{date_field} = t2.min_date
        """
        try:
            return self.db.execute_sync_query(query)
        except Exception as e:
            logger.error(f"加载最早记录失败 [{self.table_name}]: {e}")
            return []


    def load_latest(self, date_field: str) -> Optional[Dict[str, Any]]:
        """
        加载最新一条记录

        Args:
            date_field: 用于排序的日期字段名（例如 'date'、'trade_date' 等）
        """
        return self.load_one("1=1", order_by=f"{date_field} DESC")

    def load_latests(self, date_field: str, group_fields: List[str]) -> List[Dict[str, Any]]:
        """
        加载每个分组中最新日期的记录

        Args:
            date_field: 日期字段名（用于取 MAX）
            group_fields: 分组字段列表（GROUP BY 的字段）
        """
        if not group_fields:
            raise ValueError("group_fields 不能为空，需传入至少一个分组字段")
        group_fields_str = ', '.join(group_fields)
        query = f"""
            SELECT t1.*
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_fields_str}, MAX({date_field}) as max_date
                FROM {self.table_name}
                GROUP BY {group_fields_str}
            ) t2
            ON {' AND '.join([f't1.{f} = t2.{f}' for f in group_fields])}
            AND t1.{date_field} = t2.max_date
        """
        try:
            return self.db.execute_sync_query(query)
        except Exception as e:
            logger.error(f"加载最新记录失败 [{self.table_name}]: {e}")
            return []

    def load_latest_date(self, date_field: str) -> Optional[str]:
        latest_record = self.load_latest(date_field)
        return latest_record[date_field] if latest_record else None

    # ***********************************
    #        data delete operations
    # ***********************************
    
    def delete(self, condition: str, params: tuple = (), limit: int = None) -> int:
        """删除数据（带重试机制）"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                query = f"DELETE FROM {self.table_name} WHERE {condition}"
                if limit:
                    query += f" LIMIT {limit}"
                
                with self.db.get_sync_cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.rowcount
            except Exception as e:
                logger.error(f"Failed to delete data from {self.table_name} (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt == max_retries - 1:
                    return 0  # 最后一次尝试失败，返回0
                
                # 等待后重试
                import time
                time.sleep(retry_delay * (2 ** attempt))
                continue
        
        return 0

    def delete_one(self, condition: str, params: tuple = ()) -> int:
        """删除单条数据"""
        return self.delete(condition, params, 1)


    def delete_many(self, data_list: List[Dict[str, Any]]) -> int:
        """删除多条数据"""
        pass

    def delete_all(self) -> int:
        """删除所有数据"""
        return self.clear_table()


    # ***********************************
    #        data insert & update operations
    # ***********************************

    def _get_insert_batch_size(self) -> int:
        """从配置中获取 insert_batch_size"""
        batch_config = self.db.config.get('batch_write', {})
        advanced_config = batch_config.get('_advanced', {})
        return advanced_config.get('insert_batch_size', 5000)
    
    def insert(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None, use_batch: bool = False) -> int:
        """
        核心插入 API（同步）。
        
        - 支持单条或多条（由 data_list 长度决定）
        - 默认行为：**同步写入**，调用返回时数据已落库
        - 内部统一通过批次实现（_batch_insert）
        """
        if not data_list:
            return 0
        # 统一走批次实现
        return self.batch_insert(data_list, unique_keys)

    def insert_async(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        核心插入 API（异步，使用批量写入队列）。
        
        - 适合高并发、大批量写入场景
        - 调用返回时数据**可能尚未真正写入数据库**，由后台队列按 batch_size/flush_interval 决定实际落库时间
        """
        if not data_list:
            return 0

        try:
            def write_callback(table_name, count):
                logger.debug(f"Insert completed for {table_name}: {count} records")

            if hasattr(self.db, "queue_write"):
                keys = unique_keys if unique_keys else []
                self.db.queue_write(self.table_name, data_list, keys, write_callback)
                return len(data_list)

            # 无队列时退化为同步批次插入
            return self.batch_insert(data_list, unique_keys)
        except Exception as e:
            logger.error(f"Failed to insert data into {self.table_name} (async): {e}")
            return 0
    
    def batch_insert(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        显式批量插入数据（同步执行，内部批次实现）
        
        使用批量 VALUES 语法，自动分批处理，避免 SQL 语句过长。
        适合单线程场景或需要立即返回结果的场景。
        
        Args:
            data_list: 数据列表
            unique_keys: 唯一键列表（可选）。如果提供，将使用 INSERT ... ON CONFLICT DO NOTHING
                        如果不提供，使用纯 INSERT（可能重复插入）
        
        Returns:
            插入的记录数
        """
        if not data_list:
            return 0
        
        try:
            # 准备数据
            if unique_keys:
                columns, values, update_clause = DBHelper.to_upsert_params(data_list, unique_keys)
            else:
                columns, _ = DBHelper.to_columns_and_values(data_list)
                values = [tuple(data[col] for col in columns) for data in data_list]
                update_clause = None
            
            if not columns:
                return 0
            
            # 获取批量大小配置
            batch_size = self._get_insert_batch_size()
            
            # 使用 BatchInsertHelper 执行批量插入
            with self.db.get_sync_cursor() as cursor:
                return BatchOperation.execute_batch_insert(
                    executor=cursor,
                    table_name=self.table_name,
                    columns=columns,
                    values=values,
                    batch_size=batch_size,
                    unique_keys=unique_keys if unique_keys else None,
                    update_clause=update_clause
                )
        except Exception as e:
            logger.error(f"Failed to batch insert data into {self.table_name}: {e}")
            return 0
    

    def insert_one(self, data: Dict[str, Any]) -> int:
        """插入单条数据（wrapper，内部调用 insert）"""
        return self.insert([data])

    def insert_many(self, rows: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        批量插入（同步）。

        建议在业务层统一使用本方法处理多行插入：
        - 内部使用批次逻辑（batch_insert），调用返回时数据已落库。
        - unique_keys 不为空时，将使用 INSERT ... ON CONFLICT DO NOTHING 语义。
        """
        return self.insert(rows, unique_keys)

    def insert_many_async(self, rows: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        批量插入（异步，使用写入队列）。

        - 适合高并发、大批量写入场景。
        - 返回值为入队行数，实际落库由后台线程按 batch_size/flush_interval 决定。
        - 新代码建议优先使用本方法，而不是直接调用 insert_async。
        """
        return self.insert_async(rows, unique_keys)



    # ***********************************
    #        data upsert operations（统一使用 upsert 命名）
    # ***********************************

    def upsert(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        核心 Upsert API（同步，多条）。
        """
        return self._batch_upsert(rows, unique_keys)

    def upsert_async(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        核心 Upsert API（异步，多条）。
        """
        if not rows:
            return 0
        try:
            def write_callback(table_name, count):
                logger.debug(f"Upsert completed for {table_name}: {count} records")
            if hasattr(self.db, "queue_write"):
                self.db.queue_write(self.table_name, rows, unique_keys, write_callback)
                return len(rows)
            return self._batch_upsert(rows, unique_keys)
        except Exception as e:
            logger.error(f"Failed to upsert data in {self.table_name} (async): {e}")
            return 0

    def _batch_upsert(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        内部实现：按批次同步执行 upsert（INSERT ... ON CONFLICT DO UPDATE）。
        不对外暴露，由 upsert_one / upsert_many 调用。
        """
        if not rows:
            return 0
        try:
            columns, values, update_clause = DBHelper.to_upsert_params(rows, unique_keys)
            if not columns:
                return 0
            batch_size = self._get_insert_batch_size()
            with self.db.get_sync_cursor() as cursor:
                return BatchOperation.execute_batch_insert(
                    executor=cursor,
                    table_name=self.table_name,
                    columns=columns,
                    values=values,
                    batch_size=batch_size,
                    unique_keys=unique_keys,
                    update_clause=update_clause
                )
        except Exception as e:
            logger.error(f"Failed to upsert data in {self.table_name}: {e}")
            return 0

    def upsert_one(self, row: Dict[str, Any], unique_keys: List[str]) -> int:
        """
        Upsert 单条数据（同步，wrapper）。
        """
        return self.upsert([row], unique_keys)

    def upsert_many(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        Upsert 多条数据（同步，wrapper）。
        """
        return self.upsert(rows, unique_keys)

    def upsert_many_async(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        Upsert 多条数据（异步，wrapper）。
        """
        return self.upsert_async(rows, unique_keys)

    
    # ***********************************
    #        support raw query operations
    # ***********************************
    def execute_raw_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行原始SQL查询"""
        try:
            return self.db.execute_sync_query(query, params)
        except Exception as e:
            logger.error(f"Failed to execute raw query: {e}")
            return []

    def execute_raw_update(self, query: str, params: tuple = ()) -> int:
        """执行原始SQL更新语句"""
        try:
            # 转换占位符 %s -> ?
            query = query.replace("%s", "?")
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to execute raw update: {e}")
            return 0


    # ***********************************
    #        others
    # ***********************************
    def wait_for_writes(self):
        """等待所有异步写入完成"""
        if hasattr(self.db, 'wait_for_writes'):
            self.db.wait_for_writes()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if hasattr(self.db, 'get_stats'):
            return self.db.get_stats()
        return {}
