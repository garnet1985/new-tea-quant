"""CMD presenter for attribution ``analysis/report.json``."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

from .consts import ANALYSIS_SUBDIR, REPORT_JSON
from .insights import build_insights

_SECTION_WIDTH = 64


class AnalysisReportPresenter:
    """Conclusion-first CMD view of one step's attribution report."""

    def __init__(self, report: Dict[str, Any], *, report_path: Path) -> None:
        self._report = report
        self._report_path = Path(report_path)

    @classmethod
    def load(cls, output_dir: Union[str, Path]) -> "AnalysisReportPresenter":
        """Load ``{output_dir}/analysis/report.json``."""
        report_path = Path(output_dir) / ANALYSIS_SUBDIR / REPORT_JSON
        if not report_path.is_file():
            raise FileNotFoundError(
                f"归因报告不存在: {report_path}（请先运行 sa / Strategy.analyze）"
            )
        payload = ArtifactIO.read_json(report_path)
        if not isinstance(payload, dict):
            raise ValueError(f"归因报告格式无效: {report_path}")
        return cls(payload, report_path=report_path)

    def present(self, stream: Optional[TextIO] = None) -> None:
        """Print conclusion-first attribution feedback."""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        insights = build_insights(report)

        CmdLayout.title.print_banner(f"{icon('chart')} 这次回测怎么读", stream=out)
        print(
            f"{icon('gear')} 策略 {report.get('strategy_key') or '-'}  ·  "
            f"{_step_label(report.get('step'))}  ·  "
            f"版本 v{report.get('version_id') or '-'}",
            file=out,
            flush=True,
        )

        self._present_headline(out, insights)
        self._present_chart(out, insights)
        self._present_key_findings(out, insights)
        self._present_explains(out, insights)
        self._present_next_steps(out, insights)
        self._present_technical(out, insights)
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)

    def _present_headline(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('target')} 一句话结论", stream=out)
        print(f"   {insights.get('headline') or '-'}", file=out, flush=True)

    def _present_chart(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        tiers = insights.get("tiers") or []
        if not isinstance(tiers, list) or len(tiers) < 1:
            return

        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('bar_chart')} 证据（看差距）", stream=out)
        note = str(insights.get("chart_note") or "").strip()
        if note:
            print(f"   {note}", file=out, flush=True)

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
                print(
                    f"   ┊ 明显的分水岭 ≈ {_fmt_num(cut)}",
                    file=out,
                    flush=True,
                )

        print("", file=out, flush=True)
        for tier in tiers:
            if not isinstance(tier, dict):
                continue
            mean_roi = tier.get("mean_roi")
            win_rate = tier.get("win_rate")
            count = tier.get("count")
            roi_text = f"{float(mean_roi) * 100:.1f}%" if mean_roi is not None else "-"
            win_text = f"{float(win_rate) * 100:.0f}%" if win_rate is not None else "-"
            print(
                f"   · {tier.get('label')}: 平均收益 {roi_text}  ·  "
                f"{count} 笔  ·  胜率 {win_text}",
                file=out,
                flush=True,
            )

        how = _how_to_read(tiers)
        if how:
            print(f"\n   怎么看：{how}", file=out, flush=True)

    def _present_key_findings(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        findings = insights.get("key_findings") or []
        if not isinstance(findings, list) or not findings:
            return
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('rocket')} 关键发现", stream=out)
        for item in findings:
            if not isinstance(item, dict):
                continue
            print(
                f"   [{item.get('value')}]  {item.get('caption')}",
                file=out,
                flush=True,
            )

    def _present_explains(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        explains = insights.get("explains") or []
        does_not = insights.get("does_not_explain") or []
        if not explains and not does_not:
            return
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(
            f"{icon('blue_dot')} 说明了什么 / 没说明什么",
            stream=out,
        )
        if explains:
            print("   能说的:", file=out, flush=True)
            for line in explains:
                print(f"     ✓ {line}", file=out, flush=True)
        if does_not:
            print("   不能说的:", file=out, flush=True)
            for line in does_not:
                print(f"     ✗ {line}", file=out, flush=True)

    def _present_next_steps(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        steps = insights.get("next_steps") or []
        if not isinstance(steps, list) or not steps:
            return
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('success')} 建议下一步", stream=out)
        for index, step in enumerate(steps, start=1):
            print(f"   {index}. {step}", file=out, flush=True)

    def _present_technical(self, out: TextIO, insights: Dict[str, Any]) -> None:
        icon = CmdLayout.icon.get
        tech = insights.get("technical") if isinstance(insights.get("technical"), dict) else {}
        CmdLayout.separator.print_line(width=_SECTION_WIDTH, stream=out)
        CmdLayout.title.print_section(f"{icon('gear')} 技术细节", stream=out)
        parts: List[str] = []
        if tech.get("sample_size") is not None:
            parts.append(f"样本 {tech.get('sample_size')} 笔")
        if tech.get("range"):
            field = tech.get("field_key") or "条件"
            parts.append(f"{field} 区间 {tech.get('range')}")
        if tech.get("binning"):
            parts.append(str(tech.get("binning")))
        if parts:
            print(f"   {' · '.join(parts)}", file=out, flush=True)
        if tech.get("correlation"):
            print(f"   统计：{tech.get('correlation')}", file=out, flush=True)
        if tech.get("disclaimer"):
            print(f"   免责：{tech.get('disclaimer')}", file=out, flush=True)
        print(f"   文件：{self._report_path}", file=out, flush=True)


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
