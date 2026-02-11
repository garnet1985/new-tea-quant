"""
date_range_helper

负责基于 renew 配置计算：
- 所有实体的原始 last_update 映射（不考虑 renew_mode）；
- 单个实体在不同 renew_mode 下的起始日期；
- 各实体本次应抓取的 (start_date, end_date)；
- renew_if_over_days 门控逻辑；
- 通用的日期值标准化工具。

实现从 `DataSourceHandlerHelper` 中拆分而来，供 `DateRangeService`、
handler 以及测试等直接调用。`DataSourceHandlerHelper` 中同名方法
目前作为薄壳代理，后续可以逐步移除。
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

from core.global_enums.enums import TermType, UpdateMode
from core.infra.project_context import ConfigManager
from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper
from core.utils.date.date_utils import DateUtils


logger = logging.getLogger(__name__)


def normalize_date_value(date_value: Any) -> Optional[str]:
    """
    标准化日期值（处理 datetime 对象或其他格式），统一输出 YYYYMMDD 字符串。
    """
    from datetime import datetime as dt

    try:
        if isinstance(date_value, dt):
            return DateUtils.datetime_to_format(date_value)
        if isinstance(date_value, str):
            s = str(date_value).strip()
            normalized = DateUtils.normalize_str(s)
            if normalized:
                return normalized
            # 处理 DB 返回的 datetime 字符串（如 "2026-02-08 20:39:24"）
            return DateUtils.str_to_format(s, DateUtils.FMT_YYYYMMDD, DateUtils.FMT_DATETIME)
        # 兜底：粗暴去掉分隔符、截取前 8 位
        return str(date_value).replace("-", "").replace(" ", "").replace(":", "")[:8]
    except Exception as e:  # pragma: no cover - 防御性日志
        logger.debug(f"标准化日期格式失败: {date_value}, error: {e}")
        return None


def compute_last_update_map(context: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    计算所有实体的“原始”最近更新时间（latest_date）映射（不考虑 renew_mode）。

    - per-entity 场景：一次性查询整张表，返回 {entity_id: latest_date_str}；
    - 非 per-entity 场景：查询整表最新一条记录，返回 {"_global": latest_date_str}；
    - 如果表为空或查询失败，对应值为 None 或空 dict。
    """
    data_manager = context.get("data_manager")
    config = context.get("config")

    if not data_manager or not config:
        return {}

    table_name = config.get_table_name()
    date_field = config.get_date_field()
    date_format = config.get_date_format()

    if not table_name or not date_field:
        # refresh 模式不需要 last_update，静默返回空映射；其他模式才告警
        if config.get_renew_mode() != UpdateMode.REFRESH:
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
            last_update_map["_global"] = normalize_date_value(raw_value) if raw_value else None
            return last_update_map
        except Exception as e:  # pragma: no cover - 防御性日志
            logger.warning(f"查询全局 last_update 失败: {e}")
            # 查询失败时，保守返回空映射（后续逻辑会当作“无 last_update”处理）
            return {}

    # per-entity：一次性查询所有实体的最新日期（实体标识字段用 config.job_execution.key 或 keys）
    latest_dates_dict = RenewCommonHelper.query_latest_date(
        data_manager=data_manager,
        table_name=table_name,
        date_field=date_field,
        date_format=date_format,
        needs_stock_grouping=needs_stock_grouping,
        context=context,
    )

    if not latest_dates_dict:
        # 表为空或查询失败：所有实体视为没有 last_update
        logger.warning(
            f"⚠️ [compute_last_update_map] 查询 {table_name} 的最新日期返回空结果，可能表为空或查询失败"
        )
        return {}

    # latest_dates_dict: {entity_id: latest_date_raw} 或 {composite_key: latest_date_raw}
    # 检查是否是多字段分组（通过检查 key 是否包含分隔符 "::"）
    group_fields = config.get_group_fields() if config else []
    is_multi_field = len(group_fields) > 1
    _ = is_multi_field  # 目前逻辑相同，仅保留注释语义

    for key, raw_value in latest_dates_dict.items():
        if not raw_value:
            last_update_map[str(key)] = None
        else:
            normalized_date = normalize_date_value(raw_value)
            last_update_map[str(key)] = normalized_date

    return last_update_map


