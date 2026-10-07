"""战役报告的终端展示：参数扫描、联合扫描和问题章节。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, TextIO, Union

from core.infra.cmd_layout import CmdLayout

from ..attribute import AttributeStep
from ..labels import CampaignLabels

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

_FAMILY_TITLES = {
    "oaat": "修改参数后的对照",
    "cross": "多参数交叉对照",
}


class CampaignPresenter:
    """结论先行的战役 CMD 视图。"""

    def __init__(self, report: Mapping[str, Any]) -> None:
        self._report = dict(report)

    @classmethod
    def load(cls, report: Union[Mapping[str, Any], str, Path]) -> "CampaignPresenter":
        """从字典或已落盘目录载入展示器。"""
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
                },
            )
            _hydrate_families(payload)
        return cls(payload)

    def present(self, stream: Optional[TextIO] = None) -> None:
        """把战役报告打到终端。"""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        persist = report.get("persist") if isinstance(report.get("persist"), dict) else {}
        families = _family_blocks(report)
        layer = _report_layer(report)
        nested = len(families) >= 2
        tables = _all_table_rows(report)
        cells = report.get("cells") if isinstance(report.get("cells"), list) else []
        vids = _unique_version_ids([*tables, *cells])
        vid_count = len(vids)
        vid_text = "、".join(f"v{item}" for item in vids) if vids else "还没有回测号"
        strategy_key = _strategy_key(report)

        CmdLayout.title.print_h1(
            f"{icon('chart')} {CampaignLabels.report_title(layer)}",
            stream=out,
        )
        CmdLayout.text.print_kv("策略key", strategy_key or "-", sep="：", stream=out)
        CmdLayout.text.print_kv(
            f"共产生 {vid_count} 套对照组",
            vid_text,
            sep="：",
            stream=out,
        )
        group_id = report.get("group_id") or persist.get("group_id")
        if group_id:
            CmdLayout.text.print_kv("归因组 ID", group_id, sep="：", stream=out)
        cost_warning = str(
            report.get("cost_warning") or persist.get("cost_warning") or ""
        ).strip()
        if cost_warning:
            CmdLayout.text.print_kv("成本提示", cost_warning, sep="：", stream=out)
        bridge = str(
            report.get("upstream_bridge")
            or (
                (report.get("report") or {}).get("upstream_bridge")
                if isinstance(report.get("report"), dict)
                else ""
            )
            or ""
        ).strip()
        if bridge:
            CmdLayout.text.print_indent(bridge, stream=out)

        self._present_conclusion(out, families)
        self._present_parameter_sweeps(out)
        self._present_joint_sweeps(out)
        self._present_question_sections(out)

        if nested:
            for name in ("oaat", "cross"):
                block = _family_named(families, name)
                if not isinstance(block, dict):
                    continue
                title = _FAMILY_TITLES.get(name, name)
                CmdLayout.title.print_h2(f"{icon('rocket')} {title}", stream=out)
                if name == "oaat":
                    CmdLayout.text.print_indent(
                        "每次只改一个路径，比较相对基准的结果差异。",
                        stream=out,
                    )
                else:
                    # TODO: 全轴 cross 能展开，但报告仍按单因素讲，产品还没完成。
                    CmdLayout.text.print_indent(
                        "多个参数取不同组合，比较组合变化带来的结果差异。",
                        stream=out,
                    )
                view = CampaignPresenter(_family_present_payload(report, block))
                view._present_family_body(out, nested=True)
        else:
            self._present_family_body(out, nested=False)

        self._present_paths(out, persist)

    def _present_parameter_sweeps(self, out: TextIO) -> None:
        """敏感度排名 + 每轴扫描档位（参数扫描主产物）。"""
        report = self._report
        nested = report.get("report") if isinstance(report.get("report"), dict) else {}
        rank = report.get("sensitivity_rank")
        sweeps = report.get("sweeps")
        if not isinstance(rank, list) or not rank:
            rank = nested.get("sensitivity_rank") if isinstance(nested, dict) else None
        if not isinstance(sweeps, list) or not sweeps:
            sweeps = nested.get("sweeps") if isinstance(nested, dict) else None
        if not isinstance(rank, list):
            rank = []
        if not isinstance(sweeps, list):
            sweeps = []
        if not rank and not sweeps:
            return
        icon = CmdLayout.icon.get
        CmdLayout.title.print_h2(f"{icon('chart')} 参数扫描", stream=out)
        primary = str(
            report.get("sweep_primary_outcome")
            or (nested.get("sweep_primary_outcome") if isinstance(nested, dict) else "")
            or ""
        ).strip()
        if primary:
            CmdLayout.text.print_indent(
                f"主指标：{CampaignLabels.outcome_label(primary)}（样本内；换窗口请用滚动验证）",
                stream=out,
            )
        if rank:
            CmdLayout.title.print_h3("敏感度排名", stream=out)
            bullets = []
            for item in rank:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("knob_label") or item.get("knob") or "").strip()
                span = str(item.get("span_label") or item.get("span") or "").strip()
                impact = str(item.get("impact") or "").strip()
                best = str(item.get("best_value_label") or item.get("best_value") or "").strip()
                bits = [f"#{item.get('rank')}", label]
                if span:
                    bits.append(f"起伏 {span}")
                if impact:
                    bits.append(f"影响{impact}")
                if best:
                    bits.append(f"样本内较优 {best}")
                bullets.append(" · ".join(str(b) for b in bits if b))
            if bullets:
                CmdLayout.text.print_bullets(bullets, indent=3, marker="·", stream=out)
        for sweep in sweeps:
            if not isinstance(sweep, dict):
                continue
            levels = [
                item for item in (sweep.get("levels") or []) if isinstance(item, dict)
            ]
            if len(levels) < 2:
                continue
            knob_label = str(sweep.get("knob_label") or sweep.get("knob") or "").strip()
            outcome = str(
                sweep.get("primary_outcome_label")
                or sweep.get("primary_outcome")
                or primary
                or "指标"
            ).strip()
            CmdLayout.title.print_h3(f"{knob_label} → {outcome}", stream=out)
            advice = str(sweep.get("advice") or "").strip()
            if advice:
                CmdLayout.text.print_indent(advice, stream=out)
            rows = []
            for level in levels:
                metrics = level.get("metrics") if isinstance(level.get("metrics"), dict) else {}
                key = str(sweep.get("primary_outcome") or primary or "")
                metric = metrics.get(key)
                mark = "（当前）" if level.get("is_baseline") else ""
                rows.append(
                    [
                        f"{level.get('value_label')}{mark}",
                        CampaignLabels.format_number(key, metric)
                        if metric is not None
                        else "—",
                    ]
                )
            if rows:
                CmdLayout.table.print(
                    ["取值", outcome],
                    rows,
                    stream=out,
                )

    def _present_joint_sweeps(self, out: TextIO) -> None:
        """联合扫描热力表。"""
        report = self._report
        nested = report.get("report") if isinstance(report.get("report"), dict) else {}
        joints = report.get("joint_sweeps")
        if not isinstance(joints, list) or not joints:
            joints = nested.get("joint_sweeps") if isinstance(nested, dict) else None
        if not isinstance(joints, list) or not joints:
            return
        icon = CmdLayout.icon.get
        CmdLayout.title.print_h2(f"{icon('rocket')} 联合扫描", stream=out)
        for block in joints:
            if not isinstance(block, dict):
                continue
            labels = block.get("knob_labels") or block.get("knobs") or []
            title = " × ".join(str(item) for item in labels if item)
            outcome = str(
                block.get("primary_outcome_label")
                or block.get("primary_outcome")
                or "指标"
            )
            CmdLayout.title.print_h3(
                f"{title} → {outcome}" if title else outcome,
                stream=out,
            )
            advice = str(block.get("advice") or "").strip()
            if advice:
                CmdLayout.text.print_indent(advice, stream=out)
            grid = block.get("grid") if isinstance(block.get("grid"), dict) else None
            if not grid:
                continue
            col_labels = [str(item) for item in (grid.get("col_labels") or [])]
            headers = [
                str(grid.get("row_knob_label") or "行"),
                *[str(item) for item in col_labels],
            ]
            body = []
            row_labels = [str(item) for item in (grid.get("row_labels") or [])]
            label_matrix = grid.get("label_matrix") or []
            for i, row_label in enumerate(row_labels):
                cells = label_matrix[i] if i < len(label_matrix) else []
                body.append(
                    [row_label, *[str(item) for item in cells[: len(col_labels)]]]
                )
            if body:
                CmdLayout.table.print(headers, body, stream=out)

    def _present_question_sections(self, out: TextIO) -> None:
        """按问题分节报告（枚举 / 价格等 summarize 写出的 sections）。"""
        report = self._report
        sections = report.get("sections")
        scope_note = str(report.get("scope_note") or "").strip()
        if not isinstance(sections, dict) or not sections:
            nested = report.get("report") if isinstance(report.get("report"), dict) else {}
            sections = nested.get("sections") if isinstance(nested, dict) else None
            if not scope_note and isinstance(nested, dict):
                scope_note = str(nested.get("scope_note") or "").strip()
        if not isinstance(sections, dict) or not sections:
            return
        icon = CmdLayout.icon.get
        CmdLayout.title.print_h2(f"{icon('search')} 层内诊断", stream=out)
        if scope_note:
            CmdLayout.text.print_indent(scope_note, stream=out)
        order = (
            "opportunity",
            "stock_distribution",
            "dispersion",
            "exit_quality",
            "after_take_profit",
            "edge",
            "profit_concentration",
            "exit_profit",
        )
        for key in order:
            block = sections.get(key)
            if not isinstance(block, dict):
                continue
            if key == "after_take_profit" and not block.get("available"):
                continue
            question = str(block.get("question") or key).strip()
            CmdLayout.title.print_h3(question, stream=out)
            effects = [
                item
                for item in (block.get("effects") or [])
                if isinstance(item, dict)
            ]
            if effects:
                bullets: List[str] = []
                for effect in effects:
                    label = CampaignLabels.knob_label(effect.get("knob"))
                    bits = [
                        str(effect.get(name) or "").strip()
                        for name in ("max_line", "min_line", "trend_line")
                        if str(effect.get(name) or "").strip()
                    ]
                    if bits:
                        bullets.append(f"{label} — {'；'.join(bits)}")
                if bullets:
                    CmdLayout.text.print_indent("结论：", stream=out)
                    CmdLayout.text.print_bullets(
                        bullets, indent=3, marker="·", stream=out
                    )
                CmdLayout.text.print_indent("具体细节：", stream=out)
                for effect in effects:
                    table = [
                        row
                        for row in (effect.get("table") or [])
                        if isinstance(row, dict)
                    ]
                    if not table:
                        continue
                    title = str(effect.get("title") or "").strip()
                    if title:
                        CmdLayout.text.print_indent(title, stream=out)
                    knob = CampaignLabels.knob_label(effect.get("knob"))
                    outcome = CampaignLabels.outcome_label(effect.get("outcome"))
                    headers = [
                        f"当{knob}为",
                        outcome,
                        "与当前策略配置的变化",
                    ]
                    body = [
                        [
                            str(row.get("value_label") or "—"),
                            str(row.get("metric_label") or "—"),
                            str(row.get("delta_label") or "—"),
                        ]
                        for row in table
                    ]
                    CmdLayout.table.print(headers, body, stream=out)
            else:
                facts = [
                    str(item).strip()
                    for item in (block.get("facts") or [])
                    if str(item).strip()
                ]
                if facts:
                    CmdLayout.text.print_indent("结论：", stream=out)
                    CmdLayout.text.print_bullets(
                        facts, indent=3, marker="·", stream=out
                    )
                else:
                    conclusion = str(block.get("conclusion") or "").strip()
                    if conclusion:
                        CmdLayout.text.print_indent(f"结论：{conclusion}", stream=out)
            # 枚举层不写建议

    def _present_conclusion(
        self,
        out: TextIO,
        families: Mapping[str, Mapping[str, Any]],
    ) -> None:
        icon = CmdLayout.icon.get
        CmdLayout.title.print_h2(f"{icon('target')} 结论摘要", stream=out)
        CmdLayout.text.print_indent(
            "归因结果快速总结：",
            stream=out,
        )
        lines: List[str] = []
        if families:
            for name in ("oaat", "cross"):
                block = _family_named(families, name)
                if not isinstance(block, dict):
                    continue
                text = str(block.get("headline") or "").strip()
                if not text:
                    nested = block.get("report")
                    if isinstance(nested, dict):
                        text = str(nested.get("headline") or "").strip()
                if text:
                    lines.append(f"{_FAMILY_TITLES.get(name, name)}：{text}")
        else:
            text = str(self._report.get("headline") or "").strip()
            if not text:
                nested = self._report.get("report")
                if isinstance(nested, dict):
                    text = str(nested.get("headline") or "").strip()
            if text:
                lines.append(text)
        if lines:
            CmdLayout.text.print_bullets(lines, indent=3, marker="·", stream=out)
        else:
            CmdLayout.text.print_indent("这次还没有可写的结论。", stream=out)

    def _present_family_body(self, out: TextIO, *, nested: bool = False) -> None:
        self._present_table(out, _table_rows(self._report), nested=nested)
        self._present_skipped(out, nested=nested)
        self._present_hints(out, nested=nested)

    def _heading(self, title: str, out: TextIO, *, nested: bool) -> None:
        if nested:
            CmdLayout.title.print_h3(title, stream=out)
        else:
            CmdLayout.title.print_h2(title, stream=out)

    def _present_table(
        self,
        out: TextIO,
        table: Sequence[Any],
        *,
        nested: bool = False,
    ) -> None:
        rows = [row for row in table if isinstance(row, dict)]
        if not rows:
            return
        icon = CmdLayout.icon.get
        self._heading(f"{icon('clipboard')} 数字对照", out, nested=nested)

        knob_keys = _knob_columns(rows, layer=_report_layer(self._report))
        outcome_keys = _outcome_columns(rows, layer=_report_layer(self._report))
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
        CmdLayout.table.print(headers, body, stream=out)

    def _present_skipped(self, out: TextIO, *, nested: bool = False) -> None:
        cells = self._report.get("cells") or []
        skipped = [
            cell
            for cell in cells
            if isinstance(cell, dict) and str(cell.get("execute_status") or "") == "skipped"
        ]
        if not skipped:
            return
        icon = CmdLayout.icon.get
        self._heading(f"{icon('warning')} 没对照上的", out, nested=nested)
        CmdLayout.text.print_bullets(
            [
                f"第 {int(cell.get('index', 0)) + 1} 套："
                f"{_SKIP_REASONS.get(str(cell.get('execute_reason') or ''), str(cell.get('execute_reason') or '').strip() or '跳过')}"
                for cell in skipped
            ],
            indent=3,
            marker="·",
            stream=out,
        )

    def _present_hints(self, out: TextIO, *, nested: bool = False) -> None:
        summarized = self._report.get("report")
        hints = []
        if isinstance(summarized, dict):
            hints = summarized.get("hints") or []
        if not isinstance(hints, list) or not hints:
            return
        icon = CmdLayout.icon.get
        self._heading(f"{icon('blue_dot')} 解读", out, nested=nested)
        for hint in hints[:4]:
            text = str(hint or "").strip()
            if text:
                CmdLayout.text.print_indent(text, stream=out)

    def _present_paths(self, out: TextIO, persist: Mapping[str, Any]) -> None:
        icon = CmdLayout.icon.get
        path = persist.get("report_path") or self._report.get("report_path")
        group_id = persist.get("group_id") or self._report.get("group_id")
        if not path and not group_id:
            return
        CmdLayout.title.print_h2(f"{icon('gear')} 产物", stream=out)
        if group_id:
            CmdLayout.text.print_indent(f"组 {group_id}", stream=out)
        if path:
            CmdLayout.text.print_indent(path, stream=out)


_KNOWN_LAYERS = frozenset({"enumerate", "price_factor", "portfolio"})


def _report_layer(report: Mapping[str, Any]) -> str:
    for key in ("layer", "kind", "simulate_kind"):
        text = str(report.get(key) or "").strip()
        if text in _KNOWN_LAYERS:
            return text
    nested = report.get("report")
    if isinstance(nested, dict):
        for key in ("layer", "kind"):
            text = str(nested.get(key) or "").strip()
            if text in _KNOWN_LAYERS:
                return text
    return ""


def _strategy_key(report: Mapping[str, Any]) -> str:
    key = str(report.get("strategy_key") or "").strip()
    if key:
        return key
    folder = str(report.get("folder") or "").strip()
    if folder:
        return Path(folder).name
    return ""


def _unique_version_ids(rows: Sequence[Any]) -> List[str]:
    seen = set()
    out: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("version_id") or "").strip()
        if not vid or vid in seen:
            continue
        seen.add(vid)
        out.append(vid)
    return out

def _family_named(families: Mapping[str, Any], name: str) -> Any:
    """按家族名取块。"""
    return families.get(name)


def _hydrate_families(payload: Dict[str, Any]) -> None:
    if isinstance(payload.get("families"), dict) and payload.get("families"):
        return
    families: Dict[str, Any] = {}
    table = payload.get("table")
    attribute = payload.get("attribute")
    for name in ("oaat", "cross"):
        block = payload.get(name)
        if not isinstance(block, dict) or not (
            block.get("report")
            or block.get("headline")
            or block.get("table")
        ):
            continue
        fam = dict(block)
        source = name
        if isinstance(table, dict):
            fam.setdefault("table", table.get(source) or [])
        if isinstance(attribute, dict) and isinstance(attribute.get(source), dict):
            fam.setdefault("attribute", attribute.get(source) or {})
        families[name] = fam
    if families:
        payload["families"] = families


def _family_blocks(report: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    block = report.get("families")
    if isinstance(block, dict) and block:
        return {
            str(name): dict(item)
            for name, item in block.items()
            if isinstance(item, dict)
        }
    return {}


def _table_rows(report: Mapping[str, Any]) -> List[Any]:
    table = report.get("table")
    if isinstance(table, list):
        return table
    return []


def _all_table_rows(report: Mapping[str, Any]) -> List[Any]:
    table = report.get("table")
    if isinstance(table, list):
        return table
    rows: List[Any] = []
    if isinstance(table, dict):
        for group in table.values():
            if isinstance(group, list):
                rows.extend(group)
    for block in _family_blocks(report).values():
        nested = block.get("table")
        if isinstance(nested, list):
            rows.extend(nested)
    return rows


def _family_present_payload(
    root: Mapping[str, Any],
    family: Mapping[str, Any],
) -> Dict[str, Any]:
    nested_report = family.get("report")
    if not isinstance(nested_report, dict):
        nested_report = {
            "headline": family.get("headline"),
            "highlights": family.get("highlights") or [],
            "hints": family.get("hints") or [],
        }
    out = dict(root)
    out["headline"] = family.get("headline") or nested_report.get("headline")
    out["report"] = nested_report
    out["attribute"] = family.get("attribute") or {}
    out["table"] = family.get("table") or []
    out["gather"] = family.get("gather") or {}
    out["cells"] = family.get("cells") or []
    return out


def _knob_columns(rows: Sequence[Mapping[str, Any]], *, layer: str = "") -> List[str]:
    attributer = AttributeStep.for_layer(layer) if layer else None
    keys: List[str] = []
    seen = set()
    for row in rows:
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        for key, value in knobs.items():
            text = str(key)
            if text in seen or not CampaignLabels.is_display_knob(text, value):
                continue
            if attributer is not None and not attributer.accepts_knob(text):
                continue
            seen.add(text)
            keys.append(text)
    return keys


def _outcome_columns(
    rows: Sequence[Mapping[str, Any]],
    *,
    layer: str = "",
) -> List[tuple]:
    available = set()
    for row in rows:
        layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
        for layer_name, block in layers.items():
            if not isinstance(block, dict):
                continue
            for key, value in block.items():
                if value is None:
                    continue
                available.add((str(layer_name), str(key)))
    preferred = list(AttributeStep.for_layer(layer).OUTCOMES)
    out = [pair for pair in preferred if pair in available]
    if out:
        return out
    if layer:
        focused = sorted(item for item in available if item[0] == layer)
        if focused:
            return focused[:3]
    out = [pair for pair in preferred if pair in available]
    if out:
        return out
    return sorted(available)[:3]



def _read_json_object(path: Path) -> Dict[str, Any]:
    raw = _read_json_any(path)
    return raw if isinstance(raw, dict) else {}


def _read_json_any(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None
