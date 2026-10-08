"""读取已落盘的归因战役报告。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.project_context import ProjectContext
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import WorkbenchStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.persist.base import (
    ATTRIBUTE_FILE,
    REPORT_FILE,
    TABLE_FILE,
    TASK_META_FILE,
)

_TASK_BY_STEP = {
    "enum": "enum",
    "price": "price",
    "portfolio": "portfolio",
}


class AttributeReportReader:
    """按策略、层和组号组装报告响应。"""

    @classmethod
    def build(
        cls,
        *,
        strategy_name: str,
        normalized_step: str,
        group_id: str,
    ) -> Dict[str, Any]:
        """读取一组战役的报告、表和元数据。"""
        gid = str(group_id or "").strip()
        if not gid.isdigit():
            raise ValueError("group_id 无效")
        step = str(normalized_step or "").strip()
        task = _TASK_BY_STEP.get(step)
        if task is None:
            raise ValueError("step 须为 enum / price / portfolio")
        folder = Strategy.resolve_folder(strategy_name)
        root = ProjectContext.path.get_strategy_attribution_directory(folder)
        task_dir = Path(root) / gid / task
        report_path = task_dir / REPORT_FILE
        if not report_path.is_file():
            raise FileNotFoundError(f"归因报告不存在: {report_path}")

        report = _read_json(report_path) or {}
        table = _read_json(task_dir / TABLE_FILE)
        if table is None:
            table = []
        attribute = _read_json(task_dir / ATTRIBUTE_FILE) or {}
        task_meta = _read_json(task_dir / TASK_META_FILE) or {}
        trades = report.get("trades") if isinstance(report.get("trades"), dict) else {}
        layer = WorkbenchStep.parse(step).to_simulate_kind().value
        nested = report.get("report") if isinstance(report.get("report"), dict) else {}
        sections = report.get("sections")
        if not isinstance(sections, dict) or not sections:
            sections = nested.get("sections") if isinstance(nested, dict) else {}
        scope_note = str(
            report.get("scope_note")
            or (nested.get("scope_note") if isinstance(nested, dict) else "")
            or ""
        ).strip()
        analysis_mode = str(
            report.get("analysis_mode")
            or (nested.get("analysis_mode") if isinstance(nested, dict) else "")
            or report.get("mode")
            or ""
        ).strip()
        return {
            "strategy_name": strategy_name,
            "step": step,
            "group_id": gid,
            "layer": layer,
            "mode": report.get("mode"),
            "analysis_mode": analysis_mode,
            "headline": report.get("headline"),
            "scope_note": scope_note,
            "sections": sections if isinstance(sections, dict) else {},
            "report": report,
            "table": table,
            "attribute": attribute,
            "trades": trades,
            "task_meta": task_meta,
            "task_dir": str(task_dir.resolve()),
            "report_path": str(report_path.resolve()),
        }


def _read_json(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None


__all__ = ["AttributeReportReader"]
