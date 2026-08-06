"""Scale-ladder summary: fit T≈T0+kN, doubling deltas, write OVERALL.md."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common import (
    REPORTS_DIR,
    be_module_version,
    report_engine_dirname,
    report_mode_dir,
    utc_now_iso,
)

_N_DIR_RE = re.compile(r"^N(\d+)$")


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _fit_linear(ns: List[float], ts: List[float]) -> Tuple[Optional[float], Optional[float]]:
    """Least-squares T = T0 + k·N. Returns (T0, k)."""
    if len(ns) < 2 or len(ns) != len(ts):
        return None, None
    n = float(len(ns))
    sum_n = sum(ns)
    sum_t = sum(ts)
    sum_nn = sum(x * x for x in ns)
    sum_nt = sum(a * b for a, b in zip(ns, ts))
    den = n * sum_nn - sum_n * sum_n
    if abs(den) < 1e-12:
        return None, None
    k = (n * sum_nt - sum_n * sum_t) / den
    t0 = (sum_t - k * sum_n) / n
    return t0, k


def _pct_change(new: float, old: float) -> Optional[float]:
    if old == 0:
        return None
    return (new - old) / old * 100.0


def _load_scale_points(mode_dir: Path, *, engine_dir: str) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    if not mode_dir.is_dir():
        return points
    for child in sorted(mode_dir.iterdir()):
        m = _N_DIR_RE.match(child.name)
        if not m:
            continue
        metrics_path = child / engine_dir / "metrics.json"
        if not metrics_path.is_file():
            continue
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        met = dict(payload.get("metrics") or {})
        ts = dict(met.get("time_split") or {})
        n = int(met.get("entities") or m.group(1))
        wall = _safe_float(met.get("wall_time_s"))
        thr = _safe_float(met.get("throughput_entity_day_per_s"))
        days = int(met.get("timeline_points") or 0)
        if wall is None or wall <= 0 or n <= 0:
            continue
        points.append(
            {
                "n": n,
                "wall": wall,
                "throughput": thr,
                "days": days,
                "rows": int(met.get("data_rows") or n * days),
                "planning_sec": _safe_float(ts.get("planning_sec")),
                "load_sec": _safe_float(ts.get("load_sec")),
                "compute_sec": _safe_float(ts.get("compute_sec")),
                "success": bool(met.get("success")),
                "path": str(metrics_path.parent),
            }
        )
    points.sort(key=lambda p: p["n"])
    return points


def analyze_points(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive T0/k, doubling deltas, and a one-line trend verdict."""
    if len(points) < 2:
        return {
            "points": points,
            "t0": None,
            "k": None,
            "doubling": [],
            "verdict": "样本档不足（至少 2 档）",
            "fixed_share": [],
            "near_fixed": None,
            "near_linear": None,
        }

    ns = [float(p["n"]) for p in points]
    ts = [float(p["wall"]) for p in points]
    t0, k = _fit_linear(ns, ts)

    doubling: List[Dict[str, Any]] = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        if a["n"] <= 0:
            continue
        ratio_n = b["n"] / a["n"]
        wall_ratio = b["wall"] / a["wall"] if a["wall"] else None
        thr_a = a.get("throughput")
        thr_b = b.get("throughput")
        thr_pct = (
            _pct_change(float(thr_b), float(thr_a))
            if thr_a and thr_b
            else None
        )
        # Ideal linear wall for this N jump: wall_b ≈ wall_a * (Nb/Na) if T0=0
        expected_linear_wall_ratio = ratio_n
        doubling.append(
            {
                "from_n": a["n"],
                "to_n": b["n"],
                "n_ratio": round(ratio_n, 3),
                "wall_ratio": round(wall_ratio, 3) if wall_ratio is not None else None,
                "throughput_pct": round(thr_pct, 1) if thr_pct is not None else None,
                "vs_linear_wall": (
                    round(wall_ratio / expected_linear_wall_ratio, 3)
                    if wall_ratio is not None and expected_linear_wall_ratio
                    else None
                ),
            }
        )

    fixed_share: List[Dict[str, Any]] = []
    if t0 is not None:
        for p in points:
            share = (t0 / p["wall"] * 100.0) if p["wall"] > 0 else None
            fixed_share.append(
                {
                    "n": p["n"],
                    "t0_share_pct": round(share, 1) if share is not None else None,
                }
            )

    # Phase character: planning ~flat → near-fixed; (load+compute)/N ~stable → near-linear
    plans = [p["planning_sec"] for p in points if p.get("planning_sec") is not None]
    var_costs = []
    for p in points:
        load = p.get("load_sec") or 0.0
        comp = p.get("compute_sec") or 0.0
        var_costs.append((load + comp) / p["n"] if p["n"] else None)

    near_fixed = None
    if len(plans) >= 2:
        mean_p = sum(plans) / len(plans)
        spread = max(plans) - min(plans)
        near_fixed = {
            "label": "准备/规划",
            "mean_sec": round(mean_p, 4),
            "spread_sec": round(spread, 4),
            "looks_fixed": bool(mean_p > 0 and spread <= max(0.05, 0.5 * mean_p)),
        }

    near_linear = None
    clean_v = [v for v in var_costs if v is not None and v > 0]
    if len(clean_v) >= 2:
        mean_v = sum(clean_v) / len(clean_v)
        spread_v = max(clean_v) - min(clean_v)
        near_linear = {
            "label": "读数据+推进（每股票）",
            "mean_sec_per_stock": round(mean_v, 6),
            "spread_sec_per_stock": round(spread_v, 6),
            "looks_linear": bool(mean_v > 0 and spread_v <= 0.35 * mean_v),
        }

    thr_list = [p.get("throughput") for p in points if p.get("throughput")]
    verdict = "档位不足以下结论"
    if len(thr_list) >= 2:
        first, last = float(thr_list[0]), float(thr_list[-1])
        pct = _pct_change(last, first) or 0.0
        if pct >= 8:
            verdict = (
                f"越大吞吐越高（首→末 +{pct:.0f}%）：固定成本被摊薄，或并行更吃得开"
            )
        elif pct <= -8:
            verdict = (
                f"越大越慢（首→末 {pct:.0f}%）：可能争用、片宽变化或内存压力"
            )
        else:
            verdict = (
                f"吞吐随规模大致持平（首→末 {pct:+.0f}%）：接近线性边际成本"
            )

    return {
        "points": points,
        "t0": round(t0, 4) if t0 is not None else None,
        "k": round(k, 6) if k is not None else None,
        "doubling": doubling,
        "verdict": verdict,
        "fixed_share": fixed_share,
        "near_fixed": near_fixed,
        "near_linear": near_linear,
    }


