"""
Backtest Scheduler - Slice-based Scheduler

切片模式的调度逻辑：按日期切片批量执行，强制单进程。

特点：
- 强制max_workers=1（单进程执行）
- 只创建1个job（包含所有entity）
- Reader ∥ Compute内部编排
- 不计算entities_per_job和max_workers
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def resolve_slice_settings(performance: Dict[str, Any]) -> Dict[str, Any]:
    """
    切片模式：解析调度配置。

    强制配置：
    - max_workers=1（单进程）
    - 不计算entities_per_job
    - 移除timeline模式的无用配置
    """
    settings = dict(performance)
    
    # 强制单进程
    settings["max_workers"] = 1
    settings["stage_in_worker"] = False
    
    # 移除timeline模式专用的配置
    timeline_only_keys = {
        "data_chunk_size",
        "dispatch_probe",
        "entities_per_job",
        "entities_per_job_min",
        "entities_per_job_max",
    }
    for key in timeline_only_keys:
        settings.pop(key, None)
    
    return settings


__all__ = [
    "resolve_slice_settings",
]