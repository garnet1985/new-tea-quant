"""
Schema DDL 生成基类 — 字段定义来自 shared/fields，方言由子类 dialect 决定。
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.infra.db.core.engines.shared.sql_identifiers import quote_ddl_identifier
from core.infra.db.core.engines.shared.fields import Field


class SchemaParserBase:
    """将项目 schema dict 转为 CREATE TABLE / INDEX / ADD COLUMN SQL。"""

    dialect: str = "postgresql"

    def quote_identifier(self, name: str) -> str:
        return quote_ddl_identifier(self.dialect, name)

    @staticmethod
    def duckdb_sequence_name(table_name: str, column_name: str) -> str:
        safe_table = str(table_name or "table").replace(".", "_")
        safe_col = str(column_name or "id").replace(".", "_")
        return f"seq_{safe_table}_{safe_col}"

    def generate_create_table_sql(self, schema: Dict) -> str:
        table_name = schema["name"]
        fields = schema["fields"]
        primary_key = schema.get("primaryKey")

        if not isinstance(fields, list):
            raise ValueError(
                f"Schema '{table_name}' 的 'fields' 必须是列表类型，"
                f"但得到 {type(fields).__name__}: {fields}. "
                f"这可能是参数传递错误导致的。"
            )

        field_objects = []
        for field_dict in fields:
            try:
                field_objects.append(Field.from_dict(field_dict))
            except Exception as e:
                raise ValueError(
                    f"字段 '{field_dict.get('name', 'unknown')}' 定义无效: {e}"
                ) from e

        field_defs: List[str] = []
        sequence_stmts: List[str] = []
        comments: List[str] = []
        ddl = self.dialect

        for field_obj in field_objects:
            col_name = self.quote_identifier(field_obj.name)
            if ddl == "duckdb" and field_obj.auto_increment:
                seq_name = self.duckdb_sequence_name(table_name, field_obj.name)
                sequence_stmts.append(
                    f"CREATE SEQUENCE IF NOT EXISTS {seq_name} START 1;"
                )
                field_sql = (
                    f"{col_name} {field_obj.to_sql(ddl)} "
                    f"DEFAULT nextval('{seq_name}')"
                )
            else:
                field_sql = f"{col_name} {field_obj.to_sql(ddl)}"
            field_sql += field_obj.get_not_null_sql()
            field_sql += field_obj.get_default_sql(ddl)
            field_defs.append(field_sql)

            if field_obj.comment and ddl in ("postgresql", "duckdb"):
                escaped_comment = field_obj.comment.replace("'", "''")
                qt = self.quote_identifier(table_name)
                qc = self.quote_identifier(field_obj.name)
                comments.append(
                    f"COMMENT ON COLUMN {qt}.{qc} IS '{escaped_comment}';"
                )

        if primary_key:
            field_defs.append(self._primary_key_definition(primary_key))

        fields_sql = ",\n    ".join(field_defs)
        table_sql_name = self.quote_identifier(table_name)
        create_sql = (
            f"CREATE TABLE IF NOT EXISTS {table_sql_name} (\n    {fields_sql}\n);"
        )

        if comments:
            create_sql += "\n" + "\n".join(comments)

        if sequence_stmts:
            create_sql = "\n".join(sequence_stmts) + "\n" + create_sql

        return create_sql.strip()

    def _primary_key_definition(self, primary_key) -> str:
        if isinstance(primary_key, list):
            pk_fields = ", ".join(self.quote_identifier(f) for f in primary_key)
        else:
            pk_fields = self.quote_identifier(primary_key)
        return f"PRIMARY KEY ({pk_fields})"

    def generate_create_index_sql(self, table_name: str, index: Dict) -> str:
        index_name = index["name"]
        index_fields = index["fields"]
        is_unique = index.get("unique", False)

        unique_keyword = "UNIQUE" if is_unique else ""
        fields_str = ", ".join(self.quote_identifier(f) for f in index_fields)
        table_name_quoted = self.quote_identifier(table_name)
        index_name_quoted = self.quote_identifier(index_name)

        return (
            f"CREATE {unique_keyword} INDEX IF NOT EXISTS {index_name_quoted} "
            f"ON {table_name_quoted} ({fields_str})"
        )

    def generate_add_column_sql(self, table_name: str, field_dict: Dict[str, Any]) -> str:
        fd = dict(field_dict)
        fd["nullable"] = True
        fd["isNullable"] = True
        field_obj = Field.from_dict(fd)
        col = self.quote_identifier(field_obj.name)
        qt = self.quote_identifier(table_name)
        ddl = self.dialect
        frag = f"{col} {field_obj.to_sql(ddl)}"
        frag += field_obj.get_not_null_sql()
        frag += field_obj.get_default_sql(ddl)
        return f"ALTER TABLE {qt} ADD COLUMN {frag}"