def _fmt_thr(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if v >= 1000:
        return f"{v/1000:.1f}k"
    return f"{v:.0f}"


def render_overall_markdown(
    *,
    mode: str,
    mode_label: str,
    be_version: str,
    by_engine: Dict[str, Dict[str, Any]],
) -> str:
    lines: List[str] = [
        f"# 性能总览 — {mode_label}",
        "",
        f"- 生成时间: {utc_now_iso()}",
        f"- BE: {be_version}",
        f"- 模式: {mode}",
        "- 模型: 墙钟 T ≈ T0 + k·N（N=股票数，交易日固定）",
        "",
        "## 结论（先看这）",
        "",
    ]
    if not by_engine:
        lines.append("- 尚无分档报告（需要 `N{{size}}/{{db}}/metrics.json`）。")
        lines.append("")
        return "\n".join(lines)

    for eng, ana in by_engine.items():
        lines.append(f"- **{eng}**: {ana.get('verdict')}")
    lines.extend(["", "## 分库明细", ""])

    for eng, ana in by_engine.items():
        pts: List[Dict[str, Any]] = list(ana.get("points") or [])
        lines.append(f"### {eng}")
        lines.append("")
        lines.append("| N | 墙钟(s) | 吞吐(ed/s) | 准备 | 读数据 | 推进 |")
        lines.append("|--:|--:|--:|--:|--:|--:|")
        for p in pts:
            lines.append(
                f"| {p['n']} | {p['wall']:.2f} | {_fmt_thr(p.get('throughput'))} | "
                f"{(p.get('planning_sec') if p.get('planning_sec') is not None else 0):.2f} | "
                f"{(p.get('load_sec') if p.get('load_sec') is not None else 0):.2f} | "
                f"{(p.get('compute_sec') if p.get('compute_sec') is not None else 0):.2f} |"
            )
        lines.append("")

        t0, k = ana.get("t0"), ana.get("k")
        if t0 is not None and k is not None:
            lines.append(f"- 拟合: T ≈ {t0:.3f} + {k:.5f}·N 秒")
            share_tail = ""
            fs = list(ana.get("fixed_share") or [])
            if fs and fs[-1].get("t0_share_pct") is not None:
                share_tail = (
                    f"（在 N={pts[-1]['n']} 约占 {fs[-1]['t0_share_pct']}%）"
                )
            lines.append(f"- 固定成本 T0: **{t0:.3f}s**{share_tail}")
            lines.append(
                f"- 边际成本 k: **{k*1000:.2f} ms/股**（含该股全部交易日）"
            )
        else:
            lines.append("- 拟合: 档位不足")

        nf = ana.get("near_fixed")
        if nf:
            flag = "像固定成本" if nf.get("looks_fixed") else "随规模有波动"
            lines.append(
                f"- 近固定: {nf['label']} 均值 {nf['mean_sec']}s、"
                f"极差 {nf['spread_sec']}s → {flag}"
            )
        nl = ana.get("near_linear")
        if nl:
            flag = "像按股线性" if nl.get("looks_linear") else "每股票成本不稳定"
            lines.append(
                f"- 近线性: {nl['label']} 均值 {nl['mean_sec_per_stock']:.4f}s/股、"
                f"极差 {nl['spread_sec_per_stock']:.4f} → {flag}"
            )

        dubs = list(ana.get("doubling") or [])
        if dubs:
            lines.append("- 样本翻倍附近（吞吐变化可为负）:")
            for d in dubs:
                thr = d.get("throughput_pct")
                thr_s = f"{thr:+.1f}%" if thr is not None else "—"
                wr = d.get("wall_ratio")
                wr_s = f"{wr:.2f}×" if wr is not None else "—"
                lines.append(
                    f"  - N{d['from_n']}→N{d['to_n']}: "
                    f"墙钟 {wr_s}（理想线性约 {d['n_ratio']:.2f}×），"
                    f"吞吐 {thr_s}"
                )
        lines.append("")

    lines.extend(
        [
            "## 怎么读",
            "",
            "- 吞吐随 N **上升**：固定成本被摊薄（「越大越划算」）。",
            "- 吞吐大致 **持平**：墙钟近似按股线性。",
            "- 吞吐 **下降**：越大越慢，查调度/IO/内存/片宽。",
            "- T0 是 sink（进程、规划、采样等）；占比随 N 变大应下降。",
            "- entity 与 slice 分看，不要横比谁更快。",
            "",
        ]
    )
    return "\n".join(lines)


def write_overall_report(
    *,
    mode: str,
    mode_label: str,
    be_version: Optional[str] = None,
    engines: Optional[List[str]] = None,
) -> Path:
    """Scan N*/{db} metrics under mode dir; write OVERALL.md."""
    ver = str(be_version or be_module_version())
    mode_dir = report_mode_dir(be_version=ver, mode=mode)
    mode_dir.mkdir(parents=True, exist_ok=True)

    eng_dirs = engines or ["duckdb", "mysql", "pgsql"]
    by_engine: Dict[str, Dict[str, Any]] = {}
    for eng in eng_dirs:
        # normalize alias
        eng_dir = report_engine_dirname(eng)
        pts = _load_scale_points(mode_dir, engine_dir=eng_dir)
        if not pts:
            continue
        by_engine[eng_dir] = analyze_points(pts)

    text = render_overall_markdown(
        mode=mode,
        mode_label=mode_label,
        be_version=ver,
        by_engine=by_engine,
    )
    out = mode_dir / "OVERALL.md"
    out.write_text(text, encoding="utf-8")

    # machine-readable companion
    payload = {
        "generated_at": utc_now_iso(),
        "be_version": ver,
        "mode": mode,
        "engines": {
            eng: {
                "t0": ana.get("t0"),
                "k": ana.get("k"),
                "verdict": ana.get("verdict"),
                "doubling": ana.get("doubling"),
                "fixed_share": ana.get("fixed_share"),
                "near_fixed": ana.get("near_fixed"),
                "near_linear": ana.get("near_linear"),
                "points": [
                    {
                        "n": p["n"],
                        "wall": p["wall"],
                        "throughput": p.get("throughput"),
                        "planning_sec": p.get("planning_sec"),
                        "load_sec": p.get("load_sec"),
                        "compute_sec": p.get("compute_sec"),
                    }
                    for p in (ana.get("points") or [])
                ],
            }
            for eng, ana in by_engine.items()
        },
    }
    (mode_dir / "OVERALL.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def discover_report_versions() -> List[str]:
    if not REPORTS_DIR.is_dir():
        return []
    out = []
    for p in REPORTS_DIR.iterdir():
        if p.is_dir() and re.match(r"^\d+\.\d+", p.name):
            out.append(p.name)
    return sorted(out)
