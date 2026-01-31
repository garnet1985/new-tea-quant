from typing import Any, Dict, Optional
from loguru import logger
from core.global_enums.enums import TermType, UpdateMode


class DataSourceConfig:
    """
    DataSource Config class

    支持从 dict 创建，并提供配置验证功能。

    设计注意 / 潜在问题：
    - data_source_key 由框架在创建 Config 时传入（mapping 中的 key），不是 config 字典里的键。
    - 是否 per-entity 由是否配置 result_group_by 决定；incremental/rolling 下未配 result_group_by 则按全局处理。
    - get_date_format() 的 fallback 会读顶层 "date_format" 键，与该方法名相同，仅文档说明。
    - renew_if_over_days、rolling 等子段暂无严格 schema 校验，依赖约定。
    - 可选顶层 "is_dry_run": bool；为 True 时该数据源不执行 DB 写入（用户 save 钩子与系统写入均跳过），便于调试。框架会将其注入 context["is_dry_run"]。
    """
    
    def __init__(self, config_dict: Dict[str, Any], data_source_key: str = None):
        """
        从字典创建 DataSourceConfig

        Args:
            config_dict: 配置字典
            data_source_key: 数据源配置键（mapping 中的 key，用于错误提示）
        """
        self._config_dict = config_dict or {}
        self._data_source_key = data_source_key

        
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（兼容 dict 接口）"""
        return self._config_dict.get(key, default)
    
    def is_valid(self) -> bool:
        """
        验证 config 配置是否完整（根据 renew_mode 验证必填字段）。
        
        规则：
        - incremental 模式：必须配置顶层 table 和 date_field
        - rolling 模式：必须配置顶层 table、date_field、rolling_unit、rolling_length
        
        Raises:
            ValueError: 如果配置不完整
        """

        if not self._is_valid_basic_info():
            logger.warning(f"{self._data_source_key} 基本信息不完整，跳过")
            return False

        if not self._is_valid_renew_mode():
            logger.warning(f"{self._data_source_key} 续跑模式不完整，跳过")
            return False

        if not self._is_valid_group_by():
            logger.warning(f"{self._data_source_key} 结果分组不完整，跳过")
            return False

        if not self._is_valid_apis():
            logger.warning(f"{self._data_source_key} API 配置不完整，跳过")
            return False

        return True

    def _is_valid_apis(self) -> bool:
        apis = self._config_dict.get("apis")
        if not apis:
            logger.warning(f"{self._data_source_key} API 配置为空，跳过")
            return False

        for api_name, api_config in apis.items():
            if not api_config.get("provider_name"):
                logger.warning(f"{self._data_source_key} 中apis字段中 {api_name} 必须配置 provider_name")
                return False
            if not api_config.get("method"):
                logger.warning(f"{self._data_source_key} 中apis字段中 {api_name} 必须配置 method")
                return False
            if not api_config.get("max_per_minute"):
                logger.warning(f"{self._data_source_key} 中apis字段中 {api_name} 必须配置 max_per_minute")
                return False
        return True

    def _is_valid_basic_info(self) -> bool:
        if not self._config_dict:
            logger.warning(f"'{self._data_source_key}' 的 config 为空，将跳过执行")
            return False

        if not self._data_source_key:
            logger.warning(f"DataSourceConfig 必须传入 data_source_key（mapping 中的 key）")
            return False

        if not self.get("table"):
            logger.warning(f"'{self._data_source_key}' 的 config 必须配置顶层 table（绑定表名）")
            return False
        return True

    def _is_valid_renew_mode(self) -> bool:
        renew_config = self.get("renew")

        if not renew_config:
            logger.warning(f"'{self._data_source_key}' 的 config 中必须配置 renew")
            return False

        renew_type = renew_config.get("type")
        if not renew_type:
            logger.warning(f"'{self._data_source_key}' 的 config 中 renew 必须配置 type")
            return False

        # Incremental 模式验证
        if renew_type == UpdateMode.INCREMENTAL.value or renew_type == UpdateMode.ROLLING.value:

            last_update_info = renew_config.get("last_update_info")
            if not last_update_info:
                logger.warning(f"'{self._data_source_key}' 的 config 中 renew 必须配置 last_update_info 来找到以前renew到的时间点")
                return False

            table_name = self.get_table_name()
            if not table_name:
                logger.warning(f"'{self._data_source_key}' 的 config 必须配置顶层 table（绑定表名）")
                return False

            date_field = self.get_date_field()
            if not date_field:
                logger.warning(f"'{self._data_source_key}' 的 config 中 renew 必须配置 date_field（顶层或 last_update_info）")
                return False

            date_format = self.get_date_format()
            if not date_format:
                logger.warning(f"'{self._data_source_key}' 的 config 中 renew 必须配置 date_format（顶层或 last_update_info）")
                return False

            # per-entity 时实体标识字段由 result_group_by.by_key 统一提供，不再要求 last_update_info.group_field
        # Rolling 模式验证
        if renew_type == UpdateMode.ROLLING.value:
            # TODO: add validation for date range related info
            pass
            # last_update_info = renew_config.get("date_range")
            # if not last_update_info:
            #     logger.warning(f"'{self._data_source_key}' 的 config 中 renew 必须配置 date_range 来找到以前 renew 到的时间点")
            #     return False

        return True

    def _is_valid_group_by(self) -> bool:
        group_by = self.get_group_by()
        
        if group_by is None:
            return True

        if not isinstance(group_by, dict):
            logger.warning(f"'{self._data_source_key}' 的 config 中 result_group_by 必须配置为字典")
            return False

        if not group_by.get("list"):
            logger.warning(f"'{self._data_source_key}' 的 config 中 result_group_by 必须配置 list")
            return False

        if not group_by.get("by_key"):
            logger.warning(f"'{self._data_source_key}' 的 config 中 result_group_by 必须配置 by_key")
            return False

        return True
    
    # ========== 配置访问方法 ==========
    
    def get_renew_mode(self) -> Optional[UpdateMode]:
        """获取 renew_mode（小写字符串）。未配置或无效时返回 None。"""
        try:
            raw = (self.get("renew") or {}).get("type")
            return UpdateMode.from_string(raw) if raw is not None else None
        except ValueError:
            logger.warning(f"'{self._data_source_key}' 的 config 中配置的 renew_mode 无效，将跳过执行")
            return None
    
    def _normalize_term(self, value: str) -> str:
        """将 config 中的 day/month/quarter/date 规范为 TermType 值（daily/monthly/quarterly）。"""
        if not value:
            return TermType.DAILY.value
        v = str(value).lower()
        if v in ("day", "date"):
            return TermType.DAILY.value
        if v == "month":
            return TermType.MONTHLY.value
        if v == "quarter":
            return TermType.QUARTERLY.value
        if v in (TermType.DAILY.value, TermType.MONTHLY.value, TermType.QUARTERLY.value, TermType.WEEKLY.value, TermType.YEARLY.value):
            return v
        return v

    def get_date_format(self) -> str:
        """
        获取 date_format（默认与 TermType.DAILY 对齐）。

        优先从 renew.last_update_info.date_format 读取，
        未配置时回退到顶层 date_format，再回退到 "day"。
        返回值与 TermType 一致（daily/monthly/quarterly 等）。
        """
        renew = self.get("renew") or {}
        last_info = renew.get("last_update_info") or {}
        fmt = last_info.get("date_format") or self.get("date_format") or "day"
        return self._normalize_term(fmt)
    
    def get_table_name(self) -> str:
        """
        获取绑定表名。仅从顶层 table 读取（与 DB 表一一绑定）。
        """
        return (self.get("table") or "").strip()
    
    def get_date_field(self) -> str:
        """
        获取 date_field

        优先从 renew.last_update_info.date_field 读取，
        未配置时回退到顶层 date_field。
        """
        renew = self.get("renew") or {}
        last_info = renew.get("last_update_info") or {}
        return last_info.get("date_field") or self.get("date_field")
    
    def get_rolling_unit(self) -> Optional[str]:
        """
        获取 rolling_unit（与 TermType 对齐：daily/monthly/quarterly 等）。

        仅从 renew.rolling.unit 读取（新配置约定），并规范为 TermType 值。
        """
        renew = self.get("renew") or {}
        rolling = renew.get("rolling") or {}
        unit = rolling.get("unit")
        return self._normalize_term(unit) if unit else None
    
    def get_rolling_length(self) -> int:
        """
        获取 rolling_length

        仅从 renew.rolling.length 读取（新配置约定）。
        """
        renew = self.get("renew") or {}
        rolling = renew.get("rolling") or {}
        return rolling.get("length")
    
    def get_needs_stock_grouping(self) -> Optional[bool]:
        """
        获取是否需要按股票分组查询最新日期。
        
        Returns:
            bool: True 表示需要按股票分组（如 stock_kline），False 表示不需要（如 GDP, LPR）
            None: 如果未配置，返回 None（将自动判断）
        """
        return self.get("needs_stock_grouping")
    
    def get_renew_if_over_days(self) -> Optional[Dict[str, Any]]:
        """
        获取「超过阈值才续跑」配置。

        约定：配置写在 renew 段下：

        "renew": {
          ...
          "renew_if_over_days": {
            "value": 30,
            "counting_field": "..."  # 可选，默认使用 date_field
          }
        }

        Returns:
            Dict[str, Any]: 配置字典，未配置时返回 None
        """
        renew = self.get("renew") or {}
        threshold = renew.get("renew_if_over_days")
        if not threshold or not isinstance(threshold, dict):
            return None
        return threshold

    def get_renew_extra(self) -> Dict[str, Any]:
        """
        获取 renew 段下的扩展配置（如 latest_trading_date 的 backward_checking_days 等）。

        约定：
        "renew": {
          "type": "...",
          "last_update_info": {...},
          "rolling": {...},
          "extra": {
            ... 任意自定义字段 ...
          }
        }
        """
        renew = self.get("renew") or {}
        extra = renew.get("extra") or {}
        if not isinstance(extra, dict):
            return {}
        return extra

    def has_over_time_threshold(self) -> bool:
        """是否配置了「超过阈值才续跑」（renew_if_over_time_threshold / renew_if_over_days）。"""
        return self.get_renew_if_over_days() is not None

    def get_over_time_threshold(self) -> Optional[int]:
        """获取阈值数值（天数），未配置时返回 None。"""
        cfg = self.get_renew_if_over_days()
        if not cfg:
            return None
        val = cfg.get("value")
        return int(val) if val is not None else None

    def get_data_merging(self) -> Dict[str, Any]:
        """
        获取 renew 段下的数据合并配置（例如 merge_by_key 等）。

        约定：
        "renew": {
          "type": "...",
          ...,
          "data_merging": {
            "merge_by_key": "date"
          }
        }
        """
        renew = self.get("renew") or {}
        data_merging = renew.get("data_merging") or {}
        if not isinstance(data_merging, dict):
            return {}
        return data_merging

    def get_merge_by_key(self) -> Optional[str]:
        """
        获取用于跨 API 合并结果的 key（merge_by_key）。

        优先从 renew.data_merging.merge_by_key 读取，
        为兼容老配置，可回退到顶层 merge_by_key。
        """
        data_merging = self.get_data_merging()
        merge_key = data_merging.get("merge_by_key")
        if merge_key:
            return merge_key
        return self.get("merge_by_key")
    
    def get_apis(self) -> Dict[str, Any]:
        """获取 apis 配置（默认空字典）"""
        return self.get("apis") or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于兼容性）"""
        return self._config_dict.copy()

    def is_per_entity(self) -> bool:
        """获取是否是按实体分组"""
        return self.get_group_by() is not None

    def get_group_by(self) -> Dict[str, Any]:
        """
        获取结果分组字段（per-entity 配置）。

        result_group_by.by_key 是「实体标识字段」的唯一配置：既用于构建任务时的实体键，
        也用于增量/滚动续跑时查询表中「每实体的最新日期」（不再使用 last_update_info.group_field）。

        result_group_by.list 语义：
        - "stock_list"：基类会从 dependencies["stock_list"] 解析实体列表；
        - 其他值（如 "stock_index_list"）仅作语义/标签，基类不解析，实体列表需由 handler
          在 on_before_fetch 等钩子中自行注入（如从 ConfigManager 读取）。

        优先从 renew.result_group_by 读取，未配置时回退到顶层 result_group_by。
        """
        renew = self.get("renew") or {}
        group_by = renew.get("result_group_by")
        if isinstance(group_by, dict):
            return group_by
        return self.get("result_group_by")

    def get_group_by_entity_list_name(self) -> Optional[str]:
        """获取实体列表名称；未配置 result_group_by 时返回 None。"""
        group_by = self.get_group_by()
        return group_by.get("list") if isinstance(group_by, dict) else None

    def get_group_by_key(self) -> Optional[str]:
        """
        获取实体标识字段（result_group_by.by_key）。
        用于构建任务与增量/滚动续跑时查询「每实体的最新日期」，为唯一配置来源。
        """
        group_by = self.get_group_by()
        return group_by.get("by_key") if isinstance(group_by, dict) else None

    def get_date_range_required_info(self) -> Dict[str, Any]:
        """获取日期范围计算所需信息"""
        pass