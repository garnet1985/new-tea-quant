"""
通用工具模块

提供配置文件的加载、合并等工具方法
"""
from typing import Dict, Any, Set


def deep_merge_config(
    defaults: Dict[str, Any],
    custom: Dict[str, Any],
    deep_merge_fields: Set[str] = None,
    override_fields: Set[str] = None
) -> Dict[str, Any]:
    """
    深度合并两个配置字典
    
    合并规则：
    1. 对于 deep_merge_fields 中的字段，进行深度合并（嵌套字典合并）
    2. 对于 override_fields 中的字段，完全覆盖（custom 覆盖 defaults）
    3. 对于其他字段，custom 覆盖 defaults（浅层覆盖）
    
    Args:
        defaults: 默认配置字典
        custom: 自定义配置字典（会覆盖 defaults）
        deep_merge_fields: 需要深度合并的字段名集合（如 {"params"}）
        override_fields: 需要完全覆盖的字段名集合（如 {"dependencies"}）
    
    Returns:
        合并后的配置字典
    
    Example:
        >>> defaults = {
        ...     "handler": "defaults.handler",
        ...     "params": {"a": 1, "b": 2},
        ...     "dependencies": {"dep1": True, "dep2": False}
        ... }
        >>> custom = {
        ...     "params": {"b": 3, "c": 4},
        ...     "dependencies": {"dep1": False}
        ... }
        >>> result = deep_merge_config(
        ...     defaults, custom,
        ...     deep_merge_fields={"params"},
        ...     override_fields={"dependencies"}
        ... )
        >>> result["params"]  # 深度合并：{"a": 1, "b": 3, "c": 4}
        >>> result["dependencies"]  # 完全覆盖：{"dep1": False}
    """
    if deep_merge_fields is None:
        deep_merge_fields = set()
    if override_fields is None:
        override_fields = set()
    
    # 先进行浅层合并（custom 覆盖 defaults）
    merged = {**defaults, **custom}
    
    # 对于需要深度合并的字段，进行深度合并
    for field in deep_merge_fields:
        if field in defaults and field in custom:
            # 确保都是字典类型
            if isinstance(defaults[field], dict) and isinstance(custom[field], dict):
                merged[field] = {**defaults[field], **custom[field]}
            else:
                # 如果不是字典，使用 custom 的值（覆盖）
                merged[field] = custom[field]
    
    # 对于需要完全覆盖的字段，使用 custom 的值（已经在浅层合并中处理）
    # 这里不需要额外操作，因为 override_fields 的字段在浅层合并时已经被覆盖
    
    return merged


def merge_mapping_configs(
    defaults_mapping: Dict[str, Dict[str, Any]],
    custom_mapping: Dict[str, Dict[str, Any]],
    deep_merge_fields: Set[str] = None,
    override_fields: Set[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    合并两个 mapping 配置（data_sources 级别的配置）
    
    对于每个 data_source：
    - 如果 custom 中存在，使用 deep_merge_config 合并
    - 如果 custom 中不存在，保留 defaults 的配置
    
    Args:
        defaults_mapping: 默认 mapping 配置 {data_source_name: config}
        custom_mapping: 自定义 mapping 配置 {data_source_name: config}
        deep_merge_fields: 需要深度合并的字段名集合（如 {"params"}）
        override_fields: 需要完全覆盖的字段名集合（如 {"dependencies"}）
    
    Returns:
        合并后的 mapping 配置
    
    Example:
        >>> defaults = {
        ...     "kline": {
        ...         "handler": "defaults.handler",
        ...         "params": {"a": 1},
        ...         "dependencies": {"dep1": True}
        ...     }
        ... }
        >>> custom = {
        ...     "kline": {
        ...         "params": {"b": 2},
        ...         "dependencies": {"dep2": True}
        ...     }
        ... }
        >>> result = merge_mapping_configs(
        ...     defaults, custom,
        ...     deep_merge_fields={"params"},
        ...     override_fields={"dependencies"}
        ... )
    """
    merged = defaults_mapping.copy()
    
    for ds_name, custom_config in custom_mapping.items():
        if ds_name in merged:
            # 如果 defaults 中存在，深度合并
            defaults_config = merged[ds_name]
            merged[ds_name] = deep_merge_config(
                defaults_config,
                custom_config,
                deep_merge_fields=deep_merge_fields,
                override_fields=override_fields
            )
        else:
            # 如果 defaults 中不存在，直接添加（新增的 data_source）
            merged[ds_name] = custom_config
    
    return merged
