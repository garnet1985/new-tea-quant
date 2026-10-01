"""战役报告的终端展示：先看贡献度，再看对照表。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, TextIO, Union

from core.infra.cmd_layout import CmdLayout

from .labels import CampaignLabels

_SECTION_WIDTH = 64

_SKIP_REASONS = {
    "fill_missing_false": "没有现成回测，这次也没补跑",
    "version_not_found": "找不到这个回测号",
    "sample_mismatch": "区间或股票池和当前设置不同",
    "strategy_not_enabled": "策略未启用",
}

_STATUS_LABELS = {
    "hit": "复用",
    "simulated": "新跑",
    "skipped": "跳过",
}

_PREFERRED_OUTCOMES = (
    ("portfolio", "total_return"),
    ("portfolio", "max_drawdown"),
    ("enumerate", "total_opportunities"),
    ("price_factor", "win_rate"),
    ("price_factor", "avg_roi"),
)
_CONTRIB_SHOW = (
    ("portfolio", "total_return"),
    ("portfolio", "max_drawdown"),
    ("enumerate", "total_opportunities"),
)


class CampaignPresenter:
    """结论先行的战役 CMD 视图。"""

    def __init__(self, report: Mapping[str, Any]) -> None:
        self._report = dict(report)

    @classmethod
    def load(cls, report: Union[Mapping[str, Any], str, Path]) -> "CampaignPresenter":
        if isinstance(report, Mapping):
            return cls(report)
        path = Path(report)
        report_path = path / "report.json" if path.is_dir() else path
        if not report_path.is_file():
            raise FileNotFoundError(f"战役报告不存在: {report_path}")
        payload = _read_json_object(report_path)
        if path.is_dir():
            meta_path = path / "task_meta.json"
            if meta_path.is_file():
                meta = _read_json_object(meta_path)
                payload.setdefault("cells", meta.get("cells") or [])
                payload.setdefault("execute", meta.get("execute") or {})
                payload.setdefault("gather", meta.get("gather") or {})
            table_path = path / "table.json"
            if table_path.is_file():
                payload.setdefault("table", _read_json_any(table_path) or [])
            payload.setdefault("report_path", str(report_path.resolve()))
            attr_path = path / "attribute.json"
            if attr_path.is_file():
                payload.setdefault("attribute", _read_json_any(attr_path) or {})
            payload.setdefault(
                "report",
                {
                    "headline": payload.get("headline"),
                    "highlights": payload.get("highlights") or [],
                    "hints": payload.get("hints") or [],
                    "varying_knobs": payload.get("varying_knobs") or [],
                    "contributions": payload.get("contributions")
                    or (payload.get("attribute") or {}).get("contributions")
                    or {},
                },
            )
        return cls(payload)

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        persist = report.get("persist") if isinstance(report.get("persist"), dict) else {}
        gather = report.get("gather") if isinstance(report.get("gather"), dict) else {}
        table = report.get("table") if isinstance(report.get("table"), list) else []
        ready = int(gather.get("ready_count") or 0)
        group_id = report.get("group_id") or persist.get("group_id")
        vids = [
            str(row.get("version_id"))
            for row in table
            if isinstance(row, dict) and row.get("version_id")
        ]
        vid_text = "、".join(f"v{item}" for item in vids) if vids else "还没有回测号"

        CmdLayout.title.print_banner(f"{icon('chart')} 归因对照", stream=out)
        group_bit = f"组 {group_id}  ·  " if group_id else ""
        print(
            f"{icon('gear')} {group_bit}{report.get('cell_count') or 0} 套设置  ·  "
            f"对照上 {ready} 套  ·  {vid_text}",
            file=out,
            flush=True,
        )

        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('target')} 一句话", stream=out)
        print(f"   {report.get('headline') or '-'}", file=out, flush=True)

        self._present_presence(out)
        self._present_sensitivity(out)
        self._present_cross_layer(out)
        self._present_interaction(out)
        self._present_table(out, table)
        self._present_highlights(out)
        self._present_skipped(out)
        self._present_hints(out)
        self._present_paths(out, persist)
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)

    def _present_table(self, out: TextIO, table: Sequence[Any]) -> None:
        rows = [row for row in table if isinstance(row, dict)]
        if not rows:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('clipboard')} 数字对照", stream=out)

        knob_keys = _knob_columns(rows)
        outcome_keys = _outcome_columns(rows)
        headers = ["回测"] + [CampaignLabels.knob_label(key) for key in knob_keys]
        headers += [CampaignLabels.outcome_label(key) for _, key in outcome_keys]

        body: List[List[str]] = []
        for row in rows:
            vid = str(row.get("version_id") or "").strip()
            status = str(row.get("status") or "")
            label = f"v{vid}" if vid else _STATUS_LABELS.get(status, status or "-")
            line = [label]
            knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
            for key in knob_keys:
                line.append(CampaignLabels.format_knob(key, knobs.get(key)))
            layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
            for layer, key in outcome_keys:
                block = layers.get(layer) if isinstance(layers.get(layer), dict) else {}
                line.append(CampaignLabels.format_number(key, block.get(key) if isinstance(block, dict) else None))
            body.append(line)
        _print_table(headers, body, out)

    def _present_presence(self, out: TextIO) -> None:
        contrib = _chapter_block(self._report, "presence")
        items = [
            item
            for item in (contrib.get("items") or [])
            if isinstance(item, dict) and item.get("kind") == "one_at_a_time"
        ]
        if not items:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('rocket')} 参数贡献度", stream=out)
        print("   有 / 无。基准是关掉这一项的那一格。", file=out, flush=True)
        self._present_item_groups(out, items)

    def _present_sensitivity(self, out: TextIO) -> None:
        contrib = _chapter_block(self._report, "sensitivity")
        marginals = [
            block
            for block in (contrib.get("marginals") or [])
            if isinstance(block, dict) and (block.get("levels") or [])
        ]
        if marginals:
            icon = CmdLayout.icon.get
            CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
            CmdLayout.title.print_section(f"{icon('rocket')} 参数敏感度", stream=out)
            baseline = (
                contrib.get("baseline") if isinstance(contrib.get("baseline"), dict) else {}
            )
            vid = str(baseline.get("version_id") or "").strip()
            print(
                f"   取值变化。相对基准 {('v' + vid) if vid else '开着的第一套'}，按旋钮取值从小到大",
                file=out,
                flush=True,
            )
            for block in marginals:
                self._present_marginal_knob(out, block)
            return
        items = [
            item
            for item in (contrib.get("items") or [])
            if isinstance(item, dict) and item.get("kind") == "one_at_a_time"
        ]
        if not items:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('rocket')} 参数敏感度", stream=out)
        baseline = (
            contrib.get("baseline") if isinstance(contrib.get("baseline"), dict) else {}
        )
        vid = str(baseline.get("version_id") or "").strip()
        print(
            f"   取值变化。相对基准 {('v' + vid) if vid else '开着的第一套'}",
            file=out,
            flush=True,
        )
        self._present_item_groups(out, items)

    def _present_item_groups(
        self,
        out: TextIO,
        items: Sequence[Mapping[str, Any]],
    ) -> None:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        order: List[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            knob = str(item.get("knob") or "")
            if knob not in grouped:
                grouped[knob] = []
                order.append(knob)
            grouped[knob].append(item)
        for knob in order:
            print(f"   {CampaignLabels.knob_label(knob)}", file=out, flush=True)
            for item in grouped[knob]:
                bits = [
                    f"{CampaignLabels.format_knob(knob, item.get('from'))} → "
                    f"{CampaignLabels.format_knob(knob, item.get('to'))}"
                ]
                for layer, outcome in _CONTRIB_SHOW:
                    delta = _item_delta(item, layer, outcome)
                    if delta is None:
                        continue
                    bits.append(
                        f"{CampaignLabels.outcome_label(outcome)} {CampaignLabels.format_delta(outcome, delta)}"
                    )
                print(f"      {'   '.join(bits)}", file=out, flush=True)

    def _present_marginal_knob(self, out: TextIO, block: Mapping[str, Any]) -> None:
        knob = str(block.get("knob") or "")
        print(f"   {CampaignLabels.knob_label(knob)}", file=out, flush=True)
        for level in block.get("levels") or []:
            if not isinstance(level, dict):
                continue
            bits = [CampaignLabels.format_number(knob, level.get("value"))]
            for layer, outcome in _CONTRIB_SHOW:
                value = _outcome_value(level.get("outcomes") or [], layer, outcome)
                if value is None:
                    continue
                bits.append(f"{CampaignLabels.outcome_label(outcome)} {CampaignLabels.format_number(outcome, value)}")
            step = _step_label(level)
            if step:
                bits.append(step)
            print(f"      {'   '.join(bits)}", file=out, flush=True)
        if str(block.get("note") or "") == "pullback":
            best = CampaignLabels.format_number(knob, block.get("best_value"))
            print(
                f"      放到 {best} 最好，再往上调账户收益回落。",
                file=out,
                flush=True,
            )

    def _present_cross_layer(self, out: TextIO) -> None:
        contrib = _chapter_block(self._report, "sensitivity")
        rows = [
            item
            for item in (contrib.get("cross_layer") or [])
            if isinstance(item, dict)
        ]
        if not rows:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('target')} 跨层", stream=out)
        for item in rows:
            print(
                f"   · {CampaignLabels.knob_label(item.get('knob'))}："
                f"{CampaignLabels.cross_layer_phrase(item.get('verdict'))}",
                file=out,
                flush=True,
            )

    def _present_interaction(self, out: TextIO) -> None:
        contrib = _chapter_block(self._report, "sensitivity")
        block = contrib.get("interactions")
        if not isinstance(block, dict) or str(block.get("status") or "") != "ok":
            return
        grids = [grid for grid in (block.get("grids") or []) if isinstance(grid, dict)]
        if not grids:
            return
        grid = grids[0]
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('clipboard')} 交叉", stream=out)
        row_knob = str(grid.get("row_knob") or "")
        col_knob = str(grid.get("col_knob") or "")
        print(
            f"   {CampaignLabels.knob_label(row_knob)} × {CampaignLabels.knob_label(col_knob)}（账户收益）",
            file=out,
            flush=True,
        )
        col_values = list(grid.get("col_values") or [])
        headers = [""] + [CampaignLabels.format_number(col_knob, value) for value in col_values]
        best = grid.get("best") if isinstance(grid.get("best"), dict) else {}
        body: List[List[str]] = []
        for line in grid.get("cells") or []:
            if not isinstance(line, list) or not line:
                continue
            first = line[0] if isinstance(line[0], dict) else {}
            row = [CampaignLabels.format_number(row_knob, first.get("row_value"))]
            for cell in line:
                if not isinstance(cell, dict):
                    row.append("-")
                    continue
                text = CampaignLabels.format_number("total_return", cell.get("total_return"))
                if _same_number(cell.get("row_value"), best.get("row_value")) and _same_number(
                    cell.get("col_value"), best.get("col_value")
                ):
                    text = f"{text} ←最好"
                row.append(text)
            body.append(row)
        _print_table(headers, body, out)

    def _present_highlights(self, out: TextIO) -> None:
        presence = _chapter_block(self._report, "presence")
        sensitivity = _chapter_block(self._report, "sensitivity")
        if presence.get("one_at_a_time_count") or sensitivity.get("one_at_a_time_count"):
            return
        summarized = self._report.get("report")
        highlights = []
        if isinstance(summarized, dict):
            highlights = summarized.get("highlights") or []
        if not isinstance(highlights, list) or not highlights:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('rocket')} 方向", stream=out)
        seen = set()
        for item in highlights:
            if not isinstance(item, dict):
                continue
            key = (item.get("layer"), item.get("outcome"), item.get("knob"))
            if key in seen:
                continue
            seen.add(key)
            print(
                f"   · {_highlight_line(item)}",
                file=out,
                flush=True,
            )
            if len(seen) >= 3:
                break

    def _present_skipped(self, out: TextIO) -> None:
        cells = self._report.get("cells") or []
        skipped = [
            cell
            for cell in cells
            if isinstance(cell, dict) and str(cell.get("execute_status") or "") == "skipped"
        ]
        if not skipped:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('warning')} 没对照上的", stream=out)
        for cell in skipped:
            reason = _SKIP_REASONS.get(
                str(cell.get("execute_reason") or ""),
                str(cell.get("execute_reason") or "").strip() or "跳过",
            )
            print(
                f"   · 第 {int(cell.get('index', 0)) + 1} 套：{reason}",
                file=out,
                flush=True,
            )

    def _present_hints(self, out: TextIO) -> None:
        summarized = self._report.get("report")
        hints = []
        if isinstance(summarized, dict):
            hints = summarized.get("hints") or []
        if not isinstance(hints, list) or not hints:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('blue_dot')} 怎么读", stream=out)
        for hint in hints[:4]:
            text = str(hint or "").strip()
            if text:
                print(f"   {text}", file=out, flush=True)

    def _present_paths(self, out: TextIO, persist: Mapping[str, Any]) -> None:
        icon = CmdLayout.icon.get
        path = persist.get("report_path") or self._report.get("report_path")
        group_id = persist.get("group_id") or self._report.get("group_id")
        if not path and not group_id:
            return
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('gear')} 产物", stream=out)
        if group_id:
            print(f"   组 {group_id}", file=out, flush=True)
        if path:
            print(f"   {path}", file=out, flush=True)


def _knob_columns(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    keys: List[str] = []
    seen = set()
    for row in rows:
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        for key, value in knobs.items():
            text = str(key)
            if text in seen or not CampaignLabels.is_display_knob(text, value):
                continue
            seen.add(text)
            keys.append(text)
    return keys


def _outcome_columns(rows: Sequence[Mapping[str, Any]]) -> List[tuple]:
    available = set()
    for row in rows:
        layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
        for layer, block in layers.items():
            if not isinstance(block, dict):
                continue
            for key, value in block.items():
                if value is None:
                    continue
                available.add((str(layer), str(key)))
    out = [pair for pair in _PREFERRED_OUTCOMES if pair in available]
    if out:
        return out
    return sorted(available)[:3]


def _chapter_block(report: Mapping[str, Any], name: str) -> Dict[str, Any]:
    block = _contributions_block(report)
    nested = block.get(name)
    if isinstance(nested, dict):
        return nested
    if name == "sensitivity" and (
        block.get("items") or block.get("marginals") or block.get("one_at_a_time_count")
    ):
        return block
    return {}


def _contributions_block(report: Mapping[str, Any]) -> Dict[str, Any]:
    nested = report.get("report")
    if isinstance(nested, dict) and isinstance(nested.get("contributions"), dict):
        block = nested.get("contributions") or {}
        if block:
            return block
    top = report.get("contributions")
    if isinstance(top, dict) and top:
        return top
    attribute = report.get("attribute")
    if isinstance(attribute, dict) and isinstance(attribute.get("contributions"), dict):
        return attribute.get("contributions") or {}
    return {}


def _item_delta(
    item: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    for part in item.get("deltas") or []:
        if not isinstance(part, dict):
            continue
        if str(part.get("layer") or "") != layer:
            continue
        if str(part.get("outcome") or "") != outcome:
            continue
        return CampaignLabels.maybe_float(part.get("delta"))
    return None


def _outcome_value(parts: Sequence[Any], layer: str, outcome: str) -> Optional[float]:
    for part in parts:
        if not isinstance(part, dict):
            continue
        if str(part.get("layer") or "") != layer:
            continue
        if str(part.get("outcome") or "") != outcome:
            continue
        return CampaignLabels.maybe_float(part.get("value"))
    return None


def _step_label(level: Mapping[str, Any]) -> str:
    if level.get("is_baseline"):
        return "基准"
    prev = _item_delta({"deltas": level.get("vs_prev") or []}, "portfolio", "total_return")
    if prev is not None:
        return f"相对上一档 {CampaignLabels.format_delta('total_return', prev)}"
    base = _item_delta(
        {"deltas": level.get("vs_baseline") or []}, "portfolio", "total_return"
    )
    if base is not None:
        return f"相对基准 {CampaignLabels.format_delta('total_return', base)}"
    return ""


def _same_number(left: Any, right: Any) -> bool:
    a = CampaignLabels.maybe_float(left)
    b = CampaignLabels.maybe_float(right)
    if a is None or b is None:
        return False
    return abs(a - b) < 1e-12


def _highlight_line(item: Mapping[str, Any]) -> str:
    knob = str(item.get("knob") or "")
    outcome = str(item.get("outcome") or "")
    rho = CampaignLabels.maybe_float(item.get("rho")) or 0.0
    result = CampaignLabels.outcome_label(outcome)
    if "stop_loss" in knob:
        phrase = CampaignLabels.direction_phrase(outcome, -rho)
        return f"止损越深，{result}{phrase}"
    phrase = CampaignLabels.direction_phrase(outcome, rho)
    return f"{CampaignLabels.knob_label(knob)}越大，{result}{phrase}"


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[str]], out: TextIO) -> None:
    if not headers:
        return
    widths = [len(str(header)) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    def fmt(row: Sequence[str]) -> str:
        parts = []
        for i, cell in enumerate(row):
            width = widths[i] if i < len(widths) else len(str(cell))
            parts.append(str(cell).rjust(width) if i else str(cell).ljust(width))
        return "   " + "  ".join(parts)

    print(fmt(headers), file=out, flush=True)
    print("   " + "  ".join("-" * width for width in widths), file=out, flush=True)
    for row in rows:
        print(fmt(row), file=out, flush=True)


def _read_json_object(path: Path) -> Dict[str, Any]:
    raw = _read_json_any(path)
    return raw if isinstance(raw, dict) else {}


def _read_json_any(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None
