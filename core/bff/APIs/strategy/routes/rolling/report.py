"""读取当前主 version 的滚动对照报告。"""

from __future__ import annotations

import json
from typing import Any, Dict

from core.modules.strategy.core.engines.rolling.readiness import report_path_for


class RollingReportReader:
    """从主 version 的 ``rolling/report.json`` 读报告。"""

    @classmethod
    def build(cls, *, strategy_name: str) -> Dict[str, Any]:
        """返回已落盘的滚动报告。"""
        path = report_path_for(strategy_name)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FileNotFoundError(f"滚动报告无法读取: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"滚动报告格式无效: {path}")
        payload["report_path"] = str(path)
        return payload


__all__ = ["RollingReportReader"]
