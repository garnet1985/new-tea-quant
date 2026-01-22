from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

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
    ) -> List[Dict[str, Any]]:
        """
        从所有 API 的原始返回中，提取并映射出“已按 field_mapping 转换为标准字段”的记录列表。

        行为：
        - 遍历每个 API：
          - 取出 fetched_data[api_name] 作为原始结果；
          - 转换为 records 列表；
          - 应用该 API 的 field_mapping；
          - 将映射后的记录累加到 mapped_records 中。
        """
        mapped_records: List[Dict[str, Any]] = []

        for api_name, api_cfg in (apis_conf or {}).items():
            result = fetched_data.get(api_name)
            if result is None:
                continue

            records = DataSourceHandlerHelper.result_to_records(result)
            if not records:
                continue

            field_mapping = api_cfg.get("field_mapping") or {}
            mapped = DataSourceHandlerHelper._apply_field_mapping(records, field_mapping)
            mapped_records.extend(mapped)

        return mapped_records

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

