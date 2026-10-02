"""CMD presenter for attribution ``analysis/report.json``."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.services.artifacts import ArtifactStore

from .insight import InsightBuilder


class AnalysisReportPresenter:
    """Conclusion-first CMD view of one step's attribution report."""

    def __init__(self, report: Dict[str, Any], *, report_path: Path) -> None:
        self._report = report
        self._report_path = Path(report_path)

    @classmethod
    def load(cls, output_dir: Union[str, Path]) -> "AnalysisReportPresenter":
        """Load ``{output_dir}/analysis/report.json`` via artifact store."""
        report_path = ArtifactStore.named_path(output_dir, "analysis_report")
        if not report_path.is_file():
            raise FileNotFoundError(
                f"归因报告不存在: {report_path}"
            )
        payload = ArtifactStore.read_json_at(output_dir, "analysis_report")
        if not isinstance(payload, dict):
            raise ValueError(f"归因报告格式无效: {report_path}")
        return cls(payload, report_path=report_path)

    def present(self, stream: Optional[TextIO] = None) -> None:
        """Print conclusion-first attribution feedback."""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        insights = InsightBuilder.resolve(report)

        CmdLayout.title.print_h1(f"{icon('chart')} 这次回测怎么读", stream=out)
        meta = CmdLayout.text.meta(
            [
                f"策略 {report.get('strategy_key') or '-'}",
                _step_label(report.get('step')),
                f"当前版本 v{report.get('version_id') or '-'}",
            ]
        )
        print(f"{icon('gear')} {meta}", file=out, flush=True)

        self._present_headline(out, insights)
        self._present_chart(out, insights)
        self._present_key_findings(out, insights)
        self._present_other_fields(out, insights)
        self._present_multivariate(out, insights)
        self._present_run_comparison(out, insights)
        self._present_explains(out, insights)
        self._present_next_steps(out, insights)
        self._present_technical(out, insights)

    def _present_headline(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        CmdLayout.title.print_h2(f"{icon('target')} 一句话结论", stream=out)
        CmdLayout.text.print_indent(insights.get('headline') or '-', stream=out)

    def _present_chart(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        tiers = insights.get("tiers") or []
        note = str(insights.get("chart_note") or "").strip()
        has_tiers = isinstance(tiers, list) and len(tiers) >= 1
        if not has_tiers and not note:
            return
        CmdLayout.title.print_h2(f"{icon('bar_chart')} 证据（看差距）", stream=out)
        if note:
            CmdLayout.text.print_indent(note, stream=out)
        if not has_tiers:
            return

        chart_rows = []
        for tier in tiers:
            if not isinstance(tier, dict) or tier.get("mean_roi") is None:
                continue
            label = str(tier.get("label") or "?")
            # Scale percent points so bars stay readable (11.0 -> 11).
            chart_rows.append((label, float(tier["mean_roi"]) * 100.0))
        if chart_rows:
            print("", file=out, flush=True)
            CmdLayout.bar_chart.print(
                chart_rows,
                title="   平均收益（%）",
                width=22,
                show_count=True,
                show_pct=False,
                stream=out,
            )

        if len(tiers) == 2:
            cut = tiers[1].get("min") if isinstance(tiers[1], dict) else None
            if cut is not None:
                CmdLayout.text.print_indent(
                    f"┊ 明显的分水岭 ≈ {_fmt_num(cut)}",
                    stream=out,
                )

        lines = []
        for tier in tiers:
            if not isinstance(tier, dict):
                continue
            mean_roi = tier.get("mean_roi")
            win_rate = tier.get("win_rate")
            count = tier.get("count")
            roi_text = f"{float(mean_roi) * 100:.1f}%" if mean_roi is not None else "-"
            win_text = f"{float(win_rate) * 100:.0f}%" if win_rate is not None else "-"
            lines.append(
                f"{tier.get('label')}: 平均收益 {roi_text}  ·  "
                f"{count} 笔  ·  胜率 {win_text}"
            )
        if lines:
            print("", file=out, flush=True)
            CmdLayout.text.print_bullets(lines, indent=3, marker="·", stream=out)

        how = _how_to_read(tiers)
        if how:
            print("", file=out, flush=True)
            CmdLayout.text.print_indent(f"怎么看：{how}", stream=out)

    def _present_key_findings(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        findings = insights.get("key_findings") or []
        if not isinstance(findings, list) or not findings:
            return
        CmdLayout.title.print_h2(f"{icon('rocket')} 关键发现", stream=out)
        CmdLayout.text.print_indent(
            "\n".join(
                f"[{item.get('value')}]  {item.get('caption')}"
                for item in findings
                if isinstance(item, dict)
            ),
            stream=out,
        )

    def _present_other_fields(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        items = insights.get("other_fields") or []
        if not isinstance(items, list) or not items:
            return
        CmdLayout.title.print_h2(f"{icon('clipboard')} 其他变化条件", stream=out)
        CmdLayout.text.print_indent(
            "\n".join(
                f"[{item.get('value')}]  {item.get('caption')}"
                for item in items
                if isinstance(item, dict)
            ),
            stream=out,
        )

    def _present_multivariate(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        block = insights.get("multivariate")
        if not isinstance(block, dict):
            return
        status = str(block.get("status") or "")
        features = block.get("features") or []
        found = int(block.get("found_features") or len(features) or 0)
        ranking = block.get("ranking") or []
        if status in ("ok", "partial"):
            pass
        elif found >= 2 or (isinstance(ranking, list) and ranking):
            pass
        else:
            return
        CmdLayout.title.print_h2(f"{icon('line_chart')} 多指标一起看", stream=out)
        headline = str(block.get("headline") or "").strip()
        if headline:
            CmdLayout.text.print_indent(headline, stream=out)
        if isinstance(ranking, list) and ranking:
            print("", file=out, flush=True)
            CmdLayout.title.print_h3("相对重要性", stream=out)
            CmdLayout.text.print_bullets(
                [
                    f"{item.get('key')}: {item.get('caption')}  [{item.get('value')}]"
                    for item in ranking[:4]
                    if isinstance(item, dict)
                ],
                indent=3,
                marker="·",
                stream=out,
            )
        explains = block.get("explains") or []
        does_not = block.get("does_not_explain") or []
        if explains or does_not:
            print("", file=out, flush=True)
        if explains:
            CmdLayout.text.print_bullets(explains, indent=5, marker="✓", stream=out)
        if does_not:
            CmdLayout.text.print_bullets(does_not, indent=5, marker="✗", stream=out)

        ml = insights.get("ml") if isinstance(insights.get("ml"), dict) else {}
        if ml.get("status") in ("ok", "partial") and ml.get("headline"):
            print("", file=out, flush=True)
            CmdLayout.text.print_indent(f"机器学习补充：{ml.get('headline')}", stream=out)

    def _present_run_comparison(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        block = insights.get("run_comparison")
        if not isinstance(block, dict) or block.get("status") != "ok":
            return
        CmdLayout.title.print_h2(f"{icon('eyes')} 两次回测对照", stream=out)
        headline = str(block.get("headline") or "").strip()
        if headline:
            CmdLayout.text.print_indent(headline, stream=out)
        baseline = block.get("baseline_version_id")
        current = block.get("current_version_id")
        if baseline or current:
            CmdLayout.text.print_indent(
                f"当前 v{current or '-'}  vs  对照 v{baseline or '-'}",
                stream=out,
            )
        changes = block.get("changes") or []
        if isinstance(changes, list) and changes:
            print("", file=out, flush=True)
            CmdLayout.title.print_h3("改了什么", stream=out)
            CmdLayout.text.print_bullets(
                [
                    f"{item.get('label')}: {item.get('detail')}"
                    for item in changes[:6]
                    if isinstance(item, dict)
                ],
                indent=3,
                marker="·",
                stream=out,
            )
        explains = block.get("explains") or []
        does_not = block.get("does_not_explain") or []
        if explains or does_not:
            print("", file=out, flush=True)
        if explains:
            CmdLayout.title.print_h3("能说的", stream=out)
            CmdLayout.text.print_bullets(explains, indent=3, marker="✓", stream=out)
        if does_not:
            CmdLayout.title.print_h3("不能说的", stream=out)
            CmdLayout.text.print_bullets(does_not, indent=3, marker="✗", stream=out)

    def _present_explains(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        explains = insights.get("explains") or []
        does_not = insights.get("does_not_explain") or []
        if not explains and not does_not:
            return
        CmdLayout.title.print_h2(
            f"{icon('blue_dot')} 说明了什么 / 没说明什么",
            stream=out,
        )
        if explains:
            CmdLayout.title.print_h3("能说的", stream=out)
            CmdLayout.text.print_bullets(explains, indent=3, marker="✓", stream=out)
        if does_not:
            CmdLayout.title.print_h3("不能说的", stream=out)
            CmdLayout.text.print_bullets(does_not, indent=3, marker="✗", stream=out)

    def _present_next_steps(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        steps = insights.get("next_steps") or []
        if not isinstance(steps, list) or not steps:
            return
        CmdLayout.title.print_h2(f"{icon('success')} 建议下一步", stream=out)
        CmdLayout.text.print_numbered(steps, indent=3, stream=out)

    def _present_technical(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        tech = insights.get("technical") if isinstance(insights.get("technical"), dict) else {}
        CmdLayout.title.print_h2(f"{icon('gear')} 技术细节", stream=out)
        parts: List[str] = []
        if tech.get("sample_size") is not None:
            parts.append(f"样本 {tech.get('sample_size')} 笔")
        if tech.get("range"):
            field = tech.get("field_key") or "条件"
            parts.append(f"{field} 区间 {tech.get('range')}")
        if tech.get("binning"):
            parts.append(str(tech.get("binning")))
        if parts:
            CmdLayout.text.print_indent(CmdLayout.text.meta(parts), stream=out)
        if tech.get("correlation"):
            CmdLayout.text.print_indent(f"统计：{tech.get('correlation')}", stream=out)
        if tech.get("skip_summary"):
            CmdLayout.text.print_indent(f"跳过：{tech.get('skip_summary')}", stream=out)
        if tech.get("disclaimer"):
            CmdLayout.text.print_indent(f"免责：{tech.get('disclaimer')}", stream=out)
        CmdLayout.text.print_indent(f"文件：{self._report_path}", stream=out)


def _how_to_read(tiers: List[Any]) -> str:
    if len(tiers) != 2:
        if not tiers:
            return ""
        best = max(
            (t for t in tiers if isinstance(t, dict) and t.get("mean_roi") is not None),
            key=lambda item: float(item["mean_roi"]),
            default=None,
        )
        if best is None:
            return ""
        return (
            f"表现最好的是 {_fmt_num(best.get('min'))}~{_fmt_num(best.get('max'))} "
            f"这一档（平均收益 {float(best['mean_roi']) * 100:.1f}%）。"
        )
    low, high = tiers[0], tiers[1]
    if not isinstance(low, dict) or not isinstance(high, dict):
        return ""
    if low.get("mean_roi") is None or high.get("mean_roi") is None:
        return ""
    low_roi = float(low["mean_roi"]) * 100
    high_roi = float(high["mean_roi"]) * 100
    cut = high.get("min")
    if low_roi >= high_roi:
        return (
            f"左边/低段（{low.get('label')}）平均赚 {low_roi:.1f}%，"
            f"右边/高段（{high.get('label')}）平均赚 {high_roi:.1f}%。"
            f"差距明显，但中间没有平滑渐变"
            + (f"— 更像「低于约 {_fmt_num(cut)} 明显更好」。" if cut is not None else "。")
        )
    return (
        f"高段（{high.get('label')}）平均赚 {high_roi:.1f}%，"
        f"低段（{low.get('label')}）平均赚 {low_roi:.1f}%。差距明显。"
    )


def _step_label(step: Any) -> str:
    mapping = {
        "enum": "机会枚举",
        "enumerate": "机会枚举",
        "price": "价格模拟",
        "price_factor": "价格模拟",
        "portfolio": "组合模拟",
    }
    text = str(step or "").strip()
    return mapping.get(text, text or "-")


def _fmt_num(value: Any, digits: int = 1) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.{digits}f}"


__all__ = ["AnalysisReportPresenter"]
