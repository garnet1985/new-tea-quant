"""Workbench run / step weighted progress (UI envelope)."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


class WorkbenchStepProgress:
    """Stage weights and labels for workbench run progress UI."""

    STAGES: Tuple[str, ...] = ("load", "dispatch", "execute", "report")

    STEP_STAGE_WEIGHTS: Dict[str, Dict[str, float]] = {
        "enum": {"load": 0.05, "dispatch": 0.03, "execute": 0.9, "report": 0.02},
        "price": {"load": 0.1, "dispatch": 0.03, "execute": 0.85, "report": 0.02},
        "portfolio": {"load": 0.2, "dispatch": 0.1, "execute": 0.6, "report": 0.1},
    }

    STAGE_LABELS: Dict[str, str] = {
        "load": "加载数据",
        "dispatch": "调度任务",
        "execute": "回测中",
        "report": "生成报告",
    }

    @staticmethod
    def _clamp01(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @classmethod
    def step_stage_weights(cls, substep: str) -> Dict[str, float]:
        sub = str(substep or "").strip()
        return dict(cls.STEP_STAGE_WEIGHTS.get(sub, cls.STEP_STAGE_WEIGHTS["price"]))

    @classmethod
    def stage_label(cls, stage: str) -> str:
        st = str(stage or "").strip()
        return cls.STAGE_LABELS.get(st, st)

    @classmethod
    def compute_step_progress_pct(
        cls,
        substep: str,
        stage: str,
        stage_ratio: float = 0.0,
    ) -> float:
        weights = cls.step_stage_weights(substep)
        st = str(stage or "").strip()
        ratio = cls._clamp01(stage_ratio)
        acc = 0.0
        seen = False
        for name in cls.STAGES:
            w = float(weights.get(name) or 0.0)
            if name == st:
                acc += w * ratio
                seen = True
                break
            acc += w
        if not seen and st:
            acc = sum(float(weights.get(n) or 0.0) for n in cls.STAGES)
        return round(max(0.0, min(100.0, acc * 100.0)), 2)

    @classmethod
    def compute_run_progress(
        cls,
        step_names: Sequence[str],
        steps: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        names = [str(n).strip() for n in step_names if str(n).strip()]
        n = max(len(names), 1)
        by_name: Dict[str, Mapping[str, Any]] = {}
        for row in steps:
            nm = str(row.get("step_name") or "").strip()
            if nm:
                by_name[nm] = row

        total = 0.0
        current_name = ""
        current_label = ""
        counter_text = ""
        for nm in names:
            row = by_name.get(nm) or {}
            status = str(row.get("status") or "").strip().lower()
            try:
                pct = float(row.get("progress") or 0.0)
            except (TypeError, ValueError):
                pct = 0.0
            if status == "completed":
                total += 100.0
            elif status == "failed":
                total += 100.0
            else:
                total += max(0.0, min(100.0, pct))
                if status == "running" and not current_name:
                    current_name = nm
                    current_label = str(
                        row.get("stage_label")
                        or cls.stage_label(str(row.get("stage") or ""))
                    )
                    counters = row.get("counters")
                    if isinstance(counters, dict):
                        done = counters.get("done")
                        tot = counters.get("total")
                        if done is not None and tot is not None:
                            counter_text = f"{done}/{tot}"

        pct = round(total / n, 2)
        return {
            "pct": pct,
            "label": current_name or (names[-1] if names else ""),
            "substep": current_name,
            "substep_stage_label": current_label,
            "counter_text": counter_text,
        }


__all__ = ["WorkbenchStepProgress"]
