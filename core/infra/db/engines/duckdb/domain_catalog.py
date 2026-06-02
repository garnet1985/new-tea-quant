"""
DuckdbDomainCatalog — 运行时表 → 域 → .duckdb 文件映射（内存，由 schema 动态构建）。

配置里只声明三域的 ``db_path``；每张表来自 ``schema.storage_domain``，不在 JSON 里逐表列举。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, TYPE_CHECKING

from core.infra.db.helpers.duckdb_paths import resolve_duckdb_db_path
from core.infra.db.storage_registry import (
    PRIMARY_DUCKDB_DOMAIN,
    STORAGE_DOMAINS,
    normalize_storage_domain,
)

if TYPE_CHECKING:
    from core.infra.db.engines.duckdb.settings import DuckdbSettings


@dataclass(frozen=True)
class DuckdbTableFileMap:
    """单张表对应的库文件信息。"""

    table_name: str
    domain: str
    db_path: str
    """配置中的相对或绝对路径（未解析前）。"""
    absolute_path: str
    """解析到 userspace/system/db 后的绝对路径。"""

    def as_dict(self) -> Dict[str, str]:
        return {
            "table_name": self.table_name,
            "domain": self.domain,
            "db_path": self.db_path,
            "absolute_path": self.absolute_path,
        }


class DuckdbDomainCatalog:
    """
    表名 → ``DuckdbTableFileMap``；域 → 该域下所有表。

    由 ``DuckdbEngine.rebuild_table_file_map`` 在 initialize 前根据 schema 构建。
    """

    def __init__(
        self,
        table_to_file: Dict[str, DuckdbTableFileMap],
        *,
        domain_to_tables: Optional[Dict[str, Dict[str, DuckdbTableFileMap]]] = None,
    ) -> None:
        self._table_to_file = dict(table_to_file)
        if domain_to_tables is not None:
            self._domain_to_tables = domain_to_tables
        else:
            by_domain: Dict[str, Dict[str, DuckdbTableFileMap]] = {
                d: {} for d in STORAGE_DOMAINS
            }
            for name, fm in self._table_to_file.items():
                by_domain.setdefault(fm.domain, {})[name] = fm
            self._domain_to_tables = by_domain

    @classmethod
    def build(
        cls,
        settings: "DuckdbSettings",
        table_to_domain: Mapping[str, str],
    ) -> "DuckdbDomainCatalog":
        table_to_file: Dict[str, DuckdbTableFileMap] = {}
        for table_name, domain in table_to_domain.items():
            name = str(table_name).strip()
            if not name:
                continue
            dom = normalize_storage_domain(domain, table_name=name)
            dom_cfg = settings.domains.get(dom)
            if dom_cfg is None:
                raise KeyError(f"DuckDB 配置缺少域 {dom!r} 的 db_path")
            rel = dom_cfg.db_path
            table_to_file[name] = DuckdbTableFileMap(
                table_name=name,
                domain=dom,
                db_path=rel,
                absolute_path=resolve_duckdb_db_path(rel),
            )
        return cls(table_to_file)

    @classmethod
    def from_schemas(
        cls,
        settings: "DuckdbSettings",
        schemas: Mapping[str, Mapping],
    ) -> "DuckdbDomainCatalog":
        """从 ``{table_name: schema_dict}`` 提取 ``storage_domain`` 并构建映射。"""
        table_to_domain: Dict[str, str] = {}
        for _key, schema in schemas.items():
            if not schema or not isinstance(schema, dict):
                continue
            table_name = str(schema.get("name") or _key).strip()
            if not table_name:
                continue
            domain = normalize_storage_domain(
                schema.get("storage_domain"), table_name=table_name
            )
            table_to_domain[table_name] = domain
        return cls.build(settings, table_to_domain)

    def file_map_for_table(self, table_name: str) -> DuckdbTableFileMap:
        name = str(table_name or "").strip()
        if name not in self._table_to_file:
            raise KeyError(
                f"表 {name!r} 未在 DuckDB 文件映射中；"
                f"请确认 core/tables 或扩展 schema 已声明 storage_domain 且 Engine 已 rebuild_table_file_map"
            )
        return self._table_to_file[name]

    def resolve_domain(self, table_name: str) -> str:
        return self.file_map_for_table(table_name).domain

    def resolve_db_path(self, table_name: str) -> str:
        return self.file_map_for_table(table_name).absolute_path

    def tables_in_domain(self, domain: str) -> Dict[str, DuckdbTableFileMap]:
        dom = normalize_storage_domain(domain)
        return dict(self._domain_to_tables.get(dom, {}))

    def all_table_maps(self) -> Dict[str, DuckdbTableFileMap]:
        return dict(self._table_to_file)

    def register_schema(self, settings: "DuckdbSettings", schema: Dict) -> None:
        """注册单表（策略表等）并更新内存映射。"""
        if not schema or not isinstance(schema, dict):
            raise ValueError("schema 不能为空")
        table_name = str(schema.get("name") or "").strip()
        if not table_name:
            raise ValueError("schema 缺少 name")
        domain = normalize_storage_domain(
            schema.get("storage_domain"), table_name=table_name
        )
        dom_cfg = settings.domains[domain]
        fm = DuckdbTableFileMap(
            table_name=table_name,
            domain=domain,
            db_path=dom_cfg.db_path,
            absolute_path=resolve_duckdb_db_path(dom_cfg.db_path),
        )
        existing = self._table_to_file.get(table_name)
        if existing is not None and existing.domain != domain:
            raise ValueError(
                f"表 {table_name!r} 的 storage_domain 冲突: "
                f"已映射到 {existing.domain!r}，本次为 {domain!r}"
            )
        self._table_to_file[table_name] = fm
        self._domain_to_tables.setdefault(domain, {})[table_name] = fm

    @property
    def table_count(self) -> int:
        return len(self._table_to_file)

    def primary_domain(self) -> str:
        return PRIMARY_DUCKDB_DOMAIN
