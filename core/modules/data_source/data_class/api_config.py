"""
ApiConfig: 单个 API 的配置 DataClass。

强类型，构造时校验。错误第一时间抛出，不兼容。
"""
from dataclasses import dataclass
from typing import Any, Dict


from core.modules.data_source.data_class.error import DataSourceConfigError


def _require_str(val: Any, field: str, api_name: str, data_source_key: str) -> str:
    if val is None or (isinstance(val, str) and not val.strip()):
        raise DataSourceConfigError(
            f"{data_source_key}: apis.{api_name} 必须配置 {field}"
        )
    return str(val).strip()


def _require_int(val: Any, field: str, api_name: str, data_source_key: str) -> int:
    if val is None:
        raise DataSourceConfigError(
            f"{data_source_key}: apis.{api_name} 必须配置 {field}"
        )
    try:
        v = int(val)
    except (TypeError, ValueError):
        raise DataSourceConfigError(
            f"{data_source_key}: apis.{api_name}.{field} 必须是整数，收到: {type(val).__name__}"
        )
    if v <= 0:
        raise DataSourceConfigError(
            f"{data_source_key}: apis.{api_name}.{field} 必须大于 0，收到: {v}"
        )
    return v


def _dict_str_str(val: Any, field: str, api_name: str) -> Dict[str, str]:
    if val is None:
        return {}
    if not isinstance(val, dict):
        return {}
    return {str(k): str(v) for k, v in val.items() if k is not None and v is not None}


@dataclass(frozen=True)
class ApiConfig:
    """
    单个 API 的配置。

    必填：provider_name, method, max_per_minute
    可选：params_mapping, result_mapping（默认空字典）, params（静态 API 参数，默认空字典）
    """

    api_name: str
    provider_name: str
    method: str
    max_per_minute: int
    params_mapping: Dict[str, str]
    result_mapping: Dict[str, str]
    params: Dict[str, Any]

    @classmethod
    def from_dict(
        cls,
        api_name: str,
        d: dict,
        data_source_key: str,
    ) -> "ApiConfig":
        """
        从字典解析并校验。错误时抛出 DataSourceConfigError。
        """
        if not isinstance(d, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: apis.{api_name} 必须是字典，收到: {type(d).__name__}"
            )

        provider_name = _require_str(
            d.get("provider_name"), "provider_name", api_name, data_source_key
        )
        method = _require_str(d.get("method"), "method", api_name, data_source_key)
        max_per_minute = _require_int(
            d.get("max_per_minute"), "max_per_minute", api_name, data_source_key
        )
        params_mapping = _dict_str_str(d.get("params_mapping"), "params_mapping", api_name)
        result_mapping = _dict_str_str(d.get("result_mapping"), "result_mapping", api_name)

        raw_params = d.get("params")
        params = dict(raw_params) if isinstance(raw_params, dict) else {}

        return cls(
            api_name=api_name,
            provider_name=provider_name,
            method=method,
            max_per_minute=max_per_minute,
            params_mapping=params_mapping,
            result_mapping=result_mapping,
            params=params,
        )
