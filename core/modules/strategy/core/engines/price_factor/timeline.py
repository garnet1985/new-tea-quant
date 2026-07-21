"""价格回测 simulation window：枚举 runtime period（已 resolve 的 start/end）。"""
from __future__ import annotations

from typing import Tuple

from core.modules.strategy.core.engines.price_factor.enum_data import EnumVersionData


def resolve_simulation_window(data: EnumVersionData) -> Tuple[str, str]:
    """从枚举 ``0_runtime_env.json`` period 取出已 resolve 的 start/end。

    不在此建开市日轴；BE ``run(start=, end=)`` 按 window 调 CalendarService。
    """
    start = data.start_date
    end = data.end_date
    if not start or not end:
        raise ValueError(
            f"枚举 version 缺少 period.start_date/end_date: {data.output_dir}"
        )
    return start, end


__all__ = ["resolve_simulation_window"]
