"""战役报告的终端展示：先看贡献度，再看对照表。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, TextIO, Union

from core.infra.cmd_layout import CmdLayout

from ..attribute import AttributeStep
from ..contrasts import KnobContrasts
from ..labels import CampaignLabels
from ..metrics import item_delta, outcome_value

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
    "inputs": "修改参数后的对照",
    "cross": "多参数交叉对照",
}


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
            _hydrate_families(payload)
        return cls(payload)

    def present(self, stream: Optional[TextIO] = None) -> None:
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
            for name in ("inputs", "cross"):
                block = families.get(name)
                if not isinstance(block, dict):
                    continue
                title = _FAMILY_TITLES.get(name, name)
                CmdLayout.title.print_h2(f"{icon('rocket')} {title}", stream=out)
                if name == "inputs":
                    CmdLayout.text.print_indent(
                        "每次只改一个路径，比较相对基准的结果差异。",
                        stream=out,
                    )
                else:
                    CmdLayout.text.print_indent(
                        "多个参数取不同组合，比较组合变化带来的结果差异。",
                        stream=out,
                    )
                view = CampaignPresenter(_family_present_payload(report, block))
                view._present_family_body(out, nested=True)
        else:
            self._present_family_body(out, nested=False)

        self._present_trades(out)
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
            for name in ("inputs", "cross"):
                block = families.get(name)
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
        table = _table_rows(self._report)
        # 枚举五节已用取值阶梯回答「什么值最好/最差」时，不再单独讲 presence 开关。
        if not _has_enum_sections(self._report):
            self._present_presence(out, nested=nested)
        self._present_sensitivity(out, nested=nested)
        self._present_cross_layer(out, nested=nested)
        self._present_interaction(out, nested=nested)
        self._present_table(out, table, nested=nested)
        self._present_highlights(out, nested=nested)
        self._present_skipped(out, nested=nested)
        self._present_hints(out, nested=nested)

    def _heading(self, title: str, out: TextIO, *, nested: bool) -> None:
        if nested:
            CmdLayout.title.print_h3(title, stream=out)
        else:
            CmdLayout.title.print_h2(title, stream=out)

    def _contrib_pairs(self) -> Sequence[tuple]:
        return AttributeStep.for_layer(_report_layer(self._report)).OUTCOMES

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

    def _present_presence(self, out: TextIO, *, nested: bool = False) -> None:
        contrib = _chapter_block(self._report, "presence")
        items = [
            item
            for item in (contrib.get("items") or [])
            if isinstance(item, dict) and item.get("kind") == "one_at_a_time"
        ]
        if not items:
            return
        icon = CmdLayout.icon.get
        self._heading(f"{icon('rocket')} 参数贡献度", out, nested=nested)
        CmdLayout.text.print_indent(
            "比较：使用 / 未使用该参数时，结果差多少。",
            stream=out,
        )
        self._present_item_groups(out, items)

    def _present_sensitivity(self, out: TextIO, *, nested: bool = False) -> None:
        contrib = _chapter_block(self._report, "sensitivity")
        marginals = [
            block
            for block in (contrib.get("marginals") or [])
            if isinstance(block, dict) and (block.get("levels") or [])
        ]
        items = [
            item
            for item in (contrib.get("items") or [])
            if isinstance(item, dict) and item.get("kind") == "one_at_a_time"
        ]
        if not marginals and not items:
            return
        icon = CmdLayout.icon.get
        self._heading(f"{icon('rocket')} 参数敏感度", out, nested=nested)
        baseline = (
            contrib.get("baseline") if isinstance(contrib.get("baseline"), dict) else {}
        )
        vid = str(baseline.get("version_id") or "").strip()
        base = f"v{vid}" if vid else "使用该参数的第一次回测"
        CmdLayout.text.print_indent(
            f"比较：同一参数取不同值时结果怎么变。对照基准 {base}。",
            stream=out,
        )
        if marginals:
            for block in marginals:
                self._present_marginal_knob(out, block)
            return
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
            CmdLayout.title.print_h4(CampaignLabels.knob_label(knob), stream=out)
            for item in grouped[knob]:
                bits = [
                    f"{CampaignLabels.format_knob(knob, item.get('from'))} → "
                    f"{CampaignLabels.format_knob(knob, item.get('to'))}"
                ]
                for layer, outcome in self._contrib_pairs():
                    delta = item_delta(item, layer, outcome)
                    if delta is None:
                        continue
                    bits.append(
                        f"{CampaignLabels.outcome_label(outcome)} {CampaignLabels.format_delta(outcome, delta)}"
                    )
                CmdLayout.text.print_indent("   ".join(bits), stream=out)

    def _present_marginal_knob(self, out: TextIO, block: Mapping[str, Any]) -> None:
        knob = str(block.get("knob") or "")
        CmdLayout.title.print_h4(CampaignLabels.knob_label(knob), stream=out)
        for level in block.get("levels") or []:
            if not isinstance(level, dict):
                continue
            bits = [CampaignLabels.format_number(knob, level.get("value"))]
            for layer, outcome in self._contrib_pairs():
                value = outcome_value(level.get("outcomes") or [], layer, outcome)
                if value is None:
                    continue
                bits.append(f"{CampaignLabels.outcome_label(outcome)} {CampaignLabels.format_number(outcome, value)}")
            step = _step_label(level)
            if step:
                bits.append(step)
            CmdLayout.text.print_indent("   ".join(bits), stream=out)
        if str(block.get("note") or "") == "pullback":
            best = CampaignLabels.format_number(knob, block.get("best_value"))
            primary = self._contrib_pairs()[0][1] if self._contrib_pairs() else "total_return"
            CmdLayout.text.print_indent(
                f"取 {best} 时最好，再增大该参数，"
                f"{CampaignLabels.outcome_label(primary)}会回落。",
                stream=out,
            )

    def _present_cross_layer(self, out: TextIO, *, nested: bool = False) -> None:
        # 跨层叙事由本层归因器决定；枚举层关闭。
        if not AttributeStep.for_layer(_report_layer(self._report)).ENABLE_CROSS_LAYER:
            return
        contrib = _chapter_block(self._report, "sensitivity")
        rows = [
            item
            for item in (contrib.get("cross_layer") or [])
            if isinstance(item, dict)
        ]
        if not rows:
            return
        icon = CmdLayout.icon.get
        self._heading(f"{icon('target')} 机会 vs 下游账户", out, nested=nested)
        CmdLayout.text.print_indent(
            "同一回测号上：机会数与下游账户收益是否同向变化。",
            stream=out,
        )
        CmdLayout.text.print_bullets(
            [
                f"{CampaignLabels.knob_label(item.get('knob'))}："
                f"{CampaignLabels.cross_layer_phrase(item.get('verdict'))}"
                for item in rows
            ],
            indent=3,
            marker="·",
            stream=out,
        )

    def _present_interaction(self, out: TextIO, *, nested: bool = False) -> None:
        if not AttributeStep.for_layer(_report_layer(self._report)).ENABLE_INTERACTIONS:
            return
        contrib = _chapter_block(self._report, "sensitivity")
        block = contrib.get("interactions")
        if not isinstance(block, dict) or str(block.get("status") or "") != "ok":
            return
        grids = [grid for grid in (block.get("grids") or []) if isinstance(grid, dict)]
        if not grids:
            return
        grid = grids[0]
        icon = CmdLayout.icon.get
        self._heading(f"{icon('clipboard')} 参数交叉对照", out, nested=nested)
        row_knob = str(grid.get("row_knob") or "")
        col_knob = str(grid.get("col_knob") or "")
        CmdLayout.text.print_indent(
            f"{CampaignLabels.knob_label(row_knob)} × {CampaignLabels.knob_label(col_knob)}（账户收益）",
            stream=out,
        )
        col_values = list(grid.get("col_values") or [])
        headers = [""] + [CampaignLabels.format_knob(col_knob, value) for value in col_values]
        best = grid.get("best") if isinstance(grid.get("best"), dict) else {}
        body: List[List[str]] = []
        for line in grid.get("cells") or []:
            if not isinstance(line, list) or not line:
                continue
            first = line[0] if isinstance(line[0], dict) else {}
            row = [CampaignLabels.format_knob(row_knob, first.get("row_value"))]
            for cell in line:
                if not isinstance(cell, dict):
                    row.append("-")
                    continue
                text = CampaignLabels.format_number("total_return", cell.get("total_return"))
                if _same_level(cell.get("row_value"), best.get("row_value")) and _same_level(
                    cell.get("col_value"), best.get("col_value")
                ):
                    text = f"{text} ←最好"
                row.append(text)
            body.append(row)
        CmdLayout.table.print(headers, body, stream=out)

    def _present_highlights(self, out: TextIO, *, nested: bool = False) -> None:
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
        self._heading(f"{icon('rocket')} 方向", out, nested=nested)
        seen = set()
        lines = []
        for item in highlights:
            if not isinstance(item, dict):
                continue
            key = (item.get("layer"), item.get("outcome"), item.get("knob"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(_highlight_line(item))
            if len(seen) >= 3:
                break
        CmdLayout.text.print_bullets(lines, indent=3, marker="·", stream=out)

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

    def _present_trades(self, out: TextIO) -> None:
        block = self._report.get("trades")
        if not isinstance(block, dict):
            nested = self._report.get("report")
            if isinstance(nested, dict):
                block = nested.get("trades")
        if not isinstance(block, dict) or not block:
            return
        icon = CmdLayout.icon.get
        CmdLayout.title.print_h2(f"{icon('chart')} 单笔 XGBoost + SHAP", stream=out)
        status = str(block.get("status") or "skipped")
        if status not in {"ok", "partial"}:
            reason = str(block.get("reason") or "")
            if reason == "shap_disabled":
                CmdLayout.text.print_indent(
                    "单笔 SHAP 附录默认关闭；需要时在 attribution.py 写 shap: true。",
                    stream=out,
                )
                return
            if reason == "missing_dependency":
                CmdLayout.text.print_indent(
                    f"未安装 {block.get('dependency') or 'xgboost'}，跳过单笔机器学习。",
                    stream=out,
                )
                return
            if reason == "insufficient_samples":
                CmdLayout.text.print_indent(
                    f"样本 {block.get('n') or 0} 笔不足"
                    f"（建议 ≥{block.get('min_samples') or 80}），暂不做单笔 SHAP。",
                    stream=out,
                )
                return
            if reason == "insufficient_varying_fields":
                CmdLayout.text.print_indent('变化特征不足 2 个，暂不做单笔 SHAP。', stream=out)
                return
            if reason == "insufficient_samples_per_feature":
                CmdLayout.text.print_indent(
                    f"样本 {block.get('n') or 0} 笔、特征 {block.get('n_features') or 0} 个，"
                    f"平均每特征不到 {block.get('min_ratio') or 10} 笔，暂不做单笔 SHAP。",
                    stream=out,
                )
                return
            CmdLayout.text.print_indent('这次没做单笔机器学习。', stream=out)
            return

        overview = block.get("overview") if isinstance(block.get("overview"), dict) else {}
        n = overview.get("n") or block.get("n") or 0
        n_versions = overview.get("n_versions") or block.get("n_versions") or 0
        n_feat = overview.get("n_features") or block.get("n_features") or 0
        n_param = overview.get("n_parameter") or block.get("n_parameter") or 0
        n_opp = overview.get("n_opportunity") or block.get("n_opportunity") or 0
        n_train = overview.get("n_train") or block.get("n_train") or 0
        n_test = overview.get("n_test") or block.get("n_test") or 0
        auc = overview.get("auc")
        auc_train = overview.get("auc_train")
        auc_test = overview.get("auc_test") or auc
        accuracy = overview.get("accuracy")
        split = overview.get("split") if isinstance(overview.get("split"), dict) else {}
        if not split:
            split = block.get("split") if isinstance(block.get("split"), dict) else {}
        CmdLayout.title.print_h3('模型概况', stream=out)
        CmdLayout.text.print_indent(CmdLayout.text.kv("样本数", f"{n}（{n_versions} versions）"), stream=out)
        CmdLayout.text.print_indent(CmdLayout.text.kv("特征数", f"{n_feat}（{n_param} 参数级 + {n_opp} 机会级）"), stream=out)
        CmdLayout.text.print_indent(CmdLayout.text.kv("目标", "单笔收益 > 0（二分类）"), stream=out)
        CmdLayout.text.print_indent(
            CmdLayout.text.kv(
                "拟合",
                "多特征联合（一次模型看全部特征，SHAP 再拆各自贡献）",
            ),
            stream=out,
        )
        CmdLayout.text.print_indent(
            CmdLayout.text.kv(
                "训练/测试",
                f"{n_train}/{n_test}{_split_phrase(split)}",
            ),
            stream=out,
        )
        if auc_train is not None:
            CmdLayout.text.print_indent(
                CmdLayout.text.kv("训练集AUC", f"{float(auc_train):.2f}"),
                stream=out,
            )
        if auc_test is not None:
            CmdLayout.text.print_indent(
                CmdLayout.text.kv("测试集AUC", f"{float(auc_test):.2f}"),
                stream=out,
            )
        if accuracy is not None:
            CmdLayout.text.print_indent(
                CmdLayout.text.kv("测试集准确率", f"{float(accuracy) * 100:.0f}%"),
                stream=out,
            )
        warning = _auc_warning(auc_train, auc_test, split)
        if warning:
            CmdLayout.text.print_indent(warning, stream=out)
        else:
            CmdLayout.text.print_indent("AUC 0.5 = 随机猜，0.7+ 有预测力。", stream=out)

        shap_block = block.get("shap") if isinstance(block.get("shap"), dict) else {}
        ranked = [
            item
            for item in (shap_block.get("mean_abs") or [])
            if isinstance(item, dict)
        ]
        if ranked:
            CmdLayout.title.print_h3('SHAP 特征重要性（mean |SHAP|）', stream=out)
            peak = max(
                (abs(float(item.get("mean_abs_shap") or 0.0)) for item in ranked),
                default=0.0,
            )
            CmdLayout.text.print_numbered(
                [
                    f"{_feature_label(item.get('feature')):<14} "
                    f"{float(item.get('mean_abs_shap') or 0.0):6.3f}  "
                    f"{_bar(float(item.get('mean_abs_shap') or 0.0), peak)}"
                    for item in ranked[:8]
                ],
                indent=3,
                stream=out,
            )

        directions = [
            item for item in (block.get("directions") or []) if isinstance(item, dict)
        ]
        if directions:
            CmdLayout.title.print_h3('SHAP 方向', stream=out)
            for item in directions[:6]:
                name = _feature_label(item.get("feature"))
                sign = str(item.get("sign") or "")
                low = item.get("low") if isinstance(item.get("low"), dict) else {}
                high = item.get("high") if isinstance(item.get("high"), dict) else {}
                CmdLayout.text.print_indent(f"{name}:", stream=out)
                low_shap = float(low.get("mean_shap") or 0.0)
                high_shap = float(high.get("mean_shap") or 0.0)
                CmdLayout.text.print_indent(
                    f"低值（≤ {CampaignLabels.format_number(item.get('feature'), low.get('threshold'))}）"
                    f" → {_shap_phrase(low_shap)}",
                    spaces=6,
                    stream=out,
                )
                CmdLayout.text.print_indent(
                    f"高值（≥ {CampaignLabels.format_number(item.get('feature'), high.get('threshold'))}）"
                    f" → {_shap_phrase(high_shap)}",
                    spaces=6,
                    stream=out,
                )
                conclusion = _shap_direction_conclusion(name, low_shap, high_shap, sign)
                if conclusion:
                    CmdLayout.text.print_indent(
                        CmdLayout.text.kv("结论", conclusion),
                        spaces=6,
                        stream=out,
                    )

        self._present_dependence(out, block)

    def _present_dependence(self, out: TextIO, block: Mapping[str, Any]) -> None:
        items = [item for item in (block.get("dependence") or []) if isinstance(item, dict)]
        if not items:
            return
        CmdLayout.title.print_h3('SHAP 依赖', stream=out)
        for item in items[:3]:
            feature = item.get("feature")
            name = _feature_label(feature)
            bins = [row for row in (item.get("bins") or []) if isinstance(row, dict)]
            CmdLayout.text.print_indent(f"{name}:", stream=out)
            for line in _dependence_ascii(bins, str(feature or "")):
                CmdLayout.text.print_indent(line, spaces=6, stream=out)
            note = _shap_dependence_conclusion(str(name), str(feature or ""), bins)
            if note:
                CmdLayout.text.print_indent(
                    CmdLayout.text.kv("结论", note),
                    spaces=6,
                    stream=out,
                )

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


def _feature_label(feature: Any) -> str:
    return CampaignLabels.knob_label(feature)


def _bar(value: float, peak: float, width: int = 16) -> str:
    if peak <= 0:
        return ""
    n = int(round(abs(value) / peak * width))
    return "█" * max(n, 0)


def _shap_phrase(mean_shap: float) -> str:
    if mean_shap > 0.005:
        return "正贡献（倾向赚钱）"
    if mean_shap < -0.005:
        return "负贡献（倾向亏钱）"
    return "几乎没贡献"


def _shap_direction_conclusion(
    name: str,
    low_shap: float,
    high_shap: float,
    sign: str,
) -> str:
    """两端同号时不要写成「越高/越低越赚钱」。"""
    low_text = _shap_phrase(low_shap)
    high_text = _shap_phrase(high_shap)
    low_pos = "正贡献" in low_text
    high_pos = "正贡献" in high_text
    low_neg = "负贡献" in low_text
    high_neg = "负贡献" in high_text
    if low_pos and high_neg:
        return f"{name} 越低越倾向赚钱"
    if low_neg and high_pos:
        return f"{name} 越高越倾向赚钱"
    if low_pos and high_pos:
        side = "低值" if low_shap > high_shap else "高值"
        return f"{name} 两端都倾向赚钱，{side}这边贡献更大"
    if low_neg and high_neg:
        side = "低值" if low_shap < high_shap else "高值"
        return f"{name} 两端都倾向亏钱，{side}这边更亏"
    if sign == "low_positive":
        return f"{name} 越低越倾向赚钱"
    if sign == "high_positive":
        return f"{name} 越高越倾向赚钱"
    return ""


def _split_phrase(split: Mapping[str, Any]) -> str:
    kind = str(split.get("kind") or "")
    n_groups = split.get("n_groups")
    if kind == "grouped":
        extra = f"，{n_groups} 组" if n_groups else ""
        return f" 按股票+日期成组{extra}"
    return " 随机拆行"


def _auc_warning(auc_train: Any, auc_test: Any, split: Mapping[str, Any]) -> str:
    try:
        test = float(auc_test) if auc_test is not None else None
    except (TypeError, ValueError):
        test = None
    try:
        train = float(auc_train) if auc_train is not None else None
    except (TypeError, ValueError):
        train = None
    if train is not None and test is not None and train - test >= 0.15:
        return f"训练 AUC 比测试高 {train - test:.2f}，过拟合，SHAP 方向只当线索。"
    if test is not None and test >= 0.90:
        if str(split.get("kind") or "") == "grouped":
            return "测试集 AUC 仍 ≥ 0.90，即便已成组划分，仍偏乐观。"
        return "测试集 AUC ≥ 0.90，随机拆行容易把同一笔漏进两边，先看成组划分。"
    return ""


def _dependence_ascii(
    bins: Sequence[Mapping[str, Any]],
    feature: str = "",
    height: int = 5,
) -> List[str]:
    rows = [row for row in bins if isinstance(row, dict)]
    if len(rows) < 3:
        return []
    shaps = [float(row.get("mean_shap") or 0.0) for row in rows]
    peak = max(max(abs(value) for value in shaps), 0.01)
    width = len(rows)
    grid = [[" " for _ in range(width)] for _ in range(height)]
    for x, value in enumerate(shaps):
        y = int(round((1.0 - (value / peak + 1.0) / 2.0) * (height - 1)))
        y = min(max(y, 0), height - 1)
        grid[y][x] = "●"
    axis = height // 2
    for x in range(width):
        if grid[axis][x] == " ":
            grid[axis][x] = "─"
    lines: List[str] = []
    for i, cells in enumerate(grid):
        tick = peak * (1.0 - 2.0 * i / (height - 1))
        lines.append(f"{tick:+5.2f} |{'  '.join(cells)}")
    first = CampaignLabels.format_number(feature or "value", rows[0].get("lo"))
    last = CampaignLabels.format_number(feature or "value", rows[-1].get("hi"))
    lines.append(f"       {first} → {last}")
    return lines


def _shap_dependence_conclusion(
    name: str,
    feature: str,
    bins: Sequence[Mapping[str, Any]],
) -> str:
    rows = [row for row in bins if isinstance(row, dict)]
    if len(rows) < 3:
        return ""
    shaps = [float(row.get("mean_shap") or 0.0) for row in rows]
    peak_i = max(range(len(shaps)), key=lambda i: shaps[i])
    first_pos = shaps[0] > 0.005
    last_neg = shaps[-1] < -0.005
    first_neg = shaps[0] < -0.005
    last_pos = shaps[-1] > 0.005
    peak = rows[peak_i]
    peak_text = CampaignLabels.format_number(feature, peak.get("mid"))
    if 0 < peak_i < len(rows) - 1 and shaps[peak_i] > 0.005:
        return f"不是单调，{peak_text} 附近正贡献最大"
    if first_pos and last_neg:
        cut = CampaignLabels.format_number(feature, rows[0].get("hi"))
        return f"低于 {cut} 偏正贡献，再高转负"
    if first_neg and last_pos:
        cut = CampaignLabels.format_number(feature, rows[-1].get("lo"))
        return f"高于 {cut} 偏正贡献"
    if all(value > 0.005 for value in shaps):
        return f"全程偏正贡献，{peak_text} 附近最大"
    if all(value < -0.005 for value in shaps):
        return f"全程偏负贡献，{peak_text} 附近相对没那么亏"
    return f"峰值在 {peak_text}"



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

def _hydrate_families(payload: Dict[str, Any]) -> None:
    if isinstance(payload.get("families"), dict) and payload.get("families"):
        return
    families: Dict[str, Any] = {}
    table = payload.get("table")
    attribute = payload.get("attribute")
    for name in ("inputs", "cross"):
        block = payload.get(name)
        if not isinstance(block, dict) or not (
            block.get("report")
            or block.get("contributions")
            or block.get("headline")
            or block.get("table")
        ):
            continue
        fam = dict(block)
        if isinstance(table, dict):
            fam.setdefault("table", table.get(name) or [])
        if isinstance(attribute, dict) and isinstance(attribute.get(name), dict):
            fam.setdefault("attribute", attribute.get(name) or {})
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
            "contributions": family.get("contributions") or {},
        }
    out = dict(root)
    out["headline"] = family.get("headline") or nested_report.get("headline")
    out["report"] = nested_report
    out["attribute"] = family.get("attribute") or {}
    out["table"] = family.get("table") or []
    out["gather"] = family.get("gather") or {}
    out["cells"] = family.get("cells") or []
    out["contributions"] = nested_report.get("contributions") or family.get(
        "contributions"
    ) or {}
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


def _has_enum_sections(report: Mapping[str, Any]) -> bool:
    sections = report.get("sections")
    if isinstance(sections, dict) and sections:
        return True
    nested = report.get("report")
    if isinstance(nested, dict):
        nested_sections = nested.get("sections")
        if isinstance(nested_sections, dict) and nested_sections:
            return True
    return False


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


def _step_label(level: Mapping[str, Any]) -> str:
    if level.get("is_baseline"):
        return "基准"
    prev = item_delta({"deltas": level.get("vs_prev") or []}, "portfolio", "total_return")
    if prev is not None:
        return f"相对上一档 {CampaignLabels.format_delta('total_return', prev)}"
    base = item_delta(
        {"deltas": level.get("vs_baseline") or []}, "portfolio", "total_return"
    )
    if base is not None:
        return f"相对基准 {CampaignLabels.format_delta('total_return', base)}"
    return ""


def _same_level(left: Any, right: Any) -> bool:
    if KnobContrasts.is_off(left) and KnobContrasts.is_off(right):
        return True
    return _same_number(left, right)


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


def _read_json_object(path: Path) -> Dict[str, Any]:
    raw = _read_json_any(path)
    return raw if isinstance(raw, dict) else {}


def _read_json_any(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None
