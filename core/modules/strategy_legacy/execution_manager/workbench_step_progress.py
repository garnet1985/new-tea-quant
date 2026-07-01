"""工作台 run / step 加权进度：load → dispatch → execute → report。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

STAGES: Tuple[str, ...] = ("load", "dispatch", "execute", "report")

STEP_STAGE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "enum": {"load": 0.05, "dispatch": 0.03, "execute": 0.9, "report": 0.02},
    "price": {"load": 0.1, "dispatch": 0.03, "execute": 0.85, "report": 0.02},
    "capital": {"load": 0.2, "dispatch": 0.1, "execute": 0.6, "report": 0.1},
}

STEP_LABELS: Dict[str, str] = {
    "enum": "机会枚举",
    "price": "价格因子回测",
    "capital": "资金分配回测",
}

STAGE_LABELS: Dict[str, str] = {
    "load": "加载数据",
    "dispatch": "调度任务",
    "execute": "回测中",
    "report": "生成报告",
}


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def step_stage_weights(substep: str) -> Dict[str, float]:
    sub = str(substep or "").strip()
    return dict(STEP_STAGE_WEIGHTS.get(sub, STEP_STAGE_WEIGHTS["price"]))


def step_label(substep: str) -> str:
    sub = str(substep or "").strip()
    return STEP_LABELS.get(sub, sub)


def stage_label(stage: str) -> str:
    st = str(stage or "").strip()
    return STAGE_LABELS.get(st, st)


def compute_step_progress_pct(
    substep: str,
    stage: str,
    stage_ratio: float = 0.0,
) -> float:
    """单步 0～100：已完成阶段权重 + 当前阶段权重 × ratio。"""
    weights = step_stage_weights(substep)
    st = str(stage or "").strip()
    ratio = _clamp01(stage_ratio)
    acc = 0.0
    seen = False
    for name in STAGES:
        w = float(weights.get(name) or 0.0)
        if name == st:
            acc += w * ratio
            seen = True
            break
        acc += w
    if not seen and st:
        acc = sum(float(weights.get(n) or 0.0) for n in STAGES)
    return round(max(0.0, min(100.0, acc * 100.0)), 2)


def compute_run_progress(
    step_names: Sequence[str],
    steps: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """整次 run 0～100 与当前子步摘要。"""
    names = [str(n).strip() for n in step_names if str(n).strip()]
    n = max(len(names), 1)
    by_name: Dict[str, Mapping[str, Any]] = {}
    for row in steps:
        nm = str(row.get("step_name") or "").strip()
        if nm:
            by_name[nm] = row

    completed = 0
    running_name = ""
    running_row: Optional[Mapping[str, Any]] = None
    for nm in names:
        row = by_name.get(nm) or {}
        st = str(row.get("status") or "").strip().lower()
        if st == "completed":
            completed += 1
        elif st == "running":
            running_name = nm
            running_row = row
            break

    slice_w = 100.0 / n
    pct = float(completed) * slice_w
    if running_name and running_row is not None:
        try:
            sp = float(running_row.get("progress") or 0)
        except (TypeError, ValueError):
            sp = 0.0
        pct += slice_w * _clamp01(sp / 100.0)
    elif completed >= len(names) and names:
        pct = 100.0

    idx = names.index(running_name) + 1 if running_name in names else max(completed, 1)
    stage = str((running_row or {}).get("stage") or "").strip()
    counters = (running_row or {}).get("counters")
    counter_txt = ""
    if isinstance(counters, dict):
        try:
            done = int(counters.get("done") or 0)
            total = int(counters.get("total") or 0)
        except (TypeError, ValueError):
            done, total = 0, 0
        if total > 0:
            counter_txt = f"{done}/{total}"

    label = step_label(running_name) if running_name else ""
    if not label and names:
        label = step_label(names[min(completed, len(names) - 1)])

    return {
        "pct": round(max(0.0, min(100.0, pct)), 2),
        "label": label,
        "step_index": idx if running_name else max(completed, 1),
        "step_total": len(names) if names else 1,
        "substep": running_name,
        "substep_stage": stage,
        "substep_stage_label": stage_label(stage) if stage else "",
        "counters": counters if isinstance(counters, dict) else None,
        "counter_text": counter_txt,
    }


__all__ = [
    "STAGES",
    "STAGE_LABELS",
    "STEP_LABELS",
    "STEP_STAGE_WEIGHTS",
    "compute_run_progress",
    "compute_step_progress_pct",
    "stage_label",
    "step_label",
    "step_stage_weights",
]
