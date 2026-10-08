"""枚举层出场比率：轻扫 ``enum/entities/*.json`` 的 ``results[]``。"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore

_STOP = frozenset({"stop_loss", "dynamic_loss"})
_TAKE = frozenset({"take_profit"})
_EXPIRE = frozenset(
    {"simulate_end", "expiration", "expire", "expired", "time_stop", "timeout"}
)


def exit_ratios_for_version(folder: Path, version_id: str) -> Dict[str, Any]:
    """返回 stop_loss / take_profit / expire 占比与均持有天数。"""
    rows = _load_results(folder, version_id)
    return ratios_from_results(rows)


def baseline_exit_diagnosis(
    folder: Path,
    version_id: str,
    *,
    top_n: int = 5,
) -> Dict[str, Any]:
    """主 version：按票 / 按月的止损集中度（基准诊断）。"""
    rows = _load_results(folder, version_id)
    if not rows:
        return {
            "version_id": str(version_id or "").strip(),
            "n": 0,
            "high_stop_loss_stocks": [],
            "stop_loss_by_month": [],
            "exit_counts": {},
        }
    by_stock: Dict[str, Counter] = defaultdict(Counter)
    by_month: Dict[str, Counter] = defaultdict(Counter)
    total = Counter()
    names: Dict[str, str] = {}
    for row in rows:
        reason = _bucket(str(row.get("exit_reason") or ""))
        eid = str(row.get("entity_id") or "").strip() or "?"
        names[eid] = str(row.get("stock_name") or eid).strip() or eid
        by_stock[eid][reason] += 1
        month = _month_key(str(row.get("trigger_date") or row.get("exit_date") or ""))
        if month:
            by_month[month][reason] += 1
        total[reason] += 1

    stock_rows: List[Dict[str, Any]] = []
    for eid, counts in by_stock.items():
        n = sum(counts.values())
        if n <= 0:
            continue
        sl = int(counts.get("stop_loss") or 0)
        stock_rows.append(
            {
                "entity_id": eid,
                "stock_name": names.get(eid, eid),
                "n": n,
                "stop_loss": sl,
                "stop_loss_ratio": round(sl / float(n), 4),
                "take_profit": int(counts.get("take_profit") or 0),
                "expire": int(counts.get("expire") or 0),
            }
        )
    stock_rows.sort(
        key=lambda item: (
            -float(item.get("stop_loss_ratio") or 0.0),
            -int(item.get("stop_loss") or 0),
            -int(item.get("n") or 0),
        )
    )
    month_rows: List[Dict[str, Any]] = []
    for month, counts in sorted(by_month.items()):
        n = sum(counts.values())
        if n <= 0:
            continue
        sl = int(counts.get("stop_loss") or 0)
        month_rows.append(
            {
                "month": month,
                "n": n,
                "stop_loss": sl,
                "stop_loss_ratio": round(sl / float(n), 4),
                "take_profit": int(counts.get("take_profit") or 0),
                "expire": int(counts.get("expire") or 0),
            }
        )
    month_rows.sort(
        key=lambda item: (
            -float(item.get("stop_loss_ratio") or 0.0),
            -int(item.get("stop_loss") or 0),
        )
    )
    return {
        "version_id": str(version_id or "").strip(),
        "n": len(rows),
        "exit_counts": dict(total),
        "high_stop_loss_stocks": [
            item
            for item in stock_rows
            if int(item.get("stop_loss") or 0) > 0
        ][: max(1, int(top_n))],
        "stop_loss_by_month": month_rows[: max(1, int(top_n))],
    }


def after_take_profit_probe(
    folder: Path,
    version_id: str,
    effective_settings: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """止盈后还有没有涨：仅当分档或动态止盈真跑过。"""
    available, reason = _tp_probe_available(effective_settings)
    if not available:
        return {
            "available": False,
            "reason": reason,
            "facts": [],
            "conclusion": reason,
            "suggestion": "要测止盈后走势，请在 goal.take_profit 加分档（勿一档全平），或打开 dynamic_loss。",
        }
    rows = _load_results(folder, version_id)
    stage_hits: Counter = Counter()
    multi_stage = 0
    for row in rows:
        goals = row.get("completed_goals")
        if not isinstance(goals, list) or not goals:
            continue
        names = [
            str(item.get("name") or item.get("reason") or "").strip()
            for item in goals
            if isinstance(item, dict)
        ]
        names = [name for name in names if name]
        if len(names) >= 2:
            multi_stage += 1
        for name in names:
            stage_hits[name] += 1
    facts = [
        f"扫描 {len(rows)} 笔机会，其中 {multi_stage} 笔触达两档及以上止盈。",
    ]
    if stage_hits:
        top = ", ".join(
            f"{name}×{count}"
            for name, count in stage_hits.most_common(4)
        )
        facts.append(f"档位触达：{top}。")
    conclusion = (
        "分档/动态止盈有触达记录，可看 completed_goals 判断后面是否还有涨。"
        if multi_stage or stage_hits
        else "设置允许探测止盈后路径，但本版几乎没有多档触达。"
    )
    return {
        "available": True,
        "reason": "",
        "facts": facts,
        "conclusion": conclusion,
        "suggestion": "在 inputs 里对照「全平」与「分档/动态」的触达差异。",
        "multi_stage_hits": multi_stage,
        "stage_hits": dict(stage_hits),
    }


def ratios_from_results(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    if n <= 0:
        return {
            "stop_loss_ratio": None,
            "take_profit_ratio": None,
            "expire_ratio": None,
            "avg_holding_days_stop_loss": None,
            "avg_holding_days_take_profit": None,
            "n_exits": 0,
        }
    buckets = Counter()
    hold_stop: List[float] = []
    hold_tp: List[float] = []
    for row in rows:
        bucket = _bucket(str(row.get("exit_reason") or ""))
        buckets[bucket] += 1
        try:
            days = float(row.get("holding_days") or 0)
        except (TypeError, ValueError):
            days = 0.0
        if bucket == "stop_loss" and days > 0:
            hold_stop.append(days)
        if bucket == "take_profit" and days > 0:
            hold_tp.append(days)
    return {
        "stop_loss_ratio": round(buckets.get("stop_loss", 0) / float(n), 4),
        "take_profit_ratio": round(buckets.get("take_profit", 0) / float(n), 4),
        "expire_ratio": round(buckets.get("expire", 0) / float(n), 4),
        "avg_holding_days_stop_loss": (
            round(sum(hold_stop) / len(hold_stop), 2) if hold_stop else None
        ),
        "avg_holding_days_take_profit": (
            round(sum(hold_tp) / len(hold_tp), 2) if hold_tp else None
        ),
        "n_exits": n,
    }


def _load_results(folder: Path, version_id: str) -> List[Dict[str, Any]]:
    vid = str(version_id or "").strip()
    if not vid:
        return []
    try:
        store = ArtifactStore.resolve(
            folder, kind=SimulateKind.ENUMERATE, version_id=vid
        )
    except FileNotFoundError:
        return []
    entities_dir = store.entities_dir()
    if not entities_dir.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(entities_dir.glob("*.json")):
        try:
            payload = store.read_json(f"entities/{path.name}")
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        eid = str(payload.get("entity_id") or path.stem).strip()
        for row in payload.get("results") or []:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item.setdefault("entity_id", eid)
            out.append(item)
    return out


def _bucket(reason: str) -> str:
    key = str(reason or "").strip().lower()
    if key in _STOP:
        return "stop_loss"
    if key in _TAKE:
        return "take_profit"
    if key in _EXPIRE:
        return "expire"
    if not key:
        return "other"
    return "other"


def _month_key(raw: str) -> str:
    text = str(raw or "").strip().replace("-", "")
    if len(text) >= 6 and text[:6].isdigit():
        return f"{text[:4]}-{text[4:6]}"
    return ""


def _tp_probe_available(
    effective_settings: Optional[Mapping[str, Any]],
) -> Tuple[bool, str]:
    goal = (
        effective_settings.get("goal")
        if isinstance(effective_settings, Mapping)
        else None
    )
    if not isinstance(goal, Mapping):
        return False, "读不到 goal 设置，无法判断能否测止盈后走势。"
    if goal.get("dynamic_loss") not in (None, False, {}, []):
        return True, ""
    tp = goal.get("take_profit")
    stages: List[Any] = []
    if isinstance(tp, Mapping):
        stages = list(tp.get("stages") or [])
    elif isinstance(tp, list):
        stages = list(tp)
    if len(stages) >= 2:
        return True, ""
    if len(stages) == 1 and isinstance(stages[0], Mapping):
        stage = stages[0]
        close_invest = stage.get("close_invest")
        actions = stage.get("actions") or []
        if isinstance(actions, list) and any(
            str(a).strip() == "set_dynamic_loss" for a in actions
        ):
            return True, ""
        if close_invest is False:
            return True, ""
        exit_ratio = stage.get("exit_ratio")
        try:
            if exit_ratio is not None and float(exit_ratio) < 1.0:
                return True, ""
        except (TypeError, ValueError):
            pass
    return (
        False,
        "当前是一档全平止盈，同一次回测看不到止盈后走势。",
    )


__all__ = [
    "after_take_profit_probe",
    "baseline_exit_diagnosis",
    "exit_ratios_for_version",
    "ratios_from_results",
]
