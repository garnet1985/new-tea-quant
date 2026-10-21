"""跑批：拉数 → 归一化 → 落盘 → 可选分析。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from core.modules.series_relation.core.constants import MAX_SERIES
from core.modules.series_relation.core.pipeline.analyze import pairwise_summary
from core.modules.series_relation.core.pipeline.cli_report import format_cli_report
from core.modules.series_relation.core.pipeline.load_series import (
    extract_field_points,
    load_contract_rows,
)
from core.modules.series_relation.core.pipeline.normalize import normalize_points

LoadRowsFn = Callable[..., Any]


def run_relation(
    settings: Mapping[str, Any],
    *,
    output_dir: Path,
    load_rows: Optional[LoadRowsFn] = None,
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
    series_out: List[Dict[str, Any]] = []
    meta_series: List[Dict[str, Any]] = []
    calendar: set = set()

    for index, item in enumerate(series_cfg):
        sid = f"s{index}"
        data_key = str(item.get("data_key") or "").strip()
        field = str(item.get("field") or "").strip()
        entity_id = str(item.get("entity_id") or "").strip()
        label = str(item.get("label") or "").strip() or sid
        rows = loader(data_key, entity_id=entity_id)
        points_raw = extract_field_points(
            rows, field, start_date=start, end_date=end
        )
        if fill == "ffill":
            points_raw = _ffill_on_union(points_raw, start=start, end=end)
        points = normalize_points(points_raw, normalize)
        for point in points:
            calendar.add(str(point["date"]))
        series_out.append({"id": sid, "label": label, "points": points})
        dates = [str(p["date"]) for p in points]
        meta_series.append(
            {
                "id": sid,
                "data_key": data_key,
                "entity_id": entity_id,
                "field": field,
                "label": label,
                "scope": str(item.get("scope") or "").strip(),
                "point_count": len(points),
                "date_min": dates[0] if dates else "",
                "date_max": dates[-1] if dates else "",
            }
        )

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
        "notes": [
            "统计在两两日期交集上计算；图为日期并集连点。",
        ],
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
    """仅在已有观测的首尾之间按日字符串枚举不现实；ffill 只在「已出现过的日历并集」上不适用。

    第一版：保持原 points（ffill 完整实现需全局日历）。显式 fill=ffill 时仍返回原点，
    避免伪造；后续若有交易日历再补。
    """
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
    for item in meta.get("series") or []:
        lines.append(
            f"- `{item.get('id')}` {item.get('label')}: "
            f"n={item.get('point_count')} "
            f"[{item.get('date_min')} .. {item.get('date_max')}]"
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
        lines.append(
            f"  - 样本 overlap_n={row.get('overlap_n')} "
            f"reliable={row.get('reliable')} "
            f"β(B|A)={_fmt(row.get('beta_b_on_a'))}"
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


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


__all__ = ["run_relation"]
