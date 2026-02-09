"""
record_utils - 针对记录列表和标准化结果的通用工具函数。

这些工具原本挂在 BaseHandler 上，现在抽到独立模块，便于复用与解耦。
"""
from typing import Any, Dict, List

from loguru import logger


def clean_nan_in_records(records: List[Dict[str, Any]], default: Any = None) -> List[Dict[str, Any]]:
    """
    清理一批记录中的 NaN/None 等异常数值，返回清洗后的记录列表。

    内部委托 DataSourceHandlerHelper 和 DBHelper 实现，调用方无需关心细节。
    """
    if not records:
        return records

    try:
        from core.infra.db.helpers.db_helpers import DBHelper
    except ImportError:
        logger.warning("无法导入 DBHelper，clean_nan_in_records 将跳过处理")
        return records

    return DBHelper.clean_nan_in_list(records, default=default)


def clean_nan_in_normalized_data(normalized_data: Dict[str, Any], default: Any = None) -> Dict[str, Any]:
    """
    针对标准化结果的便捷 NaN 清洗：
    - 如果 normalized_data 是 {"data": [...]}，则对 data 列表做清洗；
    - 否则尝试直接将 normalized_data 视为单条记录列表的一部分。
    """
    if not normalized_data:
        return normalized_data

    if isinstance(normalized_data, dict) and "data" in normalized_data:
        data_list = normalized_data.get("data") or []
        if isinstance(data_list, list):
            normalized_data["data"] = clean_nan_in_records(data_list, default=default)
        return normalized_data

    # fallback：如果不是 {"data": [...]} 结构，则保持原样返回
    return normalized_data


def filter_records_by_required_fields(
    records: List[Dict[str, Any]], required_fields: List[str]
) -> List[Dict[str, Any]]:
    """
    过滤记录：只保留包含所有必需字段的记录。
    """
    if not records or not required_fields:
        return records
    return [r for r in records if all(r.get(f) for f in required_fields)]


def ensure_float_field(
    records: List[Dict[str, Any]], field: str, default: float = 0.0
) -> List[Dict[str, Any]]:
    """
    确保某个字段是 float 类型，转换失败时使用默认值。
    """
    if not records or not field:
        return records

    for r in records:
        if not isinstance(r, dict):
            continue
        value = r.get(field)
        if value is None:
            r[field] = default
        else:
            try:
                r[field] = float(value)
            except (ValueError, TypeError):
                logger.warning(f"字段 {field} 无法转换为 float: {value}，使用默认值 {default}")
                r[field] = default

    return records

