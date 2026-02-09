"""
RenewConfig 及相关 DataClass：renew 段配置。

强类型，构造时校验。无 fallback，配置错误即报错。
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.global_enums.enums import TermType, UpdateMode
from core.modules.data_source.data_class.error import DataSourceConfigError
from core.modules.data_source.data_class.job_execution_config import JobExecutionConfig


def _normalize_term(value: str) -> str:
    """将 day/month/quarter 规范为 TermType 值。"""
    if not value:
        return TermType.DAILY.value
    v = str(value).lower().strip()
    if v in ("day", "date"):
        return TermType.DAILY.value
    if v == "month":
        return TermType.MONTHLY.value
    if v == "quarter":
        return TermType.QUARTERLY.value
    if v in (
        TermType.DAILY.value,
        TermType.MONTHLY.value,
        TermType.QUARTERLY.value,
        TermType.WEEKLY.value,
        TermType.YEARLY.value,
    ):
        return v
    return v


@dataclass(frozen=True)
class LastUpdateInfo:
    """last_update_info 配置，incremental/rolling 模式必填。"""

    date_field: str
    date_format: str

    @classmethod
    def from_dict(cls, d: dict, data_source_key: str) -> "LastUpdateInfo":
        if not isinstance(d, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: renew.last_update_info 必须是字典"
            )
        date_field = d.get("date_field")
        if not date_field or not str(date_field).strip():
            raise DataSourceConfigError(
                f"{data_source_key}: renew.last_update_info 必须配置 date_field"
            )
        date_format_raw = d.get("date_format")
        if not date_format_raw or not str(date_format_raw).strip():
            raise DataSourceConfigError(
                f"{data_source_key}: renew.last_update_info 必须配置 date_format"
            )
        return cls(
            date_field=str(date_field).strip(),
            date_format=_normalize_term(str(date_format_raw)),
        )


@dataclass(frozen=True)
class RollingConfig:
    """rolling 配置，rolling 模式必填。"""

    unit: str
    length: int

    @classmethod
    def from_dict(cls, d: dict, data_source_key: str) -> "RollingConfig":
        if not isinstance(d, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: renew.rolling 必须是字典"
            )
        unit = d.get("unit")
        if not unit or not str(unit).strip():
            raise DataSourceConfigError(
                f"{data_source_key}: renew.rolling 必须配置 unit"
            )
        length = d.get("length")
        if length is None:
            raise DataSourceConfigError(
                f"{data_source_key}: renew.rolling 必须配置 length"
            )
        try:
            length = int(length)
        except (TypeError, ValueError):
            raise DataSourceConfigError(
                f"{data_source_key}: renew.rolling.length 必须是整数"
            )
        if length <= 0:
            raise DataSourceConfigError(
                f"{data_source_key}: renew.rolling.length 必须大于 0"
            )
        return cls(
            unit=_normalize_term(str(unit)),
            length=length,
        )


@dataclass(frozen=True)
class RenewIfOverDaysConfig:
    """renew_if_over_days 配置，可选。"""

    value: int
    counting_field: Optional[str]

    @classmethod
    def from_dict(cls, d: dict, data_source_key: str) -> Optional["RenewIfOverDaysConfig"]:
        if not d or not isinstance(d, dict):
            return None
        val = d.get("value")
        if val is None:
            return None
        try:
            value = int(val)
        except (TypeError, ValueError):
            raise DataSourceConfigError(
                f"{data_source_key}: renew.renew_if_over_days.value 必须是整数"
            )
        if value <= 0:
            raise DataSourceConfigError(
                f"{data_source_key}: renew.renew_if_over_days.value 必须大于 0"
            )
        counting = d.get("counting_field")
        return cls(
            value=value,
            counting_field=str(counting).strip() if counting else None,
        )


@dataclass(frozen=True)
class RenewConfig:
    """
    renew 段配置。

    type 必填；incremental/rolling 时 last_update_info 必填；rolling 时 rolling 必填。
    job_execution、renew_if_over_days、data_merging、extra 可选。
    """

    renew_mode: UpdateMode
    last_update_info: Optional[LastUpdateInfo]
    rolling: Optional[RollingConfig]
    job_execution: Optional[JobExecutionConfig]
    renew_if_over_days: Optional[RenewIfOverDaysConfig]
    data_merging: Dict[str, Any]
    extra: Dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict, data_source_key: str) -> "RenewConfig":
        if not isinstance(d, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: renew 必须是字典"
            )

        raw_type = d.get("type")
        if not raw_type or not str(raw_type).strip():
            raise DataSourceConfigError(
                f"{data_source_key}: renew 必须配置 type（incremental | rolling | refresh）"
            )
        try:
            renew_mode = UpdateMode.from_string(str(raw_type))
        except ValueError as e:
            raise DataSourceConfigError(f"{data_source_key}: {e}")

        last_update_info = None
        rolling = None

        if renew_mode in (UpdateMode.INCREMENTAL, UpdateMode.ROLLING):
            last_info_raw = d.get("last_update_info")
            if not last_info_raw:
                raise DataSourceConfigError(
                    f"{data_source_key}: renew 模式为 {renew_mode.value} 时必须配置 last_update_info"
                )
            last_update_info = LastUpdateInfo.from_dict(
                last_info_raw, data_source_key
            )
        elif renew_mode == UpdateMode.REFRESH:
            # REFRESH + renew_if_over_days 时需 last_update_info 提供 date_field 用于 gate 查询
            last_info_raw = d.get("last_update_info")
            if last_info_raw:
                last_update_info = LastUpdateInfo.from_dict(
                    last_info_raw, data_source_key
                )

        if renew_mode == UpdateMode.ROLLING:
            rolling_raw = d.get("rolling")
            if not rolling_raw:
                raise DataSourceConfigError(
                    f"{data_source_key}: renew 模式为 rolling 时必须配置 rolling"
                )
            rolling = RollingConfig.from_dict(rolling_raw, data_source_key)

        job_execution = None
        job_exec_raw = d.get("job_execution")
        if isinstance(job_exec_raw, dict) and job_exec_raw.get("list"):
            job_execution = JobExecutionConfig.from_dict(job_exec_raw, data_source_key)

        renew_if_over_days = RenewIfOverDaysConfig.from_dict(
            d.get("renew_if_over_days") or {}, data_source_key
        )

        data_merging_raw = d.get("data_merging")
        data_merging = (
            dict(data_merging_raw)
            if isinstance(data_merging_raw, dict)
            else {}
        )

        extra_raw = d.get("extra")
        extra = dict(extra_raw) if isinstance(extra_raw, dict) else {}

        return cls(
            renew_mode=renew_mode,
            last_update_info=last_update_info,
            rolling=rolling,
            job_execution=job_execution,
            renew_if_over_days=renew_if_over_days,
            data_merging=data_merging,
            extra=extra,
        )
