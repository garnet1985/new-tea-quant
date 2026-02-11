"""
normalization_helper - 标准化阶段相关的底层工具函数。

原本这些逻辑集中在 DataSourceHandlerHelper 中，这里抽出一份独立实现，
便于 NormalizationService 等按职责依赖，逐步减轻 handler_helper 的体积。
"""
from typing import Any, Dict, Iterable, List, Optional
import logging

from core.modules.data_source.data_class.api_config import ApiConfig
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig
from core.utils.utils import Utils


logger = logging.getLogger(__name__)


# ================================
# 字段映射 & records 工具
# ================================

def apply_field_mapping(
    records: List[Dict[str, Any]],
    field_mapping: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    应用字段映射。

    - records: 原始记录列表（通常来自 DataFrame.to_dict("records")）；
    - field_mapping: 字段映射规则（Dict[target_field, source_field or callable]）。
    """
    formatted: List[Dict[str, Any]] = []

    for item in records:
        mapped: Dict[str, Any] = {}

        if field_mapping:
            for target_field, source_field in field_mapping.items():
                if callable(source_field):
                    mapped[target_field] = source_field(item)
                elif isinstance(source_field, str):
                    value = item.get(source_field)
                    if value is not None:
                        if isinstance(value, (int, float)):
                            mapped[target_field] = float(value)
                        else:
                            mapped[target_field] = value
                    else:
                        # 默认：数值字段缺失给 0.0，日期/季度字段给空字符串
                        mapped[target_field] = (
                            0.0 if target_field not in ["date", "quarter", "month"] else ""
                        )
                else:
                    mapped[target_field] = item.get(source_field) if source_field in item else None
        else:
            mapped = item.copy()

        if mapped:
            formatted.append(mapped)

    return formatted


def result_to_records(result: Any) -> List[Dict[str, Any]]:
    """
    将单个 API 的原始结果转换为 records 列表。

    支持：
    - pandas.DataFrame（使用 to_dict("records")）；
    - list[dict]（直接返回）。
    """
    if result is None:
        return []

    # DataFrame 场景
    if hasattr(result, "to_dict"):
        try:
            return result.to_dict("records")
        except Exception as e:
            logger.warning(f"结果转换为 records 失败: {e}")
            return []

    # 已经是记录列表
    if isinstance(result, list):
        return result

    logger.warning(
        f"默认 normalize 不支持的结果类型: {type(result)}，"
        "期望 DataFrame 或 list[dict]"
    )
    return []


# ================================
# schema 应用 & 校验
# ================================

_SCHEMA_TYPE_MAP = {
    # 文本
    "varchar": str,
    "text": str,
    # 整数
    "int": int,
    "tinyint": int,
    "smallint": int,
    "bigint": int,
    # 浮点/小数
    "float": float,
    "double": float,
    "decimal": float,
    "numeric": float,
    # 日期/时间
    "datetime": str,
    "timestamp": str,
    "date": str,
}


def apply_schema(records: List[Dict[str, Any]], schema: Any) -> List[Dict[str, Any]]:
    """
    根据表 schema（dict，来自 DB）将记录列表规范化到标准字段集。

    schema 为 core/tables 的 schema dict：name, primaryKey, fields（list of {name, type, isRequired, ...}）。
    - 只保留 schema["fields"] 中定义的字段；
    - 缺失字段填 None；
    - 按 schema 的 type 做类型转换。
    """
    if not schema or not isinstance(schema, dict):
        return records
    fields_list = schema.get("fields") or []
    if not fields_list:
        return records

    type_map = _SCHEMA_TYPE_MAP
    normalized: List[Dict[str, Any]] = []

    for item in records:
        row: Dict[str, Any] = {}
        for field_def in fields_list:
            name = field_def.get("name")
            if not name:
                continue
            value = item.get(name)
            type_str = (field_def.get("type") or "").lower()
            py_type = type_map.get(type_str, str)
            if value is not None and py_type:
                try:
                    value = py_type(value)
                except (TypeError, ValueError):
                    logger.warning(
                        f"字段 {name} 类型转换失败: 值={value} 目标类型={py_type}"
                    )
            row[name] = value
        normalized.append(row)

    return normalized


def validate_field_coverage(
    apis_conf: Dict[str, ApiConfig],
    schema: Any,
    ignore_fields: Optional[Iterable[str]] = None,
) -> None:
    """
    校验：表 schema 中的字段是否都能在各 API 的 result_mapping 中找到对应来源。
    ignore_fields 中的字段不参与校验（由 save 层或 DB 填充）。
    """
    if not schema or not isinstance(schema, dict):
        return
    fields_list = schema.get("fields") or []
    schema_fields = {f.get("name") for f in fields_list if f.get("name")}
    ign = set(ignore_fields) if ignore_fields else set()
    schema_fields -= ign
    mapped_targets: set[str] = set()

    for api_cfg in (apis_conf or {}).values():
        mapped_targets.update(api_cfg.result_mapping.keys())

    unmapped = sorted(schema_fields - mapped_targets)
    if unmapped:
        logger.warning(
            "以下 schema 字段在任何 API 的 result_mapping 中都没有配置映射，"
            f"可能导致标准化后缺少这些字段: {unmapped}"
        )


def build_normalized_payload(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    将记录列表包装为标准的 {"data": [...]} 结构。
    """
    return {"data": records}


def normalize_date_field(
    records: List[Dict[str, Any]],
    field: str = "date",
    target_format: str = "day",
) -> List[Dict[str, Any]]:
    """
    使用 DateUtils 将日期字段统一转换为指定格式。

    Args:
        records: 记录列表
        field: 日期字段名（默认为 "date"）
        target_format: 目标格式，可选值：
            - "day": YYYYMMDD（默认）
            - "month": YYYYMM
            - "quarter": YYYYMMQ[1-4]（例如 202403Q1）
            - "none": 跳过标准化

    - 支持常见输入形式：YYYYMMDD, YYYY-MM-DD, datetime/date 等；
    - 不可解析的日期会被跳过（保留原值），由上层决定是否过滤。
    """
    if not records or not field or target_format == "none":
        return records

    try:
        from core.utils.date.date_utils import DateUtils
    except ImportError:
        logger.warning("无法导入 DateUtils，normalize_date_field 将跳过处理")
        return records

    period = target_format or DateUtils.PERIOD_DAY

    for r in records:
        if not isinstance(r, dict) or field not in r:
            continue
        value = r.get(field)
        if value is None:
            continue

        normalized = DateUtils.normalize_period_value(value, period)
        if normalized:
            r[field] = normalized

    return records


# ================================
# 提取 & 合并映射后的记录
# ================================

def extract_mapped_records(
    apis_conf: Dict[str, ApiConfig],
    fetched_data: Dict[str, Any],
    merge_by_key: str = None,
) -> List[Dict[str, Any]]:
    """
    从所有 API 的原始返回中，提取并映射出“已按 result_mapping 转换为标准字段”的记录列表。
    """
    if merge_by_key:
        merged_by_key: Dict[str, Dict[str, Any]] = {}

        for api_name, api_cfg in (apis_conf or {}).items():
            # fetched_data 的标准结构为:
            # {api_name: {entity_id: raw_result}}
            # 这里避免使用 "or {}" 以防 raw_result 是 DataFrame 时触发
            # "The truth value of a DataFrame is ambiguous" 错误。
            if Utils.is_dict(fetched_data):
                api_data = fetched_data.get(api_name)
            else:
                api_data = {"_unified": fetched_data}

            if not Utils.is_dict(api_data):
                api_data = {"_unified": api_data}

            for raw in api_data.values():
                records = result_to_records(raw)
                if not records:
                    continue

                result_mapping = api_cfg.result_mapping
                mapped = apply_field_mapping(records, result_mapping)

                for record in mapped:
                    key_value = record.get(merge_by_key)
                    if key_value is None:
                        logger.warning(
                            f"API {api_name} 的记录缺少 merge_by_key 字段 '{merge_by_key}'，跳过该记录"
                        )
                        continue

                    key_str = str(key_value)
                    if key_str not in merged_by_key:
                        merged_by_key[key_str] = {merge_by_key: key_value}

                    merged_by_key[key_str].update(record)

        return list(merged_by_key.values())

    # 平铺模式：简单累加所有记录
    mapped_records: List[Dict[str, Any]] = []

    for api_name, api_cfg in (apis_conf or {}).items():
        if Utils.is_dict(fetched_data):
            api_data = fetched_data.get(api_name)
        else:
            api_data = {"_unified": fetched_data}

        if not Utils.is_dict(api_data):
            api_data = {"_unified": api_data}

        result_mapping = api_cfg.result_mapping

        for raw in api_data.values():
            records = result_to_records(raw)
            if not records:
                continue

            mapped = apply_field_mapping(records, result_mapping)
            mapped_records.extend(mapped)

    return mapped_records


def normalize_fetched_data(context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    默认标准化实现（支持多 API，但不做复杂合并，仅做“平铺 + 映射 + schema 约束”）。
    """
    config = context.get("config")
    if not isinstance(config, DataSourceConfig):
        return {"data": []}
    apis_conf = config.get_apis()
    schema = context.get("schema")

    if not fetched_data or not isinstance(fetched_data, dict):
        logger.info("fetched_data 为空或类型非法，返回空数据")
        return {"data": []}

    ignore_fields = config.get_ignore_fields()
    validate_field_coverage(apis_conf, schema, ignore_fields=ignore_fields)

    mapped_records = extract_mapped_records(apis_conf, fetched_data)

    if not mapped_records:
        logger.info("所有 API 结果均为空，返回空数据")
        return {"data": []}

    normalized_records = apply_schema(mapped_records, schema)
    logger.info(f"✅ 默认标准化完成，记录数={len(normalized_records)}")
    return build_normalized_payload(normalized_records)


# ================================
# 数据验证
# ================================

def validate_normalized_data(
    normalized_data: Dict[str, Any],
    schema: Any,
    data_source_key: str = "unknown",
    ignore_fields: Optional[Iterable[str]] = None,
) -> None:
    """
    验证标准化后的数据是否符合 schema。
    """
    if not schema or not isinstance(schema, dict):
        return
    ign = set(ignore_fields) if ignore_fields else set()

    def _valid(record: dict) -> bool:
        return _validate_record_against_schema(record, schema, ignore_fields=ign)

    if isinstance(normalized_data, dict) and "data" in normalized_data:
        data_list = normalized_data.get("data", [])
        if not isinstance(data_list, list):
            raise ValueError(
                f"数据验证失败: {data_source_key} 的 data 字段不是列表类型"
            )
        errors = []
        for idx, record in enumerate(data_list):
            if not isinstance(record, dict):
                errors.append(f"记录 {idx} 不是字典类型")
                continue
            if not _valid(record):
                record_errors = _collect_validation_errors(record, schema, ignore_fields=ign)
                if record_errors:
                    errors.append(f"记录 {idx}: {', '.join(record_errors)}")
        if errors:
            raise ValueError(
                f"数据验证失败: {data_source_key} 的标准化数据不符合表 schema。"
                f"错误详情: {'; '.join(errors)}"
            )
        return

    if not _valid(normalized_data):
        errors = _collect_validation_errors(normalized_data, schema, ignore_fields=ign)
        error_msg = ", ".join(errors) if errors else "数据不符合表 schema"
        raise ValueError(
            f"数据验证失败: {data_source_key} 的标准化数据不符合表 schema。"
            f"错误详情: {error_msg}"
        )


def _validate_record_against_schema(
    record: Dict[str, Any],
    schema: Dict[str, Any],
    ignore_fields: Optional[set] = None,
) -> bool:
    """表 schema（dict）校验单条记录：必填存在、类型可接受。ignore_fields 中的字段不要求存在。"""
    if not schema or not isinstance(schema, dict):
        return True
    ign = ignore_fields or set()
    fields_list = schema.get("fields") or []
    type_map = _SCHEMA_TYPE_MAP
    for field_def in fields_list:
        name = field_def.get("name")
        if not name:
            continue
        if name in ign:
            continue
        if field_def.get("isRequired") and name not in record:
            return False
        if name in record and record[name] is not None:
            py_type = type_map.get((field_def.get("type") or "").lower(), str)
            if not _check_type(record[name], py_type):
                return False
    return True


def _collect_validation_errors(
    record: Dict[str, Any],
    schema: Any,
    ignore_fields: Optional[set] = None,
) -> List[str]:
    """
    收集数据验证错误信息。schema 为表 schema dict（fields 为 list）。
    ignore_fields 中的字段不报缺失错误。
    """
    errors = []
    if not schema or not isinstance(schema, dict):
        return errors
    ign = ignore_fields or set()
    fields_list = schema.get("fields") or []
    type_map = _SCHEMA_TYPE_MAP
    for field_def in fields_list:
        name = field_def.get("name")
        if not name:
            continue
        if name in ign:
            continue
        if field_def.get("isRequired") and name not in record:
            errors.append(f"{name}(缺失)")
        elif name in record and record[name] is not None:
            value = record[name]
            py_type = type_map.get((field_def.get("type") or "").lower(), str)
            if not _check_type(value, py_type):
                errors.append(
                    f"{name}(类型错误: {type(value).__name__} != {py_type.__name__})"
                )
    return errors


def _check_type(value: Any, expected_type: type) -> bool:
    """
    检查类型（支持类型转换）。
    """
    if isinstance(value, expected_type):
        return True

    try:
        if expected_type == int and isinstance(value, (float, str)):
            int(value)
            return True
        elif expected_type == float and isinstance(value, (int, str)):
            float(value)
            return True
        elif expected_type == str:
            str(value)
            return True
    except (ValueError, TypeError):
        return False

    return False

