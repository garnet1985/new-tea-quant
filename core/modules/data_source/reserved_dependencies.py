"""
保留依赖：不通过 data source handler 执行，由框架在注入依赖时直接解析。

- 依赖分为两类：保留关键字（本模块定义）与其他 data source（由 scheduler 从 _dependency_cache 取）。
- mapping 中的 data source key 不能使用保留关键字（在 HandlerMapping 中校验）。
"""
from typing import Any, List

from loguru import logger

# 保留依赖关键字：用于 depends_on，不能作为 data source key 使用
RESERVED_DEPENDENCY_KEYS = frozenset({"latest_trading_date"})


def resolve_reserved_dependency(dep_key: str) -> Any:
    """
    解析保留依赖的值。仅支持 RESERVED_DEPENDENCY_KEYS 中的 key。

    返回形状与「由 handler 返回并缓存」的依赖一致，便于下游复用。
    例如 latest_trading_date 返回 [{"date": "YYYYMMDD"}]。

    Args:
        dep_key: 保留依赖关键字（如 "latest_trading_date"）

    Returns:
        依赖值（如 [{"date": "20250130"}]）

    Raises:
        ValueError: 若 dep_key 不是保留关键字
    """
    if dep_key not in RESERVED_DEPENDENCY_KEYS:
        raise ValueError(f"未知的保留依赖: {dep_key}，保留关键字: {sorted(RESERVED_DEPENDENCY_KEYS)}")

    if dep_key == "latest_trading_date":
        return _resolve_latest_trading_date()

    raise ValueError(f"未实现保留依赖解析: {dep_key}")


def _resolve_latest_trading_date() -> List[dict]:
    """
    通过 CalendarService 解析最新已完成交易日（先缓存、再 fallback、再写回 sys_cache）。
    返回 [{"date": "YYYYMMDD"}]，与原 latest_trading_date handler 的 data 形状一致。
    """
    from core.modules.data_manager.data_manager import DataManager

    data_manager = DataManager.get_instance()
    if not data_manager or not getattr(data_manager, "service", None):
        logger.warning("DataManager 或 service 不可用，保留依赖 latest_trading_date 无法解析")
        from core.utils.date.date_utils import DateUtils
        fallback = DateUtils.get_current_date_str()
        return [{"date": fallback}]
    calendar = getattr(data_manager.service, "calendar", None)
    if not calendar or not hasattr(calendar, "get_latest_completed_trading_date"):
        logger.warning("CalendarService 不可用，保留依赖 latest_trading_date 使用当前日期兜底")
        from core.utils.date.date_utils import DateUtils
        fallback = DateUtils.get_current_date_str()
        return [{"date": fallback}]
    date_str = calendar.get_latest_completed_trading_date()
    return [{"date": date_str}]
