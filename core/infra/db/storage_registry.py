"""
StorageRegistry - 运行时数据库类型与表→存储域映射

在 DatabaseManager 初始化时构建并缓存，供 get_table 路由与 DuckDB 多文件连接使用。
详见 docs/storage-domains.md
"""
from __future__ import annotations

from typing import Dict, Optional, FrozenSet

STORAGE_DOMAINS: FrozenSet[str] = frozenset({"data", "tag", "strategy"})
PRIMARY_DUCKDB_DOMAIN = "data"


def normalize_storage_domain(raw: Optional[str], *, table_name: str = "") -> str:
    """校验并归一化 storage_domain 枚举值（必须显式提供）。"""
    if raw is None or not str(raw).strip():
        raise ValueError(
            f"表 {table_name!r} 缺少 storage_domain，"
            f"允许值: {', '.join(sorted(STORAGE_DOMAINS))}"
        )
    domain = str(raw).strip().lower()
    if domain not in STORAGE_DOMAINS:
        raise ValueError(
            f"表 {table_name!r} 的 storage_domain={raw!r} 无效，"
            f"允许值: {', '.join(sorted(STORAGE_DOMAINS))}"
        )
    return domain


class StorageRegistry:
    """
    进程内只读注册表：database_type + 表名 → storage_domain。

    每张表的 storage_domain 必须在 schema 中显式声明。
    """

    def __init__(self, database_type: str) -> None:
        self.database_type = str(database_type or "postgresql").lower()
        self._table_to_domain: Dict[str, str] = {}

    @property
    def is_duckdb(self) -> bool:
        return self.database_type == "duckdb"

    @property
    def table_to_domain(self) -> Dict[str, str]:
        """表名 → 域 的浅拷贝（只读使用）。"""
        return dict(self._table_to_domain)

    def register_table(self, table_name: str, domain: str) -> None:
        """注册或覆盖单表域映射。"""
        name = str(table_name or "").strip()
        if not name:
            raise ValueError("register_table: table_name 不能为空")
        d = normalize_storage_domain(domain, table_name=name)
        existing = self._table_to_domain.get(name)
        if existing is not None and existing != d:
            raise ValueError(
                f"表 {name!r} 的 storage_domain 冲突: 已注册为 {existing!r}，"
                f"本次为 {d!r}"
            )
        self._table_to_domain[name] = d

    def register_schema(self, schema: Dict) -> None:
        """从 schema dict 注册（要求显式 storage_domain）。"""
        if not schema or not isinstance(schema, dict):
            raise ValueError("register_schema: schema 不能为空")
        table_name = schema.get("name")
        if not table_name:
            raise ValueError("register_schema: schema 缺少 name")
        domain = normalize_storage_domain(
            schema.get("storage_domain"), table_name=str(table_name)
        )
        self.register_table(str(table_name), domain)

    def register_schemas(self, schemas: Dict[str, Dict]) -> None:
        """批量注册 {table_name: schema_dict}。"""
        for _key, schema in (schemas or {}).items():
            if schema:
                self.register_schema(schema)

    def get_domain(self, table_name: str) -> str:
        """查询表所属域；未注册则抛出 KeyError。"""
        name = str(table_name or "").strip()
        if name not in self._table_to_domain:
            raise KeyError(f"表 {name!r} 未注册到 StorageRegistry")
        return self._table_to_domain[name]

    def tables_in_domain(self, domain: str) -> Dict[str, str]:
        """返回某域下所有表 {table_name: domain}。"""
        d = normalize_storage_domain(domain)
        return {t: dom for t, dom in self._table_to_domain.items() if dom == d}
