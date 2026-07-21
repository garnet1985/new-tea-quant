"""价格回测时间轴：枚举 period 的 start–end 开市日（连续日历轴，允许空转）。"""
from __future__ import annotations

from typing import Any, Dict

from core.modules.backtest_engine.contracts import Timeline
from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
    RuntimeSnapshot,
)
from core.modules.strategy.core.engines.enumerator.shared.services.enumerator_timeline import (
    EnumeratorTimeline,
)
from core.modules.strategy.core.engines.enumerator.slice_based.resolver.calendar import (
    BacktestCalendarResolver,
)
from core.modules.strategy.core.engines.price_factor.enum_data import EnumVersionData


def resolve_price_timeline(
    data: EnumVersionData,
    *,
    data_manager: Any = None,
) -> Timeline:
    """用已加载的 runtime period 解析全局日历 Timeline。

    - period: ``0_runtime_env.json``（与枚举 run 一致）
    - points: 区间内全部开市日（不按产物事件抽稀）
    """
    start = data.start_date
    end = data.end_date
    if not start or not end:
        raise ValueError(
            f"枚举 version 缺少 period.start_date/end_date: {data.output_dir}"
        )

    settings = _settings_for_calendar(data.runtime)
    open_points, _calendar = BacktestCalendarResolver.resolve(
        settings=settings,
        start_date=start,
        end_date=end,
        data_manager=data_manager,
    )
    return EnumeratorTimeline.from_open_points(
        open_points,
        start=start,
        end=end,
        meta={
            "source": "trade.calendar",
            "enum_version": str(data.version_id),
        },
    )


def _settings_for_calendar(runtime: RuntimeSnapshot) -> Dict[str, Any]:
    effective = dict(runtime.settings_snapshot.effective_settings or {})
    if effective.get("market_profile"):
        return effective
    profile = str(runtime.market_profile or "").strip()
    if profile:
        effective["market_profile"] = profile
    return effective


__all__ = ["resolve_price_timeline"]
