"""滚动对照的终端展示。只列差值和重叠，不下结论。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, TextIO, Union

from core.infra.cmd_layout import CmdLayout

from core.modules.strategy.core.engines.rolling.report import metric_specs


class RollingPresenter:
    """按层打印窗口相对主 version 的差值。"""

    def __init__(self, report: Mapping[str, Any]) -> None:
        self._report = dict(report)

    @classmethod
    def load(cls, report: Union[Mapping[str, Any], str, Path]) -> "RollingPresenter":
        """从返回体、报告文件或 ``rolling/`` 目录载入。"""
        if isinstance(report, Mapping):
            return cls(report)
        path = Path(report)
        if path.is_dir():
            path = path / "report.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"滚动报告格式无效: {path}")
        return cls(payload)

    def present(self, stream: Optional[TextIO] = None) -> None:
        """把对照表打到终端。"""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        baseline = report.get("baseline") if isinstance(report.get("baseline"), dict) else {}
        parent = str(report.get("parent_version_id") or baseline.get("version_id") or "-")
        CmdLayout.title.print_h1(f"{icon('chart')} 滚动对照", stream=out)
        meta = CmdLayout.text.meta(
            [
                f"主 version {parent}",
                f"基准 {baseline.get('start') or '-'}-{baseline.get('end') or '-'}",
                f"{int(report.get('window_count') or len(report.get('windows') or []))} 段窗口",
            ]
        )
        print(f"{icon('gear')} {meta}", file=out, flush=True)
        windows = [
            item
            for item in report.get("windows") or []
            if isinstance(item, dict)
        ]
        baseline_row = _baseline_row(report)
        if baseline_row is None and not windows:
            CmdLayout.text.print_indent("没有可展示的窗口。", stream=out)
            return
        rows = ([baseline_row] if baseline_row else []) + windows
        self._print_span(rows, out)
        for layer, title in (("enum", "枚举"), ("price", "价格"), ("portfolio", "资金")):
            self._print_layer(title, layer, rows, out)
        path = report.get("report_path")
        if path:
            CmdLayout.text.print_indent(f"报告: {path}", stream=out)

    def _print_span(self, windows: List[Dict[str, Any]], out: TextIO) -> None:
        headers = ["窗口", "版本", "长度（天）", "与基准重叠（天）"]
        rows = []
        for item in windows:
            rows.append(
                [
                    str(item.get("label") or "-"),
                    str(item.get("version_id") or "-"),
                    _days(item.get("length_days")),
                    "—" if item.get("is_baseline") else _days(item.get("overlap_days")),
                ]
            )
        CmdLayout.table.print(headers, rows, stream=out)

    def _print_layer(
        self,
        title: str,
        layer: str,
        windows: List[Dict[str, Any]],
        out: TextIO,
    ) -> None:
        specs = [item for item in metric_specs() if item[0] == layer]
        if not specs:
            return
        CmdLayout.text.print_indent(title, stream=out)
        headers = ["窗口", *[spec[2] for spec in specs]]
        rows: List[List[str]] = []
        for item in windows:
            layers = item.get("layers") if isinstance(item.get("layers"), dict) else {}
            block = layers.get(layer) if isinstance(layers.get(layer), dict) else {}
            row = [str(item.get("label") or "-")]
            for _layer, key, _label, style, include_delta in specs:
                cell = block.get(key) if isinstance(block.get(key), dict) else {}
                row.append(
                    _format_cell(
                        cell,
                        style,
                        include_delta=include_delta and not item.get("is_baseline"),
                    )
                )
            rows.append(row)
        CmdLayout.table.print(headers, rows, stream=out)
        if layer == "enum":
            for item in windows:
                conclusion = str(item.get("dispersion_conclusion") or "").strip()
                if not conclusion:
                    continue
                CmdLayout.text.print_indent(
                    f"{item.get('label')} 时间分散原文：{conclusion}",
                    stream=out,
                )


def _baseline_row(report: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """基准回测作为表的第一行。"""
    baseline = report.get("baseline") if isinstance(report.get("baseline"), dict) else {}
    if not isinstance(baseline.get("layers"), dict) or not baseline.get("layers"):
        return None
    row = dict(baseline)
    row["is_baseline"] = True
    start = str(baseline.get("start") or "")
    end = str(baseline.get("end") or "")
    row["label"] = str(baseline.get("label") or (f"{start}-{end}" if start and end else "基准"))
    return row


def _days(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "-"


def _format_cell(cell: Mapping[str, Any], style: str, *, include_delta: bool) -> str:
    value = _format_number(cell.get("value"), style)
    if not include_delta:
        return value
    delta = _format_number(cell.get("delta"), style, signed=True)
    return f"{value} ({delta})"


def _format_number(value: Any, style: str, *, signed: bool = False) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    sign = "+" if signed and number > 0 else ""
    if style == "count":
        shown = str(int(round(number)))
        return f"{sign}{shown}" if signed else shown
    if style == "ratio":
        return f"{sign}{number * 100:.1f}%"
    if style == "percent":
        return f"{sign}{number:.1f}%"
    return f"{sign}{number:.2f}"
