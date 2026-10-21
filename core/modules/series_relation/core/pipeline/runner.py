"""跑批：拉数 → 变换 → 归一化 → 落盘 → 可选分析。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from core.modules.series_relation.core.constants import (
    MAX_SERIES,
    SOURCE_STRATEGY_SIM,
)
from core.modules.series_relation.core.pipeline.analyze import pairwise_summary
from core.modules.series_relation.core.pipeline.cli_report import format_cli_report
from core.modules.series_relation.core.pipeline.load_series import (
    extract_field_points,
    load_contract_rows,
)
from core.modules.series_relation.core.pipeline.load_strategy_sim import (
    StrategySimLoadError,
    load_strategy_sim_points,
)
from core.modules.series_relation.core.pipeline.normalize import normalize_points
from core.modules.series_relation.core.pipeline.transform import apply_transform

LoadRowsFn = Callable[..., Any]


def run_relation(
    settings: Mapping[str, Any],
    *,
    output_dir: Path,
    load_rows: Optional[LoadRowsFn] = None,
    load_strategy_sim: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """写入 meta/series/summary（及可选 findings），返回摘要 dict。"""
    series_cfg = list(settings.get("series") or [])
    if len(series_cfg) > MAX_SERIES:
        raise ValueError(f"series 超过 MAX_SERIES={MAX_SERIES}")

    range_cfg = settings.get("range") if isinstance(settings.get("range"), Mapping) else {}
    start = str(range_cfg.get("start_date") or "").strip()
    end = str(range_cfg.get("end_date") or "").strip()
    normalize = str(settings.get("normalize") or "zscore")
    fill = str(settings.get("fill") or "none")
    analyze = bool(settings.get("analyze", True))
    meta_cfg = settings.get("meta") if isinstance(settings.get("meta"), Mapping) else {}
    key = str(meta_cfg.get("key") or "").strip()

    loader = load_rows or load_contract_rows
    sim_loader = load_strategy_sim or load_strategy_sim_points
    series_out: List[Dict[str, Any]] = []
    meta_series: List[Dict[str, Any]] = []
    calendar: set = set()
    notes: List[str] = [
        "统计在两两日期交集上计算；图为日期并集连点。",
    ]

    for index, item in enumerate(series_cfg):
        sid = f"s{index}"
        source = str(item.get("source") or "").strip() or "data_key"
        label = str(item.get("label") or "").strip() or sid
        transform = str(item.get("transform") or "none").strip() or "none"
        resolved: Dict[str, Any] = {}

        if source == SOURCE_STRATEGY_SIM:
            try:
                points_raw, resolved = sim_loader(
                    item, start_date=start, end_date=end
                )
            except StrategySimLoadError:
                raise
            except Exception as exc:
                raise StrategySimLoadError(str(exc)) from exc
            if str(item.get("layer") or "") == "price" and str(
                item.get("metric") or ""
            ) == "cum_exit_roi":
                notes.append(
                    f"{label}: price.cum_exit_roi 为按平仓日累加的已实现 ROI（事件曲线，非盯市净值）；"
                    "先后/稳不稳请谨慎解读。"
                )
        else:
            data_key = str(item.get("data_key") or "").strip()
            field = str(item.get("field") or "").strip()
            entity_id = str(item.get("entity_id") or "").strip()
            rows = loader(data_key, entity_id=entity_id)
            points_raw = extract_field_points(
                rows, field, start_date=start, end_date=end
            )

        if fill == "ffill":
            points_raw = _ffill_on_union(points_raw, start=start, end=end)
        points_raw = apply_transform(points_raw, transform)
        if source == SOURCE_STRATEGY_SIM and not points_raw:
            raise StrategySimLoadError(
                f"{label}: transform={transform} 后无有效点（样本过短或装载为空）"
            )

        points = normalize_points(points_raw, normalize)
        for point in points:
            calendar.add(str(point["date"]))
        series_out.append({"id": sid, "label": label, "points": points})
        dates = [str(p["date"]) for p in points]
        meta_item: Dict[str, Any] = {
            "id": sid,
            "source": source,
            "label": label,
            "transform": transform,
            "point_count": len(points),
            "date_min": dates[0] if dates else "",
            "date_max": dates[-1] if dates else "",
        }
        if source == SOURCE_STRATEGY_SIM:
            sk = str(
                item.get("strategy_key") or item.get("strategy") or ""
            )
            meta_item.update(
                {
                    "strategy_key": sk,
                    "strategy": sk,
                    "version": str(item.get("version") or "latest"),
                    "resolved_version": str(resolved.get("resolved_version") or ""),
                    "layer": str(item.get("layer") or ""),
                    "metric": str(item.get("metric") or ""),
                    "entity_id": str(item.get("entity_id") or ""),
                    "data_key": "",
                    "field": str(item.get("metric") or ""),
                    "scope": "strategy_sim",
                }
            )
        else:
            meta_item.update(
                {
                    "data_key": str(item.get("data_key") or ""),
                    "entity_id": str(item.get("entity_id") or ""),
                    "field": str(item.get("field") or ""),
                    "scope": str(item.get("scope") or "").strip(),
                }
            )
        meta_series.append(meta_item)

    calendar_list = sorted(calendar)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "key": key,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "normalize": normalize,
        "fill": fill,
        "max_series": MAX_SERIES,
        "range": {"start_date": start, "end_date": end},
        "series": meta_series,
    }
    series_doc = {"calendar": calendar_list, "series": series_out}

    _write_json(output_dir / "meta.json", meta)
    _write_json(output_dir / "series.json", series_doc)

    summary: Dict[str, Any] = {
        "series_count": len(series_out),
        "calendar_len": len(calendar_list),
        "notes": notes,
    }
    if analyze and len(series_out) >= 2:
        labels = {str(s["id"]): str(s.get("label") or s["id"]) for s in series_out}
        summary["pairwise"] = pairwise_summary(series_out, labels=labels)
        findings = _render_findings(meta, summary)
        (output_dir / "findings.md").write_text(findings, encoding="utf-8")
    else:
        summary["pairwise"] = []

    _write_json(output_dir / "summary.json", summary)

    report = format_cli_report(meta, summary)
    (output_dir / "report.txt").write_text(report, encoding="utf-8")

    return {
        "success": True,
        "key": key,
        "output_dir": str(output_dir),
        "series_count": len(series_out),
        "calendar_len": len(calendar_list),
        "report": report,
    }


def _ffill_on_union(
    points: List[Tuple[str, float]],
    *,
    start: str,
    end: str,
) -> List[Tuple[str, float]]:
    _ = (start, end)
    return list(points)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _render_findings(meta: Mapping[str, Any], summary: Mapping[str, Any]) -> str:
    lines = [
        f"# {meta.get('key') or 'series_relation'}",
        "",
        f"- normalize: `{meta.get('normalize')}`",
        f"- fill: `{meta.get('fill')}`",
        f"- calendar_len: {summary.get('calendar_len')}",
        "",
        "## 数据",
        "",
    ]
    from core.modules.series_relation.core.pipeline.cli_report import (
        _participant_who,
    )

    for item in meta.get("series") or []:
        who = _participant_who(item) if isinstance(item, Mapping) else ""
        lines.append(
            f"- `{item.get('id')}` {item.get('label')}: "
            f"n={item.get('point_count')} "
            f"[{item.get('date_min')} .. {item.get('date_max')}]"
            + (f"  ← {who}" if who else "")
        )

    for note in summary.get("notes") or []:
        if "cum_exit_roi" in str(note) or "事件" in str(note):
            lines.append(f"- 注意：{note}")

    lines.extend(
        [
            "",
            "## 参与者",
            "",
        ]
    )
    for item in meta.get("series") or []:
        if not isinstance(item, Mapping):
            continue
        who = _participant_who(item)
        lines.append(
            f"- `{item.get('id')}` {item.get('label')}"
            + (f" ← {who}" if who else "")
        )

    lines.extend(
        [
            "",
            "## 核心：同向还是反向 / 谁先谁后 / 波动差多少",
            "",
            "白话结论在前；括号内为专业指标。统计描述，不是因果。",
            "",
        ]
    )
    for row in summary.get("pairwise") or []:
        core = row.get("core") if isinstance(row.get("core"), Mapping) else {}
        lines.append(f"- {core.get('relation_text') or ''}".rstrip())
        lead = str(core.get("lead_text") or "").strip()
        if lead:
            lines.append(f"  - 谁先谁后：{lead}")
        scale = str(core.get("scale_text") or "").strip()
        if scale:
            lines.append(f"  - 波动差多少：{scale}")
        from core.modules.series_relation.core.pipeline.format_num import fmt_coef

        lines.append(
            f"  - 样本 overlap_n={row.get('overlap_n')} "
            f"reliable={row.get('reliable')} "
            f"β(B|A)={fmt_coef(row.get('beta_b_on_a'))}"
        )

    lines.extend(
        [
            "",
            "## 补充：关系稳不稳、样本够不够",
            "",
            "「翻转」=相邻滚动窗从正相关变成负相关（或反过来）；"
            "分母=最多可能翻转的次数（窗数−1）。",
            "",
        ]
    )
    from core.modules.series_relation.core.pipeline.cli_report import (
        format_rolling_stability,
    )

    for row in summary.get("pairwise") or []:
        label = f"{row.get('label_a')} vs {row.get('label_b')}"
        for warn in row.get("warnings") or []:
            lines.append(f"- {label}：{warn}")
        rolling = None
        supplement = row.get("supplement")
        if isinstance(supplement, Mapping):
            rolling = supplement.get("rolling")
        if isinstance(rolling, Mapping):
            lines.append(f"- {label}：{format_rolling_stability(rolling)}")
        elif not (row.get("warnings") or []):
            lines.append(f"- {label}：无额外补充项")

    lines.append("")
    return "\n".join(lines)


__all__ = ["run_relation"]
