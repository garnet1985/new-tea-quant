from typing import Any, Dict, List

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

