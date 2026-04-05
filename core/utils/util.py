"""
配置合并工具（薄封装）

实现语义与 `ConfigManager._deep_merge_config` 一致，供业务与单测直接调用。
"""

from typing import Any, Dict, Optional, Set

from core.infra.project_context.config_manager import ConfigManager


def deep_merge_config(
    defaults: Dict[str, Any],
    custom: Dict[str, Any],
    deep_merge_fields: Optional[Set[str]] = None,
    override_fields: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """合并两个字典；规则见 `ConfigManager._deep_merge_config`。"""
    return ConfigManager._deep_merge_config(
        defaults,
        custom,
        deep_merge_fields=deep_merge_fields,
        override_fields=override_fields,
    )


def merge_mapping_configs(
    defaults: Dict[str, Any],
    custom: Dict[str, Any],
    deep_merge_fields: Optional[Set[str]] = None,
    override_fields: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    合并「数据源名 -> 配置 dict」的映射（如 data_sources 配置）。

    对每个数据源名称分别做 `deep_merge_config`；仅出现在一侧的键保留该侧配置。
    """
    all_keys = set(defaults.keys()) | set(custom.keys())
    out: Dict[str, Any] = {}
    for key in all_keys:
        if key in defaults and key in custom:
            out[key] = deep_merge_config(
                defaults[key],
                custom[key],
                deep_merge_fields=deep_merge_fields,
                override_fields=override_fields,
            )
        elif key in custom:
            out[key] = custom[key]
        else:
            out[key] = defaults[key]
    return out
