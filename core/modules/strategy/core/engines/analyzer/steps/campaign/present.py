"""战役报告的终端展示：先看贡献度，再看对照表。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, TextIO, Union

from core.infra.cmd_layout import CmdLayout

from .contrasts import KnobContrasts
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
            _hydrate_families(payload)
        return cls(payload)

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        persist = report.get("persist") if isinstance(report.get("persist"), dict) else {}
        families = _family_blocks(report)
        gather = report.get("gather") if isinstance(report.get("gather"), dict) else {}
        tables = _all_table_rows(report)
        ready = int(gather.get("ready_count") or 0)
        group_id = report.get("group_id") or persist.get("group_id")
        vids = [
            str(row.get("version_id"))
            for row in tables
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

        if len(families) >= 2:
            for name in ("overlays", "matrix"):
                block = families.get(name)
                if not isinstance(block, dict):
                    continue
                CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
                title = "单因子" if name == "overlays" else "交叉"
                CmdLayout.title.print_section(f"{icon('rocket')} {title}", stream=out)
                view = CampaignPresenter(_family_present_payload(report, block))
                view._present_family_body(out)
        else:
            self._present_family_body(out)

        self._present_trades(out)
        self._present_paths(out, persist)
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)

    def _present_family_body(self, out: TextIO) -> None:
        table = _table_rows(self._report)
        self._present_presence(out)
        self._present_sensitivity(out)
        self._present_cross_layer(out)
        self._present_interaction(out)
        self._present_table(out, table)
        self._present_highlights(out)
        self._present_skipped(out)
        self._present_hints(out)

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

    def _present_trades(self, out: TextIO) -> None:
        block = self._report.get("trades")
        if not isinstance(block, dict):
            nested = self._report.get("report")
            if isinstance(nested, dict):
                block = nested.get("trades")
        if not isinstance(block, dict) or not block:
            return
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('chart')} 单笔 XGBoost + SHAP", stream=out)
        status = str(block.get("status") or "skipped")
        if status not in {"ok", "partial"}:
            reason = str(block.get("reason") or "")
            if reason == "missing_dependency":
                print(
                    f"   未安装 {block.get('dependency') or 'xgboost'}，跳过单笔机器学习。",
                    file=out,
                    flush=True,
                )
                return
            if reason == "insufficient_samples":
                print(
                    f"   样本 {block.get('n') or 0} 笔不足"
                    f"（建议 ≥{block.get('min_samples') or 80}），暂不做单笔 SHAP。",
                    file=out,
                    flush=True,
                )
                return
            if reason == "insufficient_varying_fields":
                print("   变化特征不足 2 个，暂不做单笔 SHAP。", file=out, flush=True)
                return
            if reason == "insufficient_samples_per_feature":
                print(
                    f"   样本 {block.get('n') or 0} 笔、特征 {block.get('n_features') or 0} 个，"
                    f"平均每特征不到 {block.get('min_ratio') or 10} 笔，暂不做单笔 SHAP。",
                    file=out,
                    flush=True,
                )
                return
            print("   这次没做单笔机器学习。", file=out, flush=True)
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
        print("   模型概况", file=out, flush=True)
        print(
            f"   样本数: {n}（{n_versions} versions）",
            file=out,
            flush=True,
        )
        print(
            f"   特征数: {n_feat}（{n_param} 参数级 + {n_opp} 机会级）",
            file=out,
            flush=True,
        )
        print("   目标: 单笔收益 > 0（二分类）", file=out, flush=True)
        print(
            "   拟合: 多因子联合（一次模型看全部特征，SHAP 再拆各自贡献）",
            file=out,
            flush=True,
        )
        print(
            f"   训练/测试: {n_train}/{n_test}{_split_phrase(split)}",
            file=out,
            flush=True,
        )
        if auc_train is not None:
            print(f"   训练集AUC: {float(auc_train):.2f}", file=out, flush=True)
        if auc_test is not None:
            print(f"   测试集AUC: {float(auc_test):.2f}", file=out, flush=True)
        if accuracy is not None:
            print(f"   测试集准确率: {float(accuracy) * 100:.0f}%", file=out, flush=True)
        warning = _auc_warning(auc_train, auc_test, split)
        if warning:
            print(f"   {warning}", file=out, flush=True)
        else:
            print(
                "   AUC 0.5 = 随机猜，0.7+ 有预测力。",
                file=out,
                flush=True,
            )

        shap_block = block.get("shap") if isinstance(block.get("shap"), dict) else {}
        ranked = [
            item
            for item in (shap_block.get("mean_abs") or [])
            if isinstance(item, dict)
        ]
        if ranked:
            print("", file=out, flush=True)
            print("   SHAP 因子重要性（mean |SHAP|）", file=out, flush=True)
            peak = max(
                (abs(float(item.get("mean_abs_shap") or 0.0)) for item in ranked),
                default=0.0,
            )
            for i, item in enumerate(ranked[:8], start=1):
                name = _feature_label(item.get("feature"))
                score = float(item.get("mean_abs_shap") or 0.0)
                bar = _bar(score, peak)
                print(
                    f"   {i}. {name:<14} {score:6.3f}  {bar}",
                    file=out,
                    flush=True,
                )

        directions = [
            item for item in (block.get("directions") or []) if isinstance(item, dict)
        ]
        if directions:
            print("", file=out, flush=True)
            print("   SHAP 方向", file=out, flush=True)
            for item in directions[:6]:
                name = _feature_label(item.get("feature"))
                sign = str(item.get("sign") or "")
                low = item.get("low") if isinstance(item.get("low"), dict) else {}
                high = item.get("high") if isinstance(item.get("high"), dict) else {}
                print(f"   {name}:", file=out, flush=True)
                low_shap = float(low.get("mean_shap") or 0.0)
                high_shap = float(high.get("mean_shap") or 0.0)
                print(
                    f"      低值（≤ {CampaignLabels.format_number(item.get('feature'), low.get('threshold'))}）"
                    f" → {_shap_phrase(low_shap)}",
                    file=out,
                    flush=True,
                )
                print(
                    f"      高值（≥ {CampaignLabels.format_number(item.get('feature'), high.get('threshold'))}）"
                    f" → {_shap_phrase(high_shap)}",
                    file=out,
                    flush=True,
                )
                conclusion = _shap_direction_conclusion(name, low_shap, high_shap, sign)
                if conclusion:
                    print(f"      结论: {conclusion}", file=out, flush=True)

        self._present_dependence(out, block)

    def _present_dependence(self, out: TextIO, block: Mapping[str, Any]) -> None:
        items = [item for item in (block.get("dependence") or []) if isinstance(item, dict)]
        if not items:
            return
        print("", file=out, flush=True)
        print("   SHAP 依赖", file=out, flush=True)
        for item in items[:3]:
            feature = item.get("feature")
            name = _feature_label(feature)
            bins = [row for row in (item.get("bins") or []) if isinstance(row, dict)]
            print(f"   {name}:", file=out, flush=True)
            for line in _dependence_ascii(bins, str(feature or "")):
                print(f"      {line}", file=out, flush=True)
            note = _shap_dependence_conclusion(str(name), str(feature or ""), bins)
            if note:
                print(f"      结论: {note}", file=out, flush=True)

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


def _hydrate_families(payload: Dict[str, Any]) -> None:
    if isinstance(payload.get("families"), dict) and payload.get("families"):
        return
    families: Dict[str, Any] = {}
    table = payload.get("table")
    attribute = payload.get("attribute")
    for name in ("overlays", "matrix"):
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
