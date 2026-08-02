"""跨模块契约类型与常量（配置发现异常、DuckDB 域默认等）。

推荐::

    from core.infra.project_context import ProjectContext
    from core.infra.project_context.contracts import (
        OverridableConfigNotFoundError,
        DEFAULT_DUCKDB_DOMAINS,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.infra.project_context.core.database_defaults import (
    DEFAULT_DUCKDB_DOMAINS,
    DUCKDB_DOMAIN_FILES,
    SUPPORTED_DB_TYPES,
)


class OverridableConfigNotFoundError(FileNotFoundError):
    """core 与 userspace 均未找到有效配置文件。"""


@dataclass(frozen=True)
class DiscoveredConfig:
    """一次配置路径发现结果（core / userspace 路径）。"""

    domain: str
    config_id: str
    core_path: Optional[Path]
    user_path: Optional[Path]

    @property
    def exists(self) -> bool:
        return self.core_path is not None or self.user_path is not None


MergeFn = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]

__all__ = [
    "OverridableConfigNotFoundError",
    "DiscoveredConfig",
    "MergeFn",
    "DEFAULT_DUCKDB_DOMAINS",
    "DUCKDB_DOMAIN_FILES",
    "SUPPORTED_DB_TYPES",
]
