"""
句柄 `DataEntity`、resolver 注册表与主链路说明（与 `CONCEPTS.md` 目标架构对齐）。

**流程**见模块 `pipeline.py` 顶部文档字符串。
"""

from core.modules.data_contract.runtime.contract_meta import build_rule_meta
from core.modules.data_contract.runtime.data_entity import DataEntity
from core.modules.data_contract.runtime.pipeline import merge_params
from core.modules.data_contract.runtime.resolver_registry import ResolverRegistry

__all__ = [
    "DataEntity",
    "ResolverRegistry",
    "build_rule_meta",
    "merge_params",
]