def calc_last_update_based_on_renew_mode(
    context: Dict[str, Any],
    entity_id: Optional[str] = None,  # 保留签名以兼容旧接口（当前未使用）
    last_update: Optional[str] = None,
) -> Optional[str]:
    """
    根据 renew_mode 对“原始” last_update 做一次性转换，得到本次抓取的起点日期（start_date）。

    说明：
    - 该方法只负责“last_update → start_date”的纯函数逻辑，不参与是否触发本次更新的判断；
    - 是否需要触发由上层通过 renew_if_over_days 或其他规则统一决定；
    - 返回值为标准化后的字符串日期，格式由 config.date_format 决定。
    """
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
    except Exception:  # pragma: no cover - 防御性兜底
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
            period_type = DateUtils.normalize_period_type(date_format)
            start_period = DateUtils.add_periods(last_update, 1, period_type)
            return DateUtils.from_period_str(start_period, period_type, is_start=True)
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
                period_type = DateUtils.normalize_period_type(date_format)
                start_period = DateUtils.add_periods(last_update, 1, period_type)
                return DateUtils.from_period_str(start_period, period_type, is_start=True)
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
                if _date_format == TermType.MONTHLY.value:
                    return rolling_length * 3
                return rolling_length * 90  # daily
            if _rolling_unit == TermType.MONTHLY.value:
                if _date_format == TermType.QUARTERLY.value:
                    return (rolling_length + 2) // 3
                if _date_format == TermType.MONTHLY.value:
                    return rolling_length
                return rolling_length * 30  # daily
            # DAILY
            if _date_format == TermType.QUARTERLY.value:
                return (rolling_length + 90) // 90
            if _date_format == TermType.MONTHLY.value:
                return (rolling_length + 30) // 30
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

        period_type = DateUtils.normalize_period_type(date_format)

        if latest_completed_trading_date:
            end_period = DateUtils.to_period_str(latest_completed_trading_date, period_type)
        else:
            current_date = DateUtils.today()
            end_period = DateUtils.to_period_str(current_date, period_type)

        rolling_start_period = DateUtils.sub_periods(end_period, rolling_periods, period_type)
        rolling_start_date = DateUtils.from_period_str(
            rolling_start_period, period_type, is_start=True
        )

        if not last_update:
            # 表为空或新实体：退化为默认起点
            return default_start_date

        try:
            period_diff = DateUtils.diff_periods(last_update, end_period, period_type)
        except Exception:
            return default_start_date

        if period_diff <= rolling_periods:
            # 在 rolling 窗口内：直接从 rolling_start 开始
            return rolling_start_date

        # 落后太多：从 last_update 的后一个周期开始追
        try:
            start_period = DateUtils.add_periods(last_update, 1, period_type)
            return DateUtils.from_period_str(start_period, period_type, is_start=True)
        except Exception:
            return default_start_date

    # 未知 / 未配置模式：退化为简单增量
    if not last_update:
        return default_start_date
    try:
        period_type = DateUtils.normalize_period_type(date_format)
        start_period = DateUtils.add_periods(last_update, 1, period_type)
        return DateUtils.from_period_str(start_period, period_type, is_start=True)
    except Exception:
        return default_start_date


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
                latest_completed_trading_date = DateUtils.today()
        except Exception:
            latest_completed_trading_date = DateUtils.today()

    # 4.1 当 counting_field 与 date_field 不同时，单独查询 renew 门控用的时间（如 last_update）
    # last_update_map 用 date_field（如 event_date）用于增量起点；renew_if_over_days 应用 counting_field（如 last_update）
    # REFRESH 模式：last_update_map 可能为空（框架未为其查 DB），此时必须单独查 gate 才能让 renew_if_over_days 生效
    renew_gate_map: Optional[Dict[str, Optional[str]]] = None
    needs_stock_grouping = RenewCommonHelper.get_needs_stock_grouping(context)
    date_field = config.get_date_field()
    if threshold_cfg:
        counting_field = threshold_cfg.get("counting_field")
        table_name = config.get_table_name()
        gate_field = counting_field if counting_field else date_field
        # 需要单独查 gate：counting_field != date_field，或 last_update_map 为空（REFRESH 等场景）
        need_gate_query = (counting_field and counting_field != date_field) or (
            not last_update_map and table_name and needs_stock_grouping is not False
        )
        if need_gate_query and table_name and needs_stock_grouping is not False:
            raw_map = RenewCommonHelper.query_latest_date(
                data_manager,
                table_name,
                gate_field,
                date_format,
                needs_stock_grouping,
                context=context,
            )
            if raw_map:
                renew_gate_map = {}
                for k, v in raw_map.items():
                    renew_gate_map[k] = normalize_date_value(v) if v else None
                if not last_update_map:
                    logger.info(
                        f"📋 [renew_if_over_days] last_update_map 为空，已单独查询 gate_field={gate_field}，"
                        f"得到 {len(renew_gate_map)} 条用于过滤"
                    )
                    # 注入 context 供 handler 使用（如 on_after_single_api_job_bundle_complete 中的 last_check）
                    context["_last_update_map"] = renew_gate_map

    def should_trigger(last_update: Optional[str], composite_key: Optional[str] = None) -> bool:
        """
        根据 renew_if_over_days 判断是否需要触发本次更新（更新频率检查）。

        这是第一层检查：判断距离上次更新是否已经过去了足够长的时间。
        如果时间间隔不够，直接返回 False，不进行后续的完整周期检查。
        """
        if not threshold_cfg:
            return True

        threshold_days = threshold_cfg.get("value")
        if not threshold_days:
            # 未配置 value，当作始终需要更新
            return True

        if not last_update:
            # 没有 last_update（新实体或表为空）→ 需要更新
            return True

        # 第一层检查：更新频率（renew_if_over_days）
        # 计算距离上次更新的天数差
        try:
            days_diff = DateUtils.diff_days(last_update, latest_completed_trading_date)
        except Exception:
            # 日期解析失败，保守策略：更新
            return True

        # days_diff >= threshold → 时间间隔足够，可以更新；否则跳过
        return days_diff >= threshold_days

    # 5. 根据需要分组与否，分别计算
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
                period_type = DateUtils.normalize_period_type(date_format)
                start_period = DateUtils.add_periods(last_update, 1, period_type)
                return DateUtils.from_period_str(start_period, period_type, is_start=True)
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
            _rolling_unit = (
                rolling_unit.value if isinstance(rolling_unit, TermType) else rolling_unit
            )
            _date_format = date_format

            # 将 rolling_unit 转为与 date_format 对齐的周期数
            def _convert_rolling_length_to_periods() -> int:
                if _rolling_unit == TermType.QUARTERLY.value:
                    if _date_format == TermType.QUARTERLY.value:
                        return rolling_length
                    if _date_format == TermType.MONTHLY.value:
                        return rolling_length * 3
                    return rolling_length * 90
                if _date_format == TermType.MONTHLY.value:
                    if _date_format == TermType.QUARTERLY.value:
                        return (rolling_length + 2) // 3
                    if _date_format == TermType.MONTHLY.value:
                        return rolling_length
                    return rolling_length * 30
                # DAILY
                if _date_format == TermType.QUARTERLY.value:
                    return (rolling_length + 90) // 90
                if _date_format == TermType.MONTHLY.value:
                    return (rolling_length + 30) // 30
                return rolling_length

            rolling_periods = _convert_rolling_length_to_periods()

            # 计算 end_period / rolling_start
            period_type = DateUtils.normalize_period_type(date_format)

            if latest_completed_trading_date:
                end_period = DateUtils.to_period_str(latest_completed_trading_date, period_type)
            else:
                current_date = DateUtils.today()
                end_period = DateUtils.to_period_str(current_date, period_type)

            rolling_start_period = DateUtils.sub_periods(end_period, rolling_periods, period_type)
            rolling_start_date = DateUtils.from_period_str(
                rolling_start_period, period_type, is_start=True
            )

            if not last_update:
                # 没有 last_update：退化为从默认起点
                return default_start_date

            try:
                period_diff = DateUtils.diff_periods(last_update, end_period, period_type)
            except Exception:
                # 日期解析失败，保守策略：从默认起点
                return default_start_date

            if period_diff <= rolling_periods:
                # 在 rolling 窗口内：从 rolling_start 起
                return rolling_start_date

            # 落后太多：从 last_update 的后一个周期开始追
            try:
                start_period = DateUtils.add_periods(last_update, 1, period_type)
                return DateUtils.from_period_str(start_period, period_type, is_start=True)
            except Exception:
                return default_start_date

        # 未知或未配置的模式：退化为增量模式逻辑
        if not last_update:
            return default_start_date
        try:
            period_type = DateUtils.normalize_period_type(date_format)
            start_period = DateUtils.add_periods(last_update, 1, period_type)
            return DateUtils.from_period_str(start_period, period_type, is_start=True)
        except Exception:
            return default_start_date

        # 理论不会走到这里

    # 非 per-entity：只算一条 "_global"
    if not needs_stock_grouping:
        gate_val = (renew_gate_map.get("_global") if renew_gate_map else None) or last_update_map.get(
            "_global"
        )
        if not should_trigger(gate_val):
            return {}
        start_date = compute_start_for_mode(last_update_map.get("_global"))
        result["_global"] = (start_date, end_date)
        return result

    # per-entity：从 dependencies 中获取实体列表（标准位置）
    # 实体列表名称由 config.job_execution.list 决定（如 stock_list、index_list）
    entity_list_name = config.get_group_by_entity_list_name() if config else "stock_list"
    dependencies = context.get("dependencies", {})
    entity_list = dependencies.get(entity_list_name)

    if not entity_list:
        logger.warning(
            f"needs_stock_grouping=True 但 dependencies['{entity_list_name}'] 为空，返回空日期范围。"
            f"请在 handler 的 on_prepare_context 中注入 {entity_list_name}。"
        )
        return {}

    # 检查是否是多字段分组（通过检查 last_update_map 的 key 是否包含分隔符 "::"）
    group_fields = config.get_group_fields() if config else []
    is_multi_field = len(group_fields) > 1

    if is_multi_field:
        # 多字段分组：需要从 stock_list 遍历，为每个股票的每个 term 创建日期范围
        # 这样可以处理新股票（不在 last_update_map 中）的情况
        # 例如：{"000001.SZ::daily": "20240101", "000001.SZ::weekly": "20240107"}

        # 获取 terms：从 last_update_map 提取已有 term；不足时从 job_execution.terms 补充（不允许运行时推断）
        terms_set = set()
        for key in last_update_map.keys():
            if "::" in key:
                parts = key.split("::")
                if len(parts) >= 2:
                    terms_set.add(parts[1].lower())

        config_terms = config.get_group_by_terms() if config else None
        if not terms_set and config_terms:
            terms_set = {str(t).lower() for t in config_terms if t}
        if not terms_set:
            from core.modules.data_source.data_class.error import DataSourceConfigError

            raise DataSourceConfigError(
                "多字段分组时 terms 必须从 job_execution.terms 显式配置，不允许运行时推断"
            )

        # 提取 entity_key_field 用于从 stock_info 中获取 entity_id
        entity_key_field = group_fields[0] if group_fields else "id"

        # 遍历 entity_list，为每个实体的每个 term 创建日期范围
        for stock_info in entity_list:
            # 提取实体 ID
            if isinstance(stock_info, dict):
                entity_id = str(stock_info.get(entity_key_field))
            else:
                entity_id = str(stock_info)

            if not entity_id:
                continue

            for term in terms_set:
                composite_key = f"{entity_id}::{term}"
                last_update = last_update_map.get(composite_key)

                # 第一层检查：更新频率（renew_if_over_days，使用 counting_field 如 last_update）
                gate_val = (
                    renew_gate_map.get(composite_key) if renew_gate_map else None
                ) or last_update
                if not should_trigger(gate_val, composite_key=composite_key):
                    continue

                start_date = compute_start_for_mode(last_update)
                result[composite_key] = (start_date, end_date)
        return result

    # 单字段分组：以 entity_id 为 key
    for stock_info in entity_list:
        if isinstance(stock_info, dict):
            entity_id = str(stock_info.get(group_fields[0] if group_fields else "id"))
        else:
            entity_id = str(stock_info)

        if not entity_id:
            continue

        last_update = last_update_map.get(entity_id)
        gate_val = (renew_gate_map.get(entity_id) if renew_gate_map else None) or last_update
        if not should_trigger(gate_val, composite_key=entity_id):
            continue

        start_date = compute_start_for_mode(last_update)
        result[entity_id] = (start_date, end_date)

    return result


