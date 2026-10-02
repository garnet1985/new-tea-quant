"""层诊断终端展示：事实 / 结论 / 建议。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TextIO

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.engines.analyzer.steps.layer.persist import load_layer_report
from core.modules.strategy.core.services.artifacts import ArtifactStore

_LAYER_TITLE = {
    "enumerate": "枚举层归因",
    "price_factor": "价格层归因",
    "portfolio": "组合层归因",
}


class LayerPresenter:
    """三块报告，不拆文件。"""

    def __init__(self, report: Mapping[str, Any], *, report_path: Optional[Path] = None) -> None:
        self._report = dict(report)
        self._report_path = Path(report_path) if report_path else None

    @classmethod
    def load(cls, store: ArtifactStore) -> "LayerPresenter":
        payload = load_layer_report(store)
        if not payload:
            raise FileNotFoundError(f"层归因报告不存在: {store.file('layer_attribution')}")
        return cls(payload, report_path=store.file("layer_attribution"))

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        layer = str(report.get("layer") or "enumerate")
        title = _LAYER_TITLE.get(layer, "层归因")
        CmdLayout.title.print_banner(f"{icon('search')} {title}", stream=out)
        vid = str(report.get("version_id") or "")
        if vid:
            print(f"{icon('gear')} version {vid}", file=out, flush=True)
        disclaimer = str(report.get("disclaimer") or "").strip()
        if disclaimer:
            print(f"{icon('info')} {disclaimer}", file=out, flush=True)
        facts = dict(report.get("facts") or {})
        CmdLayout.title.print_section(f"{icon('blue_dot')} 事实", char="-", stream=out)
        if layer == "portfolio":
            _print_portfolio_facts(facts, out)
        elif facts.get("book") is not None or layer == "price_factor":
            _print_price_facts(facts, out)
        else:
            _print_enum_facts(facts, out)
        CmdLayout.title.print_section(f"{icon('success')} 结论", char="-", stream=out)
        _print_items(report.get("conclusions") or [], out, empty="本格数字还不够写成结论。")
        CmdLayout.title.print_section(f"{icon('rocket')} 建议", char="-", stream=out)
        _print_items(report.get("suggestions") or [], out, empty="没有可执行的下一步。")
        if self._report_path:
            print(f"{icon('folder')} {self._report_path}", file=out, flush=True)


def _print_enum_facts(facts: Mapping[str, Any], out: TextIO) -> None:
    quantity = dict(facts.get("quantity") or {})
    time_block = dict(facts.get("time") or {})
    exits = dict(facts.get("exits") or {})
    leftover = dict(facts.get("leftover_upside") or {})
    total = int(quantity.get("total_opportunities") or 0)
    stocks = int(quantity.get("total_stocks") or 0)
    triggered = int(quantity.get("trigger_stocks") or 0)
    print(
        f"机会 {total} 笔 · 覆盖 {triggered}/{stocks} "
        f"({_pct(quantity.get('trigger_ratio'))}) · "
        f"前5只 { _pct(quantity.get('top5_share')) }",
        file=out,
        flush=True,
    )
    calendar = dict(time_block.get("calendar") or {})
    per_stock = dict(time_block.get("per_stock") or {})
    peak = str(calendar.get("peak_month") or "—")
    print(
        f"日历峰值 {peak} {_pct(calendar.get('peak_share'))} · "
        f"每股间隔 CV {float(per_stock.get('cv') or 0.0):.2f} "
        f"({per_stock.get('dispersion_conclusion') or '—'})",
        file=out,
        flush=True,
    )
    mix = list(exits.get("by_reason") or [])
    if mix:
        parts = [
            f"{item.get('label') or item.get('reason')}"
            f" {int(item.get('count') or 0)}"
            f"({_pct(item.get('share'))})"
            for item in mix[:6]
        ]
        print("出场 " + " · ".join(parts), file=out, flush=True)
    leftover_text = (
        "可测止盈后路径"
        if leftover.get("measurable")
        else f"止盈后路径不可测（{leftover.get('mode') or 'unknown'}）"
    )
    print(leftover_text, file=out, flush=True)


def _print_price_facts(facts: Mapping[str, Any], out: TextIO) -> None:
    book = dict(facts.get("book") or {})
    concentration = dict(facts.get("concentration") or {})
    exits = dict(facts.get("exits") or {})
    yearly = list(facts.get("yearly") or [])
    denoising = dict(facts.get("denoising") or {})
    factor = book.get("profit_factor")
    factor_text = f"{float(factor):.2f}" if factor is not None else "—"
    print(
        f"去噪账 {int(book.get('completed_count') or 0)} 笔完成 · "
        f"胜率 {_pct(book.get('win_rate'))} · "
        f"均收益 {_pct_roi(book.get('avg_roi'))} · "
        f"盈亏比 {factor_text}",
        file=out,
        flush=True,
    )
    without = concentration.get("avg_roi_without_top5_trades")
    print(
        f"利润头部：前5笔 {_pct(concentration.get('top5_trades_profit_share'))} · "
        f"去掉后均收益 {_pct_roi(without)}",
        file=out,
        flush=True,
    )
    mix = list(exits.get("by_reason") or [])
    if mix:
        parts = [
            f"{item.get('label') or item.get('reason')}"
            f" {int(item.get('count') or 0)}"
            f"(利润 {_pct(item.get('profit_share'))})"
            for item in mix[:6]
        ]
        print("出场 " + " · ".join(parts), file=out, flush=True)
    if yearly:
        parts = [
            f"{item.get('year')} {_pct_roi(item.get('avg_roi'))}"
            for item in yearly[:6]
        ]
        print("年份 " + " · ".join(parts), file=out, flush=True)
    enum_count = denoising.get("enum_count")
    merged = denoising.get("merged_count")
    if denoising.get("enum_available"):
        print(
            f"相对枚举 {enum_count}→{int(denoising.get('price_book_count') or 0)}"
            f"（并掉 {merged}，"
            f"涨停跳过 {int(denoising.get('skipped_buy_at_limit_up') or 0)}）",
            file=out,
            flush=True,
        )
    else:
        print("相对枚举：本格没有枚举产物", file=out, flush=True)


def _print_portfolio_facts(facts: Mapping[str, Any], out: TextIO) -> None:
    fill = dict(facts.get("fill") or {})
    quality = dict(facts.get("taken_vs_leftover") or {})
    taken = dict(quality.get("taken") or {})
    leftover = dict(quality.get("leftover") or {})
    alloc = dict(facts.get("allocation") or {})
    if not facts.get("price_available"):
        print("相对价格：本格没有价格账本，买到/漏掉答不了", file=out, flush=True)
    else:
        print(
            f"价格账 {int(fill.get('price_completed') or 0)} 笔完成 · "
            f"买到 {int(fill.get('taken_count') or 0)} "
            f"({_pct(fill.get('fill_ratio'))}) · "
            f"漏掉 {int(fill.get('leftover_count') or 0)}",
            file=out,
            flush=True,
        )
        print(
            f"买到均收益 {_pct_roi(taken.get('avg_roi'))} · "
            f"漏掉均收益 {_pct_roi(leftover.get('avg_roi'))} · "
            f"质量差 {_pct_roi(quality.get('roi_gap'))}",
            file=out,
            flush=True,
        )
    slots = int(fill.get("max_portfolio_size") or alloc.get("max_portfolio_size") or 0)
    peak = int(fill.get("peak_open_positions") or 0)
    cap = "顶满" if fill.get("slots_at_cap") else "未满"
    print(
        f"槽位峰值 {peak}/{slots}（{cap}）· "
        f"均持仓 {float(fill.get('avg_open_positions') or 0.0):.1f} · "
        f"账户收益 {_pct_roi(fill.get('total_return'))} · "
        f"胜率 {_pct(fill.get('win_rate'))}",
        file=out,
        flush=True,
    )
    print(
        f"利用率均 {_pct_points(fill.get('capital_utilization_ratio_pct'))} · "
        f"峰 {_pct_points(fill.get('peak_capital_utilization_ratio_pct'))} · "
        f"满仓天数 {_pct_points(fill.get('full_exposure_days_ratio_pct'))} · "
        f"前5只 {_pct_points(fill.get('top5_profit_concentration_pct'))}",
        file=out,
        flush=True,
    )
    _print_portfolio_groups(list(facts.get("groups") or []), out)


def _print_portfolio_groups(groups: Sequence[Any], out: TextIO) -> None:
    rows = [dict(item) for item in groups if isinstance(item, Mapping)]
    preferred = [item for item in rows if item.get("kind") == "rsi"]
    chosen = preferred or [item for item in rows if item.get("kind") == "exit"] or rows
    if not chosen:
        return
    parts = [
        (
            f"{item.get('name')}"
            f" 价格{_pct_roi(item.get('price_avg_roi'))}"
            f" 买到{int(item.get('taken_count') or 0)}"
        )
        for item in chosen[:4]
    ]
    print("分组 " + " · ".join(parts), file=out, flush=True)


def _print_items(items: Sequence[Any], out: TextIO, *, empty: str) -> None:
    rows = [dict(item) for item in items if isinstance(item, Mapping)]
    if not rows:
        print(empty, file=out, flush=True)
        return
    for idx, item in enumerate(rows, start=1):
        print(f"{idx}. {item.get('text') or ''}", file=out, flush=True)


def _pct(value: Any) -> str:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return "0.0%"
    return f"{number:.1%}"


def _pct_roi(value: Any) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number * 100.0:.1f}%"


def _pct_points(value: Any) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:.1f}%"
