"""
DataSourceConfig: 数据源配置。

强类型，仅通过 from_dict 创建。构造时校验，错误第一时间抛出，不兼容不 fallback。
"""
from typing import Any, Dict, List, Optional

from core.global_enums.enums import UpdateMode

from core.modules.data_source.data_class.api_config import ApiConfig
from core.modules.data_source.data_class.error import DataSourceConfigError
from core.modules.data_source.data_class.job_execution_config import JobExecutionConfig
from core.modules.data_source.data_class.renew_config import RenewConfig


class DataSourceConfig:
    """
    数据源配置。

    仅通过 from_dict() 创建。不接受 dict 直接构造。
    data_source_key 由框架传入（mapping 中的 key），用于错误提示。
    """

    def __init__(
        self,
        data_source_key: str,
        table: str,
        save_mode: str,
        save_batch_size: int,
        renew: RenewConfig,
        apis: Dict[str, ApiConfig],
        ignore_fields: List[str],
        is_dry_run: bool,
        needs_stock_grouping: Optional[bool],
        top_level_merge_by_key: Optional[str],
        default_date_range_years: int,
    ):
        self._data_source_key = data_source_key
        self._table = table
        self._save_mode = save_mode
        self._save_batch_size = save_batch_size
        self._renew = renew
        self._apis = apis
        self._ignore_fields = ignore_fields
        self._is_dry_run = is_dry_run
        self._needs_stock_grouping = needs_stock_grouping
        self._top_level_merge_by_key = top_level_merge_by_key
        self._default_date_range_years = default_date_range_years

    @classmethod
    def from_dict(cls, config_dict: dict, data_source_key: str) -> "DataSourceConfig":
        """
        从字典解析并校验。错误时抛出 DataSourceConfigError。
        不接受 dict 以外的类型。
        """
        if not data_source_key or not str(data_source_key).strip():
            raise DataSourceConfigError("DataSourceConfig 必须传入 data_source_key")

        if not isinstance(config_dict, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: config 必须是字典，收到: {type(config_dict).__name__}"
            )

        table = config_dict.get("table")
        if not table or not str(table).strip():
            raise DataSourceConfigError(
                f"{data_source_key}: 必须配置 table（绑定表名）"
            )
        table = str(table).strip()

        save_mode = config_dict.get("save_mode")
        if not save_mode or not str(save_mode).strip():
            raise DataSourceConfigError(
                f"{data_source_key}: 必须配置 save_mode（unified | immediate | batch）"
            )
        save_mode = str(save_mode).strip().lower()
        if save_mode not in ("unified", "immediate", "batch"):
            raise DataSourceConfigError(
                f"{data_source_key}: save_mode 无效 '{save_mode}'，应为 unified | immediate | batch"
            )

        save_batch_size = 50
        raw_batch = config_dict.get("save_batch_size")
        if raw_batch is not None:
            try:
                save_batch_size = int(raw_batch)
            except (TypeError, ValueError):
                raise DataSourceConfigError(
                    f"{data_source_key}: save_batch_size 必须是整数"
                )
            if save_batch_size <= 0:
                raise DataSourceConfigError(
                    f"{data_source_key}: save_batch_size 必须大于 0"
                )

        renew_raw = config_dict.get("renew")
        if not renew_raw or not isinstance(renew_raw, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: 必须配置 renew"
            )
        renew = RenewConfig.from_dict(renew_raw, data_source_key)

        apis_raw = config_dict.get("apis")
        if not apis_raw or not isinstance(apis_raw, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: 必须配置 apis 且不能为空"
            )
        apis = {}
        for api_name, api_cfg in apis_raw.items():
            if not api_name or not str(api_name).strip():
                raise DataSourceConfigError(
                    f"{data_source_key}: apis 的 key 不能为空"
                )
            apis[api_name] = ApiConfig.from_dict(
                str(api_name).strip(), api_cfg, data_source_key
            )

        ignore_raw = config_dict.get("ignore_fields")
        if ignore_raw is None:
            ignore_fields = []
        elif isinstance(ignore_raw, list):
            ignore_fields = [str(x) for x in ignore_raw if x is not None]
        else:
            raise DataSourceConfigError(
                f"{data_source_key}: ignore_fields 必须是列表"
            )

        is_dry_run = bool(config_dict.get("is_dry_run", False))
        needs_stock_grouping = config_dict.get("needs_stock_grouping")
        if needs_stock_grouping is not None and not isinstance(
            needs_stock_grouping, bool
        ):
            needs_stock_grouping = None

        top_level_merge_by_key = config_dict.get("merge_by_key")
        if top_level_merge_by_key:
            top_level_merge_by_key = str(top_level_merge_by_key).strip()
        else:
            top_level_merge_by_key = None

        default_range = config_dict.get("default_date_range")
        default_date_range_years = 1
        if isinstance(default_range, dict) and default_range.get("years") is not None:
            try:
                default_date_range_years = int(default_range["years"])
            except (TypeError, ValueError):
                pass
            if default_date_range_years <= 0:
                default_date_range_years = 1

        return cls(
            data_source_key=data_source_key,
            table=table,
            save_mode=save_mode,
            save_batch_size=save_batch_size,
            renew=renew,
            apis=apis,
            ignore_fields=ignore_fields,
            is_dry_run=is_dry_run,
            needs_stock_grouping=needs_stock_grouping,
            top_level_merge_by_key=top_level_merge_by_key,
            default_date_range_years=default_date_range_years,
        )

    # ========== 兼容访问方法（读取内部强类型） ==========

    def get_table_name(self) -> str:
        return self._table

    def get_save_mode(self) -> str:
        return self._save_mode

    def get_save_batch_size(self) -> int:
        return self._save_batch_size

    def get_ignore_fields(self) -> List[str]:
        return self._ignore_fields

    def get_renew_mode(self) -> UpdateMode:
        return self._renew.renew_mode

    def get_date_format(self) -> str:
        if self._renew.last_update_info:
            return self._renew.last_update_info.date_format
        return "day"

    def get_date_field(self) -> str:
        if self._renew.last_update_info:
            return self._renew.last_update_info.date_field
        return ""

    def get_rolling_unit(self) -> Optional[str]:
        if self._renew.rolling:
            return self._renew.rolling.unit
        return None

    def get_rolling_length(self) -> int:
        if self._renew.rolling:
            return self._renew.rolling.length
        return 0

    def get_needs_stock_grouping(self) -> Optional[bool]:
        return self._needs_stock_grouping

    def get_renew_if_over_days(self) -> Optional[Dict[str, Any]]:
        if self._renew.renew_if_over_days:
            cfg = self._renew.renew_if_over_days
            r = {"value": cfg.value}
            if cfg.counting_field:
                r["counting_field"] = cfg.counting_field
            return r
        return None

    def get_renew_extra(self) -> Dict[str, Any]:
        return dict(self._renew.extra)

    def has_over_time_threshold(self) -> bool:
        return self._renew.renew_if_over_days is not None

    def get_over_time_threshold(self) -> Optional[int]:
        if self._renew.renew_if_over_days:
            return self._renew.renew_if_over_days.value
        return None

    def get_data_merging(self) -> Dict[str, Any]:
        return dict(self._renew.data_merging)

    def get_merge_by_key(self) -> Optional[str]:
        merge_key = self._renew.data_merging.get("merge_by_key")
        if merge_key:
            return str(merge_key)
        return self._top_level_merge_by_key

    def get_apis(self) -> Dict[str, ApiConfig]:
        return self._apis

    def is_per_entity(self) -> bool:
        return self._renew.job_execution is not None

    def has_result_group_by(self) -> bool:
        return self._renew.job_execution is not None

    def get_group_by(self) -> Optional[JobExecutionConfig]:
        return self._renew.job_execution

    def get_group_by_entity_list_name(self) -> Optional[str]:
        if self._renew.job_execution:
            return self._renew.job_execution.list_name
        return None

    def get_group_by_terms(self) -> Optional[List[str]]:
        if self._renew.job_execution and self._renew.job_execution.terms:
            return list(self._renew.job_execution.terms)
        return None

    def get_group_by_key(self) -> Optional[str]:
        if self._renew.job_execution and self._renew.job_execution.key:
            return self._renew.job_execution.key
        return None

    def get_group_fields(self) -> List[str]:
        if not self._renew.job_execution:
            return []
        job = self._renew.job_execution
        if job.keys:
            return list(job.keys)
        if job.key:
            return [job.key]
        return []

    def get_is_dry_run(self) -> bool:
        return self._is_dry_run

    def get_default_date_range_years(self) -> int:
        return self._default_date_range_years

    def get_default_date_range(self) -> Dict[str, int]:
        """返回 default_date_range 配置，如 {"years": 1}，供 RefreshRenewService 使用。"""
        return {"years": self._default_date_range_years}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于调试或序列化）。"""
        return {
            "table": self._table,
            "save_mode": self._save_mode,
            "save_batch_size": self._save_batch_size,
            "ignore_fields": self._ignore_fields,
            "is_dry_run": self._is_dry_run,
            "needs_stock_grouping": self._needs_stock_grouping,
        }
