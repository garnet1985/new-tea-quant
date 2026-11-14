"""
保留依赖：不通过 data source handler 执行，由框架在注入依赖时直接解析。

- 依赖分为两类：保留关键字（本模块定义）与其他 data source（由 scheduler 从 _dependency_cache 取）。
- mapping 中的 data source key 不能使用保留关键字（在 HandlerMapping 中校验）。
"""
from typing import Any, List
import logging

# 保留依赖关键字：用于 depends_on，不能作为 data source key 使用
RESERVED_DEPENDENCY_KEYS = frozenset({"latest_completed_trading_date"})


logger = logging.getLogger(__name__)


def resolve_reserved_dependency(dep_key: str) -> Any:
    """
    解析保留依赖的值。仅支持 RESERVED_DEPENDENCY_KEYS 中的 key。

    返回形状与「由 handler 返回并缓存」的依赖一致，便于下游复用。
    例如 latest_completed_trading_date 返回 [{"date": "YYYYMMDD"}]。

    Args:
        dep_key: 保留依赖关键字（如 "latest_completed_trading_date"）

    Returns:
        依赖值（如 [{"date": "20250130"}]）

    Raises:
        ValueError: 若 dep_key 不是保留关键字
    """
    if dep_key not in RESERVED_DEPENDENCY_KEYS:
        raise ValueError(f"未知的保留依赖: {dep_key}，保留关键字: {sorted(RESERVED_DEPENDENCY_KEYS)}")

    if dep_key == "latest_completed_trading_date":
        return _resolve_latest_completed_trading_date()

    raise ValueError(f"未实现保留依赖解析: {dep_key}")


def _resolve_latest_completed_trading_date() -> List[dict]:
    """
    Renew 注入的截止日：交易日历推导（不读 assumed_latest）。
    返回 [{"date": "YYYYMMDD"}]。
    """
    from core.modules.data_manager import DataManager
    from core.modules.data_source.core.service.renew_progress import resolve_uptodate_day

    data_manager = DataManager.get_instance()
    date_str = ""
    try:
        date_str = str(resolve_uptodate_day(data_manager) or "").strip()
    except Exception as exc:
        logger.warning("保留依赖 latest_completed_trading_date 解析失败: %s", exc)
    if not date_str:
        logger.warning(
            "保留依赖 latest_completed_trading_date 为空，使用当前日期兜底"
        )
        from core.infra.utils import Utils

        date_str = Utils.date.today()
    return [{"date": date_str}]