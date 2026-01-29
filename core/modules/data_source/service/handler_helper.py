from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from core.global_enums.enums import UpdateMode
from core.infra.project_context import ConfigManager
from core.modules.data_source.data_class.api_job import ApiJob


class DataSourceHandlerHelper:
    """
    DataSource Handler 侧的辅助方法

    目标：
    - 将 config 中的 apis 转换为 ApiJob 列表；
    - 提供基于 field_mapping / schema 的默认标准化实现；
    - 具体细节都收敛在这里，BaseHandler 中只保留“步骤大纲”。
    """

    # ========== ApiJob 构造 ==========

    @staticmethod
    def build_api_jobs(apis: Dict[str, Any]) -> List[ApiJob]:
        """
        将 config 中的 apis 定义转换为 ApiJob 列表。

        约定（保持宽松，主要由 userspace config 决定）：
        - apis: {
            "<api_name>": {
                "provider_name": "tushare",
                "method": "get_xxx",
                "max_per_minute": 200,                      # 可选，限流信息（每分钟最大请求数）
                "depends_on": ["other_api1", "other_api2"], # 可选，字符串或字符串列表
                "params": {...},                            # 可选，请求参数
                "field_mapping": {...},                     # 可选，字段映射
                ... 其他自定义字段 ...
            },
            ...
          }

        封装规则（不做过多业务理解，只做统一包装）：
        - ApiJob.api_name        = key 名（即 api_name）
        - ApiJob.provider_name   = provider_name
        - ApiJob.method          = method
        - ApiJob.params          = params（默认为 {}）
        - ApiJob.depends_on      = 归一化后的依赖列表（List[str]）
        - ApiJob.rate_limit      = max_per_minute（缺省为一个安全默认值）
        - ApiJob.api_params      = 整个 api 定义（dict，保留原始配置）
        - ApiJob.job_id          = api_name（后续如需可扩展为更复杂规则）
        """
        jobs: List[ApiJob] = []
        default_rate_limit = 50

        if not apis:
            logger.warning(f"apis 为空，返回空列表: {apis}")
            return jobs

        if not isinstance(apis, dict):
            logger.warning(f"apis 应为 dict，当前类型为: {type(apis)}")
            return jobs

        for api_name, api_conf in apis.items():
            if not isinstance(api_conf, dict):
                logger.warning(f"api 配置必须是 dict，当前 {api_name} 类型为: {type(api_conf)}，已跳过")
                continue

            # 依赖关系
            depends_on = api_conf.get("depends_on", [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            elif not isinstance(depends_on, list):
                depends_on = []

            # 限流信息：从 max_per_minute 读取
            max_per_minute = api_conf.get("max_per_minute")
            if max_per_minute is None:
                max_per_minute = default_rate_limit
            try:
                max_per_minute_int = int(max_per_minute)
            except (TypeError, ValueError):
                logger.warning(f"max_per_minute 非法，使用默认值 {default_rate_limit}，当前值: {max_per_minute}")
                max_per_minute_int = default_rate_limit

            # 请求参数
            params = api_conf.get("params") or {}
            if not isinstance(params, dict):
                logger.warning(f"params 应为 dict，当前 {api_name} 类型为: {type(params)}，使用空字典")
                params = {}

            # 构造 ApiJob 实例：一次性通过构造函数注入所有字段，便于检查与对比
            job = ApiJob(
                api_name=api_name,
                provider_name=api_conf.get("provider_name"),
                method=api_conf.get("method"),
                params=params,
                api_params=api_conf,
                depends_on=depends_on,
                rate_limit=max_per_minute_int,
                job_id=api_name,
            )

            jobs.append(job)

        return jobs

    # ========== 日期范围 & renew_mode ==========

    @staticmethod
    def ensure_date_range(context: Dict[str, Any]) -> None:
        """
        根据 config 中的 renew_mode / default_date_range，在 context 中补全 start_date / end_date。

        设计目标：
        - 如果调用方已经在 context 中显式给出了 start_date / end_date，则不做修改；
        - 否则根据 renew_mode + default_date_range 给出一个“合理的默认范围”（不访问数据库）；
        - 复杂的增量 / 滚动逻辑交给上层或专用服务覆盖。

        当前简化策略：
        - 支持的 date_format：day / date / month / quarter / none（不区分大小写，默认 day）；
        - default_date_range: {"years": N}，表示从 N 年前到今天；
        - 不涉及数据库，仅基于当前日期计算。
        """
        if context is None:
            return

        # 已经有日期范围则不干预
        if "start_date" in context and "end_date" in context:
            return

        config: Dict[str, Any] = context.get("config") or {}
        renew_mode = (config.get("renew_mode") or "").lower()
        date_format = (config.get("date_format") or "day").lower()
        default_range = config.get("default_date_range") or {}
        years = int(default_range.get("years") or 1)

        from datetime import datetime, timedelta

        today = datetime.today()
        if date_format in ("day", "date"):
            end = today
            start = today - timedelta(days=365 * years)
            fmt = "%Y-%m-%d"
        elif date_format == "month":
            # 简化：按 30 天一月估算
            end = today
            start = today - timedelta(days=30 * 12 * years)
            fmt = "%Y-%m"
        elif date_format == "quarter":
            # 简化：按 3 个月一季度估算，用 YYYYQn 表示
            year = today.year
            quarter = (today.month - 1) // 3 + 1
            end_str = f"{year}Q{quarter}"
            start_year = year - years
            start_str = f"{start_year}Q1"
            context["start_date"] = start_str
            context["end_date"] = end_str
            logger.info(
                f"📅 自动设置季度范围: {start_str} → {end_str} "
                f"(renew_mode={renew_mode or 'unknown'})"
            )
            return
        else:
            # 不识别的 format 或 none，不设置日期
            logger.info(f"日期格式 {date_format} 不支持自动范围计算，跳过 ensure_date_range")
            return

        start_str = start.strftime(fmt)
        end_str = end.strftime(fmt)
        context["start_date"] = start_str
        context["end_date"] = end_str
        logger.info(
            f"📅 自动设置日期范围: {start_str} → {end_str} "
            f"(renew_mode={renew_mode or 'unknown'}, years={years})"
        )

    @staticmethod
    def is_date_range_specified(context: Dict[str, Any]) -> bool:
        """
        判断 context 中是否已经显式指定了 start_date / end_date。
        """
        if not context:
            return False
        return "start_date" in context and "end_date" in context


    @staticmethod
    def add_date_range(
        apis: List[ApiJob],
        start_date: Any,
        end_date: Any,
        per_stock_date_ranges: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> List[ApiJob]:
        """
        将 start_date / end_date 注入到每个 ApiJob 的 params 中。

        约定：
        - 各 API 对 start_date / end_date 的具体含义由各自的 provider/handler 决定；
        - 此处只做通用注入，子类可以覆盖或在 on_before_fetch 中进一步细化。
        
        Args:
            apis: ApiJob 列表
            start_date: 统一的起始日期（当 per_stock_date_ranges 为 None 时使用）
            end_date: 统一的结束日期（当 per_stock_date_ranges 为 None 时使用）
            per_stock_date_ranges: per stock 的日期范围字典 {stock_id: (start_date, end_date)}
        
        Returns:
            List[ApiJob]: 已注入日期范围的 ApiJob 列表
        """
        if per_stock_date_ranges:
            # per stock 模式：从 ApiJob 的 params 中提取 stock_id，使用对应的日期范围
            for job in apis or []:
                params = job.params or {}
                
                # 尝试从 params 中提取 stock_id（支持多种字段名）
                stock_id = (
                    params.get("ts_code") or 
                    params.get("code") or 
                    params.get("stock_id") or
                    params.get("id")
                )
                
                if stock_id:
                    stock_id_str = str(stock_id)
                    date_range = per_stock_date_ranges.get(stock_id_str)
                    if date_range:
                        job_start_date, job_end_date = date_range
                        if job_start_date is not None:
                            params.setdefault("start_date", job_start_date)
                        if job_end_date is not None:
                            params.setdefault("end_date", job_end_date)
                    else:
                        # 如果找不到对应的日期范围，使用统一的日期范围（降级）
                        logger.warning(f"股票 {stock_id_str} 在 per_stock_date_ranges 中未找到，使用统一日期范围")
                        if start_date is not None:
                            params.setdefault("start_date", start_date)
                        if end_date is not None:
                            params.setdefault("end_date", end_date)
                else:
                    # 如果无法提取 stock_id，使用统一的日期范围（降级）
                    logger.warning(f"ApiJob {job.job_id} 无法提取 stock_id，使用统一日期范围")
                    if start_date is not None:
                        params.setdefault("start_date", start_date)
                    if end_date is not None:
                        params.setdefault("end_date", end_date)
                
                job.params = params
        else:
            # 统一模式：所有 ApiJob 使用相同的日期范围
            for job in apis or []:
                params = job.params or {}
                if start_date is not None:
                    params.setdefault("start_date", start_date)
                if end_date is not None:
                    params.setdefault("end_date", end_date)
                job.params = params
        
        return apis

    @staticmethod
    def compute_default_date_range(context: Dict[str, Any]) -> Any:
        """
        计算一个基于 default_date_range 的默认日期范围（不依赖数据库）。

        返回：
        - (start_date, end_date)，字符串形式，格式取决于 date_format。
        """
        config: Dict[str, Any] = context.get("config") or {}
        date_format = (config.get("date_format") or "day").lower()
        default_range = config.get("default_date_range") or {}
        years = int(default_range.get("years") or 1)

        from datetime import datetime, timedelta

        today = datetime.today()
        if date_format in ("day", "date"):
            end = today
            start = today - timedelta(days=365 * years)
            fmt = "%Y-%m-%d"
            return start.strftime(fmt), end.strftime(fmt)
        elif date_format == "month":
            end = today
            start = today - timedelta(days=30 * 12 * years)
            return start.strftime("%Y-%m"), end.strftime("%Y-%m")
        elif date_format == "quarter":
            year = today.year
            quarter = (today.month - 1) // 3 + 1
            end_str = f"{year}Q{quarter}"
            start_year = year - years
            start_str = f"{start_year}Q1"
            return start_str, end_str
        else:
            return None, None

    @staticmethod
    def compute_incremental_date_range(context: Dict[str, Any]) -> Any:
        """
        计算增量模式下的日期范围（占位实现）。

        当前简化策略：
        - 暂时与 compute_default_date_range 相同；
        - 未来可接入 DataManager，基于最近完成日期和最新交易日精确计算。
        """
        return DataSourceHandlerHelper.compute_default_date_range(context)

    @staticmethod
    def compute_rolling_date_range(context: Dict[str, Any]) -> Any:
        """
        计算滚动模式下的日期范围（占位实现）。

        当前简化策略：
        - 暂时与 compute_default_date_range 相同；
        - 未来可基于 rolling_unit / rolling_length + 最近完成日期精确计算窗口。
        """
        return DataSourceHandlerHelper.compute_default_date_range(context)

    # ========== 标准化（默认实现） ==========

    @staticmethod
    def _apply_field_mapping(
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
                            mapped[target_field] = 0.0 if target_field not in ["date", "quarter", "month"] else ""
                    else:
                        mapped[target_field] = item.get(source_field) if source_field in item else None
            else:
                mapped = item.copy()

            if mapped:
                formatted.append(mapped)

        return formatted

    @staticmethod
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

    @staticmethod
    def apply_schema(records: List[Dict[str, Any]], schema: Any) -> List[Dict[str, Any]]:
        """
        根据 DataSourceSchema 将记录列表规范化到标准字段集。

        行为：
        - 只保留 schema.fields 中定义的字段；
        - 如果缺失字段，使用 DataSourceField.default；
        - 尝试将值转换为 DataSourceField.type。
        """
        if schema is None or not getattr(schema, "fields", None):
            # 没有可用 schema，直接返回原始记录
            return records

        normalized: List[Dict[str, Any]] = []
        fields_def: Dict[str, Any] = schema.fields  # name -> DataSourceField

        for item in records:
            row: Dict[str, Any] = {}
            for field_name, field_def in fields_def.items():
                value = item.get(field_name, getattr(field_def, "default", None))
                field_type = getattr(field_def, "type", None)

                if field_type and value is not None:
                    try:
                        value = field_type(value)
                    except (TypeError, ValueError):
                        logger.warning(
                            f"字段 {field_name} 类型转换失败: "
                            f"值={value} 目标类型={field_type}"
                        )
                row[field_name] = value

            normalized.append(row)

        return normalized

    # ========== 字段覆盖校验 ==========

    @staticmethod
    def validate_field_coverage(apis_conf: Dict[str, Any], schema: Any) -> None:
        """
        校验：schema 中的字段是否都能在各 API 的 field_mapping 中找到对应来源。

        当前行为：
        - 仅做“提醒式”校验，不抛异常；
        - 打印哪些 schema 字段在所有 field_mapping 中都没有出现。
        """
        if schema is None or not getattr(schema, "fields", None):
            return

        schema_fields = set(schema.fields.keys())
        mapped_targets: set[str] = set()

        for api_name, api_cfg in (apis_conf or {}).items():
            fm = api_cfg.get("field_mapping") or {}
            if isinstance(fm, dict):
                mapped_targets.update(fm.keys())

        unmapped = sorted(schema_fields - mapped_targets)
        if unmapped:
            logger.warning(
                "以下 schema 字段在任何 API 的 field_mapping 中都没有配置映射，"
                f"可能导致标准化后缺少这些字段: {unmapped}"
            )

    # ========== 高层标准化入口 ==========

    @staticmethod
    def build_normalized_payload(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将记录列表包装为标准的 {"data": [...]} 结构。
        """
        return {"data": records}

    @staticmethod
    def extract_mapped_records(
        apis_conf: Dict[str, Any],
        fetched_data: Dict[str, Any],
        merge_by_key: str = None,
    ) -> List[Dict[str, Any]]:
        """
        从所有 API 的原始返回中，提取并映射出“已按 field_mapping 转换为标准字段”的记录列表。

        统一规范的 fetched_data 组织形式（BREAKING，所有 handler 需遵守）：

        ```python
        fetched_data = {
            api_name: {
                "_unified": raw_result,     # 全局数据（无实体维度时使用）
                entity_id1: raw_result_1,   # 按实体分组的数据（如 stock_id、index_id 等）
                entity_id2: raw_result_2,
                ...
            },
            ...
        }
        ```

        在统一格式下：
        - 不关心 entity_id 的具体含义（如股票/指数），这里只负责“遍历所有 raw_result 并做映射”；
        - 如果需要将 entity_id 带入记录（如 id 字段），建议在 handler 的 on_after_fetch/on_after_mapping 中处理。

        行为：
        - 遍历每个 API（apis_conf）：
          - 取出 fetched_data[api_name] 作为该 API 的“数据容器”（必须为 dict）；
          - 按 entity 维度遍历每个 raw_result（包括 \"_unified\"）；
          - 对每个 raw_result：
            - 转换为 records 列表；
            - 应用该 API 的 field_mapping；
            - 合并/累加到最终记录列表中。
        """
        if merge_by_key:
            # 按 key 合并模式：使用字典按 key 合并记录
            merged_by_key: Dict[str, Dict[str, Any]] = {}

            for api_name, api_cfg in (apis_conf or {}).items():
                api_data = fetched_data.get(api_name) or {}
                if not isinstance(api_data, dict):
                    logger.warning(
                        f"fetched_data[{api_name}] 不是 dict，期望统一格式 "
                        f"{{api_name: {{entity_id: raw_result}}}}，已跳过"
                    )
                    continue

                for raw in api_data.values():
                    records = DataSourceHandlerHelper.result_to_records(raw)
                    if not records:
                        continue

                    field_mapping = api_cfg.get("field_mapping") or {}
                    mapped = DataSourceHandlerHelper._apply_field_mapping(records, field_mapping)

                    # 按 merge_by_key 合并
                    for record in mapped:
                        key_value = record.get(merge_by_key)
                        if key_value is None:
                            # 如果记录没有 merge_by_key 字段，跳过该记录
                            logger.warning(
                                f"API {api_name} 的记录缺少 merge_by_key 字段 '{merge_by_key}'，跳过该记录"
                            )
                            continue

                        key_str = str(key_value)
                        if key_str not in merged_by_key:
                            # 创建新记录
                            merged_by_key[key_str] = {merge_by_key: key_value}
                        
                        # 合并字段（后处理的 API 会覆盖先处理的 API 的同名字段）
                        merged_by_key[key_str].update(record)

            # 转换为列表
            return list(merged_by_key.values())
        else:
            # 平铺模式：简单累加所有记录
            mapped_records: List[Dict[str, Any]] = []

            for api_name, api_cfg in (apis_conf or {}).items():
                api_data = fetched_data.get(api_name) or {}
                if not isinstance(api_data, dict):
                    logger.warning(
                        f"fetched_data[{api_name}] 不是 dict，期望统一格式 "
                        f"{{api_name: {{entity_id: raw_result}}}}，已跳过"
                    )
                    continue

                field_mapping = api_cfg.get("field_mapping") or {}

                for raw in api_data.values():
                    records = DataSourceHandlerHelper.result_to_records(raw)
                    if not records:
                        continue

                    mapped = DataSourceHandlerHelper._apply_field_mapping(records, field_mapping)
                    mapped_records.extend(mapped)

            return mapped_records

    # ================================
    # Fetched Data 分组与重组
    # ================================

    @staticmethod
    def build_grouped_fetched_data(
        context: Dict[str, Any],
        fetched_data: Dict[str, Any],
        apis: List[ApiJob],
    ) -> Dict[str, Dict[str, Any]]:
        """
        根据配置中的 group_by 规则，将执行层返回的 {job_id: result} 统一整理为标准的
        fetched_data 结构，供 normalize 阶段使用。

        统一规范（BREAKING）：

        fetched_data = {
            api_name: {
                "_unified": raw_result,     # 全局数据（无实体维度或未配置 group_by 时）
                entity_id1: raw_result_1,   # 按实体分组的数据（如 stock_id、index_id 等）
                entity_id2: raw_result_2,
                ...
            }
        }

        规则：
        - 如果某个 api 在 config.apis[api_name] 中配置了 group_by 字段：
          - 例如: {"group_by": "ts_code"}，则按 ApiJob.params["ts_code"] 进行分组；
          - 得到 grouped[api_name][<entity_id>] = raw_result。
        - 如果未配置 group_by 或对应的参数不存在：
          - 默认将该 API 的所有结果合并为一个全局数据块，放入 "_unified"；
          - 如果同一 api_name 多次写入 "_unified"，后写入的结果会覆盖之前的结果，并打印 warning。

        注意：
        - 该方法仅负责“按 API + entity 分组”，不负责字段映射和 schema 处理；
        - 子类如需更复杂的重组逻辑（例如跨 API 合并），可以在 on_after_fetch 中自行调用
          本方法作为基础，或完全自定义实现。
        """
        from loguru import logger

        config = context.get("config")
        if hasattr(config, "get_apis"):
            apis_conf = config.get_apis()
        else:
            apis_conf = (config or {}).get("apis", {}) if isinstance(config, dict) else {}

        grouped: Dict[str, Dict[str, Any]] = {}

        for api_job in apis or []:
            api_name = getattr(api_job, "api_name", None)
            job_id = getattr(api_job, "job_id", None) or api_name
            if not api_name or not job_id:
                continue

            raw_result = fetched_data.get(job_id)
            if raw_result is None:
                continue

            api_conf = apis_conf.get(api_name, {})
            group_by = None
            if isinstance(api_conf, dict):
                group_by = api_conf.get("group_by")
            elif hasattr(api_conf, "get"):
                group_by = api_conf.get("group_by", None)

            bucket = grouped.setdefault(api_name, {})

            if group_by:
                # 按声明的参数名从 params 中提取实体 ID
                entity_id = getattr(api_job, "params", {}).get(group_by)
                if entity_id is None:
                    logger.warning(
                        f"[DataSource:{context.get('data_source_name', 'unknown')}][API:{api_name}] "
                        f"配置了 group_by='{group_by}'，但 ApiJob.params 中未找到对应键，"
                        "将该结果回退到 '_unified' 分组。"
                    )
                    if "_unified" in bucket:
                        logger.warning(
                            f"[DataSource:{context.get('data_source_name', 'unknown')}][API:{api_name}] "
                            "存在多个未能识别实体 ID 的结果，写入同一 '_unified' 分组，后写将覆盖前写。"
                        )
                    bucket["_unified"] = raw_result
                else:
                    bucket[str(entity_id)] = raw_result
            else:
                # 未配置 group_by：默认按全局 unified 处理
                if "_unified" in bucket:
                    logger.warning(
                        f"[DataSource:{context.get('data_source_name', 'unknown')}][API:{api_name}] "
                        "在未配置 group_by 的情况下产生了多个结果，将按顺序覆盖 '_unified'。"
                    )
                bucket["_unified"] = raw_result

        return grouped

    @staticmethod
    def build_unified_fetched_data(
        context: Dict[str, Any],
        fetched_data: Dict[str, Any],
        apis: List[ApiJob],
    ) -> Dict[str, Dict[str, Any]]:
        """
        不考虑 group_by，简单按 api_name 聚合结果到 "_unified"。

        适用于：
        - 所有 API 都是全局数据（无实体维度）；
        - 或者暂时不希望在 BaseHandler 层做实体分组，只要一个统一的数据块。
        """
        from loguru import logger

        unified: Dict[str, Dict[str, Any]] = {}

        for api_job in apis or []:
            api_name = getattr(api_job, "api_name", None)
            job_id = getattr(api_job, "job_id", None) or api_name
            if not api_name or not job_id:
                continue

            raw_result = fetched_data.get(job_id)
            if raw_result is None:
                continue

            bucket = unified.setdefault(api_name, {})
            if "_unified" in bucket:
                logger.warning(
                    f"[DataSource:{context.get('data_source_name', 'unknown')}][API:{api_name}] "
                    "未使用 group_by 但产生了多个结果，将按顺序覆盖 '_unified'。"
                )
            bucket["_unified"] = raw_result

        return unified

    # ================================
    # 配置辅助工具
    # ================================

    @staticmethod
    def has_group_by_config(context: Dict[str, Any], apis: List[ApiJob]) -> bool:
        """
        检查本次执行涉及的 API 中，是否至少有一个配置了 group_by。
        """
        config = context.get("config")
        if hasattr(config, "get_apis"):
            apis_conf = config.get_apis()
        else:
            apis_conf = (config or {}).get("apis", {}) if isinstance(config, dict) else {}

        for api_job in apis or []:
            api_name = getattr(api_job, "api_name", None)
            if not api_name:
                continue
            api_conf = apis_conf.get(api_name, {})
            group_by = None
            if isinstance(api_conf, dict):
                group_by = api_conf.get("group_by")
            elif hasattr(api_conf, "get"):
                group_by = api_conf.get("group_by", None)
            if group_by:
                return True

        return False

    # ================================
    # 通用字段/日期/NaN 处理工具
    # ================================

    @staticmethod
    def add_constant_fields(
        records: List[Dict[str, Any]],
        **fields: Any,
    ) -> List[Dict[str, Any]]:
        """
        在一批记录上追加固定字段（原地修改并返回）。
        """
        if not records or not fields:
            return records
        for r in records:
            if isinstance(r, dict):
                r.update(fields)
        return records

    @staticmethod
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
                - "quarter": YYYYQ[1-4]
                - "none": 跳过标准化

        - 支持常见输入形式：YYYYMMDD, YYYY-MM-DD, datetime/date 等；
        - 不可解析的日期会被跳过（保留原值），由上层决定是否过滤。
        """
        if not records or not field or target_format == "none":
            return records

        try:
            from core.utils.date.date_utils import DateUtils, DateFormat
        except ImportError:
            logger = DataSourceHandlerHelper._get_logger()
            logger.warning("无法导入 DateUtils，normalize_date_field 将跳过处理")
            return records

        # 将字符串格式转换为枚举
        format_map = {
            "day": DateFormat.DAY,
            "month": DateFormat.MONTH,
            "quarter": DateFormat.QUARTER,
            "none": DateFormat.NONE,
        }
        output_format = format_map.get(target_format.lower(), DateFormat.DAY)

        for r in records:
            if not isinstance(r, dict) or field not in r:
                continue
            value = r.get(field)
            if value is None:
                continue
            
            try:
                normalized = DateUtils.normalize_to_format(value, output_format)
                if normalized:
                    r[field] = normalized
            except Exception:
                # 保留原值，交给上层决定是否过滤
                continue

        return records

    @staticmethod
    def clean_nan_in_records(
        records: List[Dict[str, Any]],
        default: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        使用 DBHelper 将一批记录中的 NaN/None 等异常数值清洗为默认值。
        """
        if not records:
            return records
        try:
            from core.infra.db.helpers.db_helpers import DBHelper
        except ImportError:
            logger = DataSourceHandlerHelper._get_logger()
            logger.warning("无法导入 DBHelper，clean_nan_in_records 将跳过处理")
            return records
        return DBHelper.clean_nan_in_list(records, default=default)

    @staticmethod
    def _get_logger():
        from loguru import logger  # 局部导入，避免强依赖
        return logger

    @staticmethod
    def normalize_fetched_data(context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        默认标准化实现（支持多 API，但不做复杂合并，仅做“平铺 + 映射 + schema 约束”）。

        步骤：
        1. 从 context 中解析 apis 配置和 schema；
        2. 遍历每个 API：
           - 从 fetched_data 中取出对应结果；
           - 转换为 records 列表；
           - 应用该 API 的 field_mapping；
           - 追加到总 records 列表；
        3. 将所有 records 通过 schema 规范化字段集和类型；
        4. 包装为 {"data": [...]} 返回。
        """
        config: Dict[str, Any] = context.get("config") or {}
        apis_conf: Dict[str, Any] = config.get("apis") or {}
        schema = context.get("schema")

        if not fetched_data or not isinstance(fetched_data, dict):
            logger.info("fetched_data 为空或类型非法，返回空数据")
            return {"data": []}

        # 步骤 1：字段覆盖校验（提醒式）
        DataSourceHandlerHelper.validate_field_coverage(apis_conf, schema)

        # 步骤 2：对每个 API 结果做 field_mapping，合并为 records
        mapped_records = DataSourceHandlerHelper.extract_mapped_records(apis_conf, fetched_data)

        if not mapped_records:
            logger.info("所有 API 结果均为空，返回空数据")
            return {"data": []}

        # 步骤 3：应用 schema 进行字段规范化
        normalized_records = DataSourceHandlerHelper.apply_schema(mapped_records, schema)
        logger.info(f"✅ 默认标准化完成，记录数={len(normalized_records)}")
        # 步骤 4：包装成标准 payload
        return DataSourceHandlerHelper.build_normalized_payload(normalized_records)

    # ========== 数据验证 ==========

    @staticmethod
    def validate_normalized_data(normalized_data: Dict[str, Any], schema: Any, data_source_name: str = "unknown") -> None:
        """
        验证标准化后的数据是否符合 schema。

        验证逻辑：
        - 如果数据是 {"data": [...]} 格式，验证列表中的每个记录
        - 如果数据不是 {"data": [...]} 格式，直接验证整个字典
        - 校验失败时抛出 ValueError

        Args:
            normalized_data: 标准化后的数据，通常是 {"data": [...]} 格式
            schema: Schema 对象（用于验证）
            data_source_name: 数据源名称（用于错误信息）

        Raises:
            ValueError: 如果数据验证失败
        """
        if not schema:
            # 如果没有 schema，跳过验证
            return

        # 如果数据是 {"data": [...]} 格式，验证列表中的每个记录
        if isinstance(normalized_data, dict) and "data" in normalized_data:
            data_list = normalized_data.get("data", [])
            if not isinstance(data_list, list):
                raise ValueError(
                    f"数据验证失败: {data_source_name} 的 data 字段不是列表类型"
                )
            
            # 验证列表中的每个记录
            errors = []
            for idx, record in enumerate(data_list):
                if not isinstance(record, dict):
                    errors.append(f"记录 {idx} 不是字典类型")
                    continue
                
                if not schema.validate_data(record):
                    # 收集错误信息
                    record_errors = DataSourceHandlerHelper._collect_validation_errors(record, schema)
                    if record_errors:
                        errors.append(f"记录 {idx}: {', '.join(record_errors)}")
            
            if errors:
                raise ValueError(
                    f"数据验证失败: {data_source_name} 的标准化数据不符合 schema 定义。"
                    f"错误详情: {'; '.join(errors)}"
                )
            return
        
        # 如果数据不是 {"data": [...]} 格式，直接验证整个字典
        if not schema.validate_data(normalized_data):
            errors = DataSourceHandlerHelper._collect_validation_errors(normalized_data, schema)
            error_msg = ', '.join(errors) if errors else "数据不符合 schema 定义"
            raise ValueError(
                f"数据验证失败: {data_source_name} 的标准化数据不符合 schema 定义。"
                f"错误详情: {error_msg}"
            )

    @staticmethod
    def _collect_validation_errors(record: Dict[str, Any], schema: Any) -> List[str]:
        """
        收集数据验证错误信息。

        Args:
            record: 单条记录（字典）
            schema: Schema 对象

        Returns:
            List[str]: 错误信息列表
        """
        errors = []
        
        for field_name, field_def in schema.fields.items():
            if field_def.required and field_name not in record:
                errors.append(f"{field_name}(缺失)")
            elif field_name in record and record[field_name] is not None:
                value = record[field_name]
                expected_type = field_def.type
                if not DataSourceHandlerHelper._check_type(value, expected_type):
                    errors.append(
                        f"{field_name}(类型错误: {type(value).__name__} != {expected_type.__name__})"
                    )
        
        return errors

    @staticmethod
    def _check_type(value: Any, expected_type: type) -> bool:
        """
        检查类型（支持类型转换）。

        Args:
            value: 值
            expected_type: 期望的类型

        Returns:
            bool: 是否符合类型（或可以转换）
        """
        if isinstance(value, expected_type):
            return True
        
        # 尝试类型转换
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

    # ================================
    # Renew 辅助：一次性获取所有实体的 last_update 映射
    # ================================

    @staticmethod
    def get_last_update_map(
        context: Dict[str, Any],
        renew_mode: UpdateMode,
    ) -> Dict[str, Optional[str]]:
        """
        获取所有实体的“本次抓取起点”映射。

        语义：
        - REFRESH:   不查 DB，所有实体统一从全局 default_start_date 开始；
        - 其他模式:  一次性从 DB 查询原始 latest_date，再根据 renew_mode 计算起点。
        """
        # per-entity 的实体列表（例如 dependencies["entity_list"]）
        deps = context.get("dependencies") or {}
        entity_list = deps.get("entity_list")

        if renew_mode == UpdateMode.REFRESH:
            if not entity_list:
                return {}
            default_start = ConfigManager.get_default_start_date()
            return {str(entity_id): default_start for entity_id in entity_list}

        # 非 refresh：统一查一次 DB，拿到原始 last_update，再按模式转换为“起点”
        raw_last_update_map = DataSourceHandlerHelper.compute_last_update_map(context)
        result: Dict[str, Optional[str]] = {}

        if entity_list:
            for entity_id in entity_list:
                key = str(entity_id)
                raw_last = raw_last_update_map.get(key)
                start_date = DataSourceHandlerHelper.calc_last_update_based_on_renew_mode(
                    context, entity_id=key, last_update=raw_last
                )
                result[key] = start_date
        else:
            # 没有显式 entity_list，就直接对 DB 返回的 key 做转换
            for key, raw_last in raw_last_update_map.items():
                start_date = DataSourceHandlerHelper.calc_last_update_based_on_renew_mode(
                    context, entity_id=str(key), last_update=raw_last
                )
                result[str(key)] = start_date

        return result

    @staticmethod
    def get_last_update(
        context: Dict[str, Any],
        renew_mode: UpdateMode,
    ) -> Optional[str]:
        """
        获取“单实体/全局”的本次抓取起点日期。

        - REFRESH:   直接使用全局 default_start_date；
        - 其他模式:  从 DB 查询当前数据源的最新日期，再根据 renew_mode 计算本次起点。
        """
        if renew_mode == UpdateMode.REFRESH:
            return ConfigManager.get_default_start_date()

        # 使用 compute_last_update_map 的全局分支（"_global"）获取原始 last_update
        raw_map = DataSourceHandlerHelper.compute_last_update_map(context)
        raw_last = raw_map.get("_global")
        return DataSourceHandlerHelper.calc_last_update_based_on_renew_mode(
            context, entity_id=None, last_update=raw_last
        )

    @staticmethod
    def compute_last_update_map(context: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        计算所有实体的“原始”最近更新时间（latest_date）映射（不考虑 renew_mode）。

        - per-entity 场景：一次性查询整张表，返回 {entity_id: latest_date_str}；
        - 非 per-entity 场景：查询整表最新一条记录，返回 {"_global": latest_date_str}；
        - 如果表为空或查询失败，对应值为 None 或空 dict。
        """
        from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper
        from loguru import logger

        data_manager = context.get("data_manager")
        config = context.get("config")

        if not data_manager or not config:
            return {}

        table_name = config.get_table_name()
        date_field = config.get_date_field()
        date_format = config.get_date_format()

        if not table_name or not date_field:
            logger.warning("table_name 或 date_field 未配置，无法计算 last_update 映射")
            return {}

        last_update_map: Dict[str, Optional[str]] = {}

        # 是否需要按实体分组（如 per stock）
        needs_stock_grouping = RenewCommonHelper.get_needs_stock_grouping(context)

        if not needs_stock_grouping:
            # 全局数据：查询整表最新一条记录
            try:
                model = data_manager.get_table(table_name)
                if not model:
                    last_update_map["_global"] = None
                    return last_update_map

                latest_record = model.load_one("1=1", order_by=f"{date_field} DESC")
                if not latest_record:
                    last_update_map["_global"] = None
                    return last_update_map

                raw_value = latest_record.get(date_field)
                last_update_map["_global"] = (
                    DataSourceHandlerHelper._normalize_date_value(raw_value) if raw_value else None
                )
                return last_update_map
            except Exception as e:
                logger.warning(f"查询全局 last_update 失败: {e}")
                # 查询失败时，保守返回空映射（后续逻辑会当作“无 last_update”处理）
                return {}

        # per-entity：一次性查询所有实体的最新日期
        latest_dates_dict = RenewCommonHelper.query_latest_date(
            data_manager=data_manager,
            table_name=table_name,
            date_field=date_field,
            date_format=date_format,
            needs_stock_grouping=needs_stock_grouping,
        )

        if not latest_dates_dict:
            # 表为空或查询失败：所有实体视为没有 last_update
            return {}

        # latest_dates_dict: {entity_id: latest_date_raw}
        for entity_id, raw_value in latest_dates_dict.items():
            if not raw_value:
                last_update_map[str(entity_id)] = None
            else:
                last_update_map[str(entity_id)] = DataSourceHandlerHelper._normalize_date_value(
                    raw_value
                )

        return last_update_map

    @staticmethod
    def calc_last_update_based_on_renew_mode(
        context: Dict[str, Any],
        entity_id: Optional[str] = None,
        last_update: Optional[str] = None,
    ) -> Optional[str]:
        """
        根据 renew_mode 对“原始” last_update 做一次性转换，得到本次抓取的起点日期（start_date）。

        说明：
        - 该方法只负责“last_update → start_date”的纯函数逻辑，不参与是否触发本次更新的判断；
        - 是否需要触发由上层通过 renew_if_over_days 或其他规则统一决定；
        - 返回值为标准化后的字符串日期，格式由 config.date_format 决定。
        """
        from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper
        from core.utils.date.date_utils import DateUtils
        from core.global_enums.enums import TermType, UpdateMode
        from loguru import logger

        if not context:
            return None

        config = context.get("config")
        data_manager = context.get("data_manager")

        if not config:
            logger.warning("Config 未初始化，无法根据 renew_mode 计算起点日期")
            return None

        renew_mode = config.get_renew_mode()
        date_format = config.get_date_format()

        # 统一的默认起点（用于新实体或 last_update 缺失 / 非法时兜底）
        try:
            default_start_date, _ = RenewCommonHelper.get_default_date_range(
                data_manager, date_format, context
            )
        except Exception:
            # 极端情况下回退到全局配置
            default_start_date = ConfigManager.get_default_start_date()

        # REFRESH：全量刷新，直接从默认起点开始
        if renew_mode == UpdateMode.REFRESH:
            return default_start_date

        # INCREMENTAL：从 last_update 的后一个周期开始
        if renew_mode == UpdateMode.INCREMENTAL:
            if not last_update:
                return default_start_date
            try:
                start_value = DateUtils.add_one_period(last_update, date_format)
                return DateUtils.format_period(start_value, date_format)
            except Exception:
                return default_start_date

        # ROLLING：滚动窗口
        if renew_mode == UpdateMode.ROLLING:
            rolling_unit = config.get_rolling_unit()
            rolling_length = config.get_rolling_length()

            if not rolling_unit or not rolling_length:
                # 未配置滚动窗口，退化为增量模式（保持与 IncrementalRenewService 一致）
                if not last_update:
                    return default_start_date
                try:
                    start_value = DateUtils.add_one_period(last_update, date_format)
                    return DateUtils.format_period(start_value, date_format)
                except Exception:
                    return default_start_date

            # 支持 TermType / str 两种形式
            _rolling_unit = rolling_unit.value if isinstance(rolling_unit, TermType) else rolling_unit
            _date_format = date_format

            # 将 rolling_length 转换为与 date_format 对齐的“周期数”
            def _convert_rolling_length_to_periods() -> int:
                if _rolling_unit == TermType.QUARTERLY.value:
                    if _date_format == TermType.QUARTERLY.value:
                        return rolling_length
                    elif _date_format == TermType.MONTHLY.value:
                        return rolling_length * 3
                    else:  # daily
                        return rolling_length * 90
                elif _rolling_unit == TermType.MONTHLY.value:
                    if _date_format == TermType.QUARTERLY.value:
                        return (rolling_length + 2) // 3
                    elif _date_format == TermType.MONTHLY.value:
                        return rolling_length
                    else:  # daily
                        return rolling_length * 30
                else:  # DAILY
                    if _date_format == TermType.QUARTERLY.value:
                        return (rolling_length + 90) // 90
                    elif _date_format == TermType.MONTHLY.value:
                        return (rolling_length + 30) // 30
                    else:
                        return rolling_length

            rolling_periods = _convert_rolling_length_to_periods()

            # 计算当前 end_value（统一为“最近完成交易日”对应周期）
            latest_completed_trading_date = context.get("latest_completed_trading_date")
            try:
                if not latest_completed_trading_date and data_manager and getattr(
                    data_manager, "service", None
                ):
                    latest_completed_trading_date = (
                        data_manager.service.calendar.get_latest_completed_trading_date()
                    )
            except Exception:
                latest_completed_trading_date = None

            if latest_completed_trading_date:
                end_value = DateUtils.get_current_period(
                    latest_completed_trading_date, date_format
                )
            else:
                current_date = DateUtils.get_current_date_str()
                end_value = DateUtils.get_current_period(current_date, date_format)

            rolling_start_value = DateUtils.subtract_periods(
                end_value, rolling_periods, date_format
            )
            rolling_start_date = DateUtils.format_period(rolling_start_value, date_format)

            if not last_update:
                # 表为空或新实体：退化为默认起点
                return default_start_date

            try:
                period_diff = DateUtils.calculate_period_diff(
                    last_update, end_value, date_format
                )
            except Exception:
                return default_start_date

            if period_diff <= rolling_periods:
                # 在 rolling 窗口内：直接从 rolling_start 开始
                return rolling_start_date

            # 落后太多：从 last_update 的后一个周期开始追
            try:
                start_value = DateUtils.add_one_period(last_update, date_format)
                return DateUtils.format_period(start_value, date_format)
            except Exception:
                return default_start_date

        # 未知 / 未配置模式：退化为简单增量
        if not last_update:
            return default_start_date
        try:
            start_value = DateUtils.add_one_period(last_update, date_format)
            return DateUtils.format_period(start_value, date_format)
        except Exception:
            return default_start_date

    # ================================
    # Renew 辅助：基于 last_update + renew_mode 计算起止日期
    # ================================

    @staticmethod
    def compute_entity_date_ranges(
        context: Dict[str, Any],
        last_update_map: Dict[str, Optional[str]],
    ) -> Dict[str, Tuple[str, str]]:
        """
        基于 last_update 映射和 renew_mode 计算各实体本次应抓取的 (start_date, end_date)。

        步骤：
        1. 根据 renew_mode 决定基础策略（refresh / incremental / rolling）；
        2. 计算 end_date（通常是 latest_completed_trading_date 对应的周期）；
        3. 计算默认起点 default_start_date（用于新实体或表为空）；
        4. 可选：根据 renew_if_over_days 决定哪些实体需要 trigger；
        5. 对于需要 trigger 的实体，按模式生成 start_date：
           - refresh: 一律从 default_start_date 起；
           - incremental: 从 last_update 的后一个周期起（新实体从 default_start_date 起）；
           - rolling: 先算 rolling 窗口起点，再与 last_update 对比决定从 rolling_start 或 last_update+1 起。
        """
        from loguru import logger
        from core.global_enums.enums import UpdateMode
        from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper
        from core.utils.date.date_utils import DateUtils

        config = context.get("config")
        data_manager = context.get("data_manager")

        if not config:
            logger.warning("Config 未初始化，无法计算实体日期范围")
            return {}

        # 1. 解析更新模式
        renew_mode = config.get_renew_mode()
        date_format = config.get_date_format()

        # 2. 计算统一的 end_date（按 date_format 标准化）
        end_date = RenewCommonHelper.get_end_date(date_format, context)

        # 3. 计算默认起点（用于新实体或表为空）
        default_start_date, _ = RenewCommonHelper.get_default_date_range(
            data_manager, date_format, context
        )

        # 4. 可选：读取 renew_if_over_days 配置，用于 trigger gating
        threshold_cfg = config.get_renew_if_over_days()
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            try:
                if data_manager and getattr(data_manager, "service", None):
                    latest_completed_trading_date = (
                        data_manager.service.calendar.get_latest_completed_trading_date()
                    )
                else:
                    latest_completed_trading_date = DateUtils.get_current_date_str()
            except Exception:
                latest_completed_trading_date = DateUtils.get_current_date_str()

        def should_trigger(last_update: Optional[str]) -> bool:
            """根据 renew_if_over_days 判断是否需要触发本次更新。"""
            if not threshold_cfg:
                return True

            threshold_days = threshold_cfg.get("value")
            if not threshold_days:
                # 未配置 value，当作始终需要更新
                return True

            if not last_update:
                # 没有 last_update（新实体或表为空）→ 需要更新
                return True

            try:
                days_diff = DateUtils.get_duration_in_days(
                    last_update, latest_completed_trading_date
                )
            except Exception:
                # 日期解析失败，保守策略：更新
                return True

            # 与 check_renew_if_over_days 保持一致：
            # days_diff >= threshold → 需要更新；否则跳过
            return days_diff >= threshold_days

        # 5. 根据需要分组与否，分别计算
        needs_stock_grouping = RenewCommonHelper.get_needs_stock_grouping(context)
        result: Dict[str, Tuple[str, str]] = {}

        # 公共：根据模式计算起点
        def compute_start_for_mode(last_update: Optional[str]) -> str:
            # refresh: 总是从默认起点开始刷全量
            if renew_mode == UpdateMode.REFRESH:
                return default_start_date

            # incremental: from last_update+1，否则从默认起点
            if renew_mode == UpdateMode.INCREMENTAL:
                if not last_update:
                    return default_start_date
                try:
                    start_value = DateUtils.add_one_period(last_update, date_format)
                    return DateUtils.format_period(start_value, date_format)
                except Exception:
                    # 回退到默认起点
                    return default_start_date

            # rolling 模式
            if renew_mode == UpdateMode.ROLLING:
                rolling_unit = config.get_rolling_unit()
                rolling_length = config.get_rolling_length()
                if not rolling_unit or not rolling_length:
                    # 未配置滚动窗口时，退化为增量模式
                    return compute_start_for_mode(last_update=None if not last_update else last_update)

                # 计算 rolling_periods（尽量复用 RollingRenewService 的语义）
                # 支持 TermType / str 两种形式
                from core.global_enums.enums import TermType

                _rolling_unit = rolling_unit.value if isinstance(rolling_unit, TermType) else rolling_unit
                _date_format = date_format

                # 将 rolling_unit 转为与 date_format 对齐的周期数
                def _convert_rolling_length_to_periods() -> int:
                    if _rolling_unit == TermType.QUARTERLY.value:
                        if _date_format == TermType.QUARTERLY.value:
                            return rolling_length
                        elif _date_format == TermType.MONTHLY.value:
                            return rolling_length * 3
                        else:  # daily
                            return rolling_length * 90
                    elif _rolling_unit == TermType.MONTHLY.value:
                        if _date_format == TermType.QUARTERLY.value:
                            return (rolling_length + 2) // 3
                        elif _date_format == TermType.MONTHLY.value:
                            return rolling_length
                        else:  # daily
                            return rolling_length * 30
                    else:  # DAILY
                        if _date_format == TermType.QUARTERLY.value:
                            return (rolling_length + 90) // 90
                        elif _date_format == TermType.MONTHLY.value:
                            return (rolling_length + 30) // 30
                        else:
                            return rolling_length

                rolling_periods = _convert_rolling_length_to_periods()

                # 计算 end_value / rolling_start
                if latest_completed_trading_date:
                    end_value = DateUtils.get_current_period(
                        latest_completed_trading_date, date_format
                    )
                else:
                    current_date = DateUtils.get_current_date_str()
                    end_value = DateUtils.get_current_period(current_date, date_format)

                rolling_start_value = DateUtils.subtract_periods(
                    end_value, rolling_periods, date_format
                )
                rolling_start_date = DateUtils.format_period(
                    rolling_start_value, date_format
                )

                if not last_update:
                    # 没有 last_update：退化为从默认起点
                    return default_start_date

                try:
                    period_diff = DateUtils.calculate_period_diff(
                        last_update, end_value, date_format
                    )
                except Exception:
                    # 日期解析失败，保守策略：从默认起点
                    return default_start_date

                if period_diff <= rolling_periods:
                    # 在 rolling 窗口内：从 rolling_start 起
                    return rolling_start_date

                # 落后太多：从 last_update 的后一个周期开始追
                try:
                    start_value = DateUtils.add_one_period(last_update, date_format)
                    return DateUtils.format_period(start_value, date_format)
                except Exception:
                    return default_start_date

            # 未知或未配置的模式：退化为增量模式逻辑
            if not last_update:
                return default_start_date
            try:
                start_value = DateUtils.add_one_period(last_update, date_format)
                return DateUtils.format_period(start_value, date_format)
            except Exception:
                return default_start_date

        # 非 per-entity：只算一条 "_global"
        if not needs_stock_grouping:
            last_update = last_update_map.get("_global")
            if not should_trigger(last_update):
                return {}
            start_date = compute_start_for_mode(last_update)
            result["_global"] = (start_date, end_date)
            return result

        # per-entity：按 stock_list 遍历实体
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("needs_stock_grouping=True 但 context['stock_list'] 为空，返回空日期范围")
            return {}

        for stock_id in stock_list:
            entity_id = str(stock_id)
            last_update = last_update_map.get(entity_id)
            if not should_trigger(last_update):
                continue
            start_date = compute_start_for_mode(last_update)
            result[entity_id] = (start_date, end_date)

        return result

    @staticmethod
    def check_renew_if_over_days(
        context: Dict[str, Any],
        threshold_config: Dict[str, Any],
        stock_list: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[List[str]]:
        """
        检查 renew_if_over_days，返回需要更新的 entity 列表（candidates）。
        
        流程：
        1. 判断是全局数据还是 per entity
        2. 从数据库一次性查询所有需要对比的数据（per entity 就是每个 entity 一条，不是就是 1 条）
        3. 对比：没有时间记录或超过 threshold 的进入 candidates
        4. 返回 candidates list
        
        Args:
            context: 执行上下文（包含 config, data_manager 等）
            threshold_config: renew_if_over_days 配置字典
            stock_list: 股票列表（可选，如果提供则只检查这些股票）
        
        Returns:
            - None: 不过滤（全局数据且需要更新，或表为空）
            - []: 过滤掉所有 ApiJobs（全局数据且不需要更新）
            - List[str]: 需要更新的 entity ID 列表（candidates，per entity 模式）
        """
        from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper
        from core.utils.date.date_utils import DateUtils
        from loguru import logger
        
        if not threshold_config:
            return None
        
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法检查 renew_if_over_days")
            return None
        
        config = context.get("config")
        if not config:
            logger.warning("Config 未初始化，无法检查 renew_if_over_days")
            return None
        
        # 获取配置
        table_name = config.get_table_name()
        if not table_name:
            logger.warning("table_name 未配置，无法检查 renew_if_over_days")
            return None
        
        threshold_days = threshold_config.get("value")
        if not threshold_days:
            logger.warning("renew_if_over_days.value 未配置")
            return None
        
        # counting_field 默认使用 config 的 date_field，除非专门声明
        counting_field = threshold_config.get("counting_field") or config.get_date_field()
        if not counting_field:
            logger.warning("counting_field 未配置且 date_field 也未配置，无法检查 renew_if_over_days")
            return None
        
        # 获取结束日期（当前日期）
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            try:
                latest_completed_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新完成交易日失败: {e}")
                latest_completed_trading_date = DateUtils.get_current_date_str()
        
        # ========== 步骤1：判断是全局数据还是 per entity ==========
        needs_stock_grouping = RenewCommonHelper.get_needs_stock_grouping(context)
        
        # ========== 步骤2：从数据库一次性查询所有需要对比的数据 ==========
        if not needs_stock_grouping:
            # 全局数据：查询 1 条最新记录
            try:
                model = data_manager.get_table(table_name)
                if not model:
                    return None
                
                latest_record = model.load_one("1=1", order_by=f"{counting_field} DESC")
                if not latest_record:
                    # 表为空，返回 None（不过滤）
                    return None
                
                latest_date = latest_record.get(counting_field)
                if not latest_date:
                    # 没有时间记录，返回 None（不过滤，需要更新）
                    return None
                
                # 标准化日期格式
                latest_date_str = DataSourceHandlerHelper._normalize_date_value(latest_date)
                if not latest_date_str:
                    return None
                
                # ========== 步骤3：对比 - 计算天数差 ==========
                days_diff = DateUtils.get_duration_in_days(latest_date_str, latest_completed_trading_date)
                
                if days_diff >= threshold_days:
                    # 超过 threshold，返回 None（不过滤，需要更新）
                    return None
                else:
                    # 没过 threshold，返回空列表（过滤掉所有 ApiJobs）
                    return []
                    
            except Exception as e:
                logger.warning(f"查询全局数据最新日期失败: {e}")
                return None
        
        # Per entity：一次性查询所有 entity 的最新记录
        date_format = config.get_date_format()
        latest_dates_dict = RenewCommonHelper.query_latest_date(
            data_manager, table_name, counting_field, date_format, needs_stock_grouping
        )
        
        if not latest_dates_dict:
            # 表为空，返回 None（不过滤）
            return None
        
        # ========== 步骤3：对比 - 遍历所有 entity，找出 candidates ==========
        candidates = []
        
        for entity_id, latest_date in latest_dates_dict.items():
            if not latest_date:
                # 没有时间记录，进入 candidates
                candidates.append(entity_id)
                continue
            
            # 标准化日期格式
            latest_date_str = DataSourceHandlerHelper._normalize_date_value(latest_date)
            if not latest_date_str:
                # 日期格式错误，保守策略：进入 candidates
                candidates.append(entity_id)
                continue
            
            # 计算天数差
            try:
                days_diff = DateUtils.get_duration_in_days(latest_date_str, latest_completed_trading_date)
                
                if days_diff >= threshold_days:
                    # 超过 threshold，进入 candidates
                    candidates.append(entity_id)
            except Exception as e:
                logger.warning(f"计算 entity {entity_id} 的天数差失败: {e}")
                # 计算失败，保守策略：进入 candidates
                candidates.append(entity_id)
        
        # 如果提供了 stock_list，只返回在 stock_list 中的 entity
        if stock_list:
            stock_ids = {stock.get("id") or stock.get("ts_code") for stock in stock_list if stock.get("id") or stock.get("ts_code")}
            candidates = [eid for eid in candidates if eid in stock_ids]
        
        return candidates if candidates else None
    
    @staticmethod
    def _normalize_date_value(date_value: Any) -> Optional[str]:
        """
        标准化日期值（处理 datetime 对象或其他格式）
        
        Args:
            date_value: 日期值（可能是 datetime、str 或其他格式）
        
        Returns:
            str: YYYYMMDD 格式的日期字符串，如果无法解析返回 None
        """
        from datetime import datetime as dt
        from core.utils.date.date_utils import DateUtils
        from loguru import logger
        
        try:
            if isinstance(date_value, dt):
                return date_value.strftime('%Y%m%d')
            elif isinstance(date_value, str):
                return DateUtils.normalize_date(date_value) or date_value
            else:
                return str(date_value).replace('-', '').replace(' ', '').replace(':', '')[:8]
        except Exception as e:
            logger.debug(f"标准化日期格式失败: {date_value}, error: {e}")
            return None

