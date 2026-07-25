"""价格回测 simulation window（来自 enum runtime period）。

本文件:
- resolve_simulation_window: 取出已 resolve 的 start/end 传给 BE
  边界: 只提 period；不建开市日轴、不复写 Timeline.points
  说明: 真业务现为 after_task 事件回放；勿在此加 TimelineBuilder「为少空转」—
        等 ``on_tick`` 成为回放主路径再议 event 轴（见 BOUNDARY_NOTES）
"""
from __future__ import annotations

from typing import Tuple

from core.modules.strategy.core.engines.shared.services.simulation_output.enum_source import EnumSource


def resolve_simulation_window(data: EnumSource) -> Tuple[str, str]:
    """从枚举 ``runtime_env.json`` period 取出已 resolve 的 start/end。

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
