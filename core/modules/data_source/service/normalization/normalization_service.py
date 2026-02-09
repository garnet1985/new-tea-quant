"""
NormalizationService - 标准化阶段的集中实现。

当前实现基本沿用 BaseHandler._normalize_data 的逻辑，仅做轻量封装，
方便后续逐步拆分字段映射 / schema 应用 / 日期标准化等职责。
"""
from typing import Any, Dict, List

from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.normalization import normalization_helper as nh


class NormalizationService:
    """负责将 fetched_data 标准化为统一的 {"data": [...]} 结构。"""

    @staticmethod
    def normalize(context: Dict[str, Any], fetched_data: Any) -> Dict[str, Any]:
        """
        默认标准化实现（与 BaseHandler._normalize_data 保持语义一致）。
        """
        config: DataSourceConfig = context.get("config")
        schema = context.get("schema")

        if not config or not isinstance(config, DataSourceConfig):
            # 没有有效配置时，保持兼容行为：尝试使用 DataSourceHandlerHelper 的默认 normalize
            if not fetched_data:
                return {"data": []}
            # 回退：直接使用 normalization_helper 的简单实现
            return nh.normalize_fetched_data(context, fetched_data)

        apis_conf = config.get_apis()

        if not fetched_data:
            # 原始数据为空或类型不对，直接返回空结果
            return {"data": []}

        # 步骤 2：做一次字段覆盖校验（提醒式，不中断执行；ignore_fields 不参与）
        ignore_fields = config.get_ignore_fields() if config else []
        nh.validate_field_coverage(apis_conf, schema, ignore_fields=ignore_fields)

        # 步骤 3 & 4：从所有 API 返回中提取并映射出标准字段记录
        # 检查是否配置了 merge_by_key（用于按 key 合并多个 API 的结果）
        merge_by_key = config.get_merge_by_key() if config else None

        mapped_records: List[Dict[str, Any]] = nh.extract_mapped_records(
            apis_conf=apis_conf,
            fetched_data=fetched_data,
            merge_by_key=merge_by_key,
        )

        if not mapped_records:
            # 所有 API 都没有产生有效记录
            return {"data": []}

        # 步骤 4.4：自动日期标准化（如果配置了 date_format）
        # 根据 config.date_format 自动标准化 date 字段
        date_format = config.get_date_format() if config else None

        # 使用 DateUtils 的 period 规范化逻辑，将各种配置值统一为
        # "day" / "month" / "quarter"，再交给 normalize_date_field 处理。
        try:
            from core.utils.date.date_utils import DateUtils

            target_format = DateUtils.normalize_period_type(date_format or DateUtils.PERIOD_DAY)
        except Exception:
            # 极端情况下（例如循环依赖），回退为按天标准化，保持兼容
            target_format = "day"

        if target_format and target_format != "none":
            # 日期标准化逻辑委托给 normalization_helper.normalize_date_field
            mapped_records = nh.normalize_date_field(
                mapped_records,
                field="date",
                target_format=target_format,
            )

        # 注意：调用方（BaseHandler）仍负责 on_after_mapping / on_after_normalize 等 hook，
        # 这里仅负责公共部分。

        # 步骤 5 & 6：使用 schema 约束字段集和类型（只保留 schema 定义的字段，并做类型转换/默认值填充）
        normalized_records = nh.apply_schema(mapped_records, schema)

        # 步骤 7：将最终记录包装为 {"data": [...]} 返回
        return nh.build_normalized_payload(normalized_records)