def check_renew_if_over_days(
    context: Dict[str, Any],
    threshold_config: Dict[str, Any],
    stock_list: Optional[List[Dict[str, Any]]] = None,
) -> Optional[List[str]]:
    """
    检查 renew_if_over_days，返回需要更新的 entity 列表（candidates）。

    流程：
    1. 判断是全局数据还是 per entity
    2. 从数据库一次性查询所有需要对比的数据（per entity 就是每个 entity 一条，不是就是 1 条）
    3. 对比：没有时间记录或超过 threshold 的进入 candidates
    4. 返回 candidates list

    Returns:
        - None: 不过滤（全局数据且需要更新，或表为空）
        - []: 过滤掉所有 ApiJobs（全局数据且不需要更新）
        - List[str]: 需要更新的 entity ID 列表（candidates，per entity 模式）
    """
    from core.modules.data_source.data_class.error import DataSourceConfigError

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
        except Exception as e:  # pragma: no cover - 防御性日志
            logger.warning(f"获取最新完成交易日失败: {e}")
            latest_completed_trading_date = DateUtils.today()

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
            latest_date_str = normalize_date_value(latest_date)
            if not latest_date_str:
                return None

            # ========== 步骤3：对比 - 计算天数差 ==========
            days_diff = DateUtils.diff_days(latest_date_str, latest_completed_trading_date)

            if days_diff >= threshold_days:
                # 超过 threshold，返回 None（不过滤，需要更新）
                return None
            # 没过 threshold，返回空列表（过滤掉所有 ApiJobs）
            return []
        except Exception as e:  # pragma: no cover - 防御性日志
            logger.warning(f"查询全局数据最新日期失败: {e}")
            return None

    # Per entity：一次性查询所有 entity 的最新记录（实体标识字段用 config.job_execution.key 或 keys）
    date_format = config.get_date_format()
    latest_dates_dict = RenewCommonHelper.query_latest_date(
        data_manager, table_name, counting_field, date_format, needs_stock_grouping, context=context
    )

    if not latest_dates_dict:
        # 表为空，返回 None（不过滤）
        return None

    # ========== 步骤3：对比 - 遍历所有 entity，找出 candidates ==========
    candidates: List[str] = []

    for entity_id, latest_date in latest_dates_dict.items():
        if not latest_date:
            # 没有时间记录，进入 candidates
            candidates.append(entity_id)
            continue

        # 标准化日期格式
        latest_date_str = normalize_date_value(latest_date)
        if not latest_date_str:
            # 日期格式错误，保守策略：进入 candidates
            candidates.append(entity_id)
            continue

        # 计算天数差（renew_if_over_days 检查：更新频率）
        try:
            days_diff = DateUtils.diff_days(latest_date_str, latest_completed_trading_date)

            if days_diff >= threshold_days:
                # 超过 threshold，进入 candidates
                candidates.append(entity_id)
        except Exception as e:  # pragma: no cover - 防御性日志
            logger.warning(f"计算 entity {entity_id} 的天数差失败: {e}")
            # 计算失败，保守策略：进入 candidates
            candidates.append(entity_id)

    # 如果提供了 stock_list，只返回在 stock_list 中的 entity（按 config.group_fields 提取）
    if stock_list:
        group_fields = config.get_group_fields()
        if not group_fields:
            raise DataSourceConfigError("stock_list 过滤需要 job_execution.key 或 keys 配置")
        stock_ids = set()
        for stock in stock_list:
            if isinstance(stock, dict):
                parts = [str(stock.get(f, "")) for f in group_fields]
                eid = "::".join(parts) if len(parts) > 1 else (parts[0] if parts else "")
            else:
                eid = str(stock)
            if eid:
                stock_ids.add(eid)
        candidates = [eid for eid in candidates if eid in stock_ids]

    return candidates if candidates else None

