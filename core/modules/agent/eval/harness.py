"""分流 A/B 评测：主出口 accuracy、清单匹配、高代价错分、红线漏拦。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from core.modules.agent.core.navigator.classifier import classify_route
from core.modules.agent.core.navigator.router import Route, route
from core.modules.agent.eval.gold_set import (
    GOLD_CASES,
    TRAP_CASES,
    GoldCase,
    expected_kinds,
)


RouterFn = Callable[[str], Route]


@dataclass(frozen=True)
class EvalReport:
    name: str
    total: int
    correct: int
    accuracy: float
    queue_exact: int
    queue_exact_rate: float
    # 红线漏拦：期望含 advice/oos，预测主出口不是且清单也不含
    redline_miss: int
    false_worker: int
    missed_worker: int
    model_fail: int
    by_kind: Dict[str, Dict[str, int]]
    mistakes: List[Dict[str, str]]


def evaluate(
    *,
    name: str,
    router: Optional[RouterFn] = None,
    cases: Optional[List[GoldCase]] = None,
) -> EvalReport:
    rows = list(cases or GOLD_CASES)
    predict = router or (lambda text: route(text, provider_id="ntq", mode="regex"))
    correct = 0
    queue_exact = 0
    redline_miss = 0
    false_worker = 0
    missed_worker = 0
    model_fail = 0
    by_kind: Dict[str, Dict[str, int]] = {}
    mistakes: List[Dict[str, str]] = []

    for case in rows:
        expected = case["kind"]
        exp_q = expected_kinds(case)
        got = predict(case["text"])
        pred = str(got.kind or "")
        pred_q = list(got.queue or (pred,))
        bucket = by_kind.setdefault(expected, {"n": 0, "hit": 0})
        bucket["n"] += 1
        if pred == "__fail__" or "__fail__" in pred_q:
            model_fail += 1
            mistakes.append(
                {
                    "text": case["text"],
                    "expected": expected,
                    "exp_q": ",".join(exp_q),
                    "pred": "__fail__",
                    "pred_q": "__fail__",
                    "note": case.get("note") or "",
                }
            )
            continue
        primary_ok = pred == expected
        queue_ok = pred_q == exp_q
        if primary_ok:
            correct += 1
            bucket["hit"] += 1
        if queue_ok:
            queue_exact += 1
        if not primary_ok or not queue_ok:
            mistakes.append(
                {
                    "text": case["text"],
                    "expected": expected,
                    "exp_q": ",".join(exp_q),
                    "pred": pred,
                    "pred_q": ",".join(pred_q),
                    "note": case.get("note") or "",
                }
            )
        if _redline_missed(exp_q, pred, pred_q):
            redline_miss += 1
        if expected in {"guide", "guide_arch", "identity"} and pred == "worker":
            false_worker += 1
        if expected == "worker" and pred in {"guide", "guide_arch", "identity"}:
            missed_worker += 1

    total = len(rows)
    scored = max(0, total - model_fail)
    return EvalReport(
        name=name,
        total=total,
        correct=correct,
        accuracy=(correct / scored) if scored else 0.0,
        queue_exact=queue_exact,
        queue_exact_rate=(queue_exact / scored) if scored else 0.0,
        redline_miss=redline_miss,
        false_worker=false_worker,
        missed_worker=missed_worker,
        model_fail=model_fail,
        by_kind=by_kind,
        mistakes=mistakes,
    )


def model_only_router(provider_id: str) -> RouterFn:
    """live 对照：纯模型输出（无正则加严/回退），失败记 ``__fail__``。"""

    def _predict(text: str) -> Route:
        from core.modules.agent.core.navigator.router import _route_from_kinds

        kinds = classify_route(text, provider_id=provider_id)
        if not kinds:
            return Route(kind="__fail__", queue=("__fail__",))
        return _route_from_kinds(kinds)

    return _predict


def _redline_missed(exp_q: Sequence[str], pred: str, pred_q: Sequence[str]) -> bool:
    need = [k for k in exp_q if k in {"advice", "out_of_scope"}]
    if not need:
        return False
    have = set(pred_q) | {pred}
    return any(k not in have for k in need)


def worker_recall(report: EvalReport) -> float:
    bucket = report.by_kind.get("worker") or {"n": 0, "hit": 0}
    n = int(bucket.get("n") or 0)
    hit = int(bucket.get("hit") or 0)
    return (hit / n) if n else 0.0


def format_report(report: EvalReport) -> str:
    lines = [
        f"[{report.name}] n={report.total} scored={report.total - report.model_fail} "
        f"primary_acc={report.accuracy:.1%} "
        f"queue_exact={report.queue_exact_rate:.1%} "
        f"redline_miss={report.redline_miss} "
        f"false_worker={report.false_worker} missed_worker={report.missed_worker} "
        f"model_fail={report.model_fail} "
        f"worker_recall={worker_recall(report):.1%}",
    ]
    for kind, bucket in sorted(report.by_kind.items()):
        lines.append(f"  {kind}: {bucket['hit']}/{bucket['n']}")
    if report.mistakes:
        lines.append("  mistakes:")
        for row in report.mistakes[:16]:
            lines.append(
                f"    exp={row['exp_q']} pred={row['pred_q']} | {row['text'][:44]}"
            )
    return "\n".join(lines)


def run_ab(
    *,
    include_live: bool = False,
    trap_only: bool = False,
    providers: Optional[List[str]] = None,
) -> List[EvalReport]:
    cases = TRAP_CASES if trap_only else GOLD_CASES
    label = "trap" if trap_only else "full"
    reports = [
        evaluate(
            name=f"A0_regex_{label}",
            router=lambda t: route(t, provider_id="ntq", mode="regex"),
            cases=cases,
        ),
    ]
    if include_live:
        pids = list(providers or ["ntq"])
        for pid in pids:
            reports.append(
                evaluate(
                    name=f"{pid}_{label}",
                    router=model_only_router(pid),
                    cases=cases,
                )
            )
    return reports


if __name__ == "__main__":
    import sys

    live = "--live" in sys.argv
    trap_only = "--trap" in sys.argv
    providers: Optional[List[str]] = None
    for arg in sys.argv[1:]:
        if arg.startswith("--providers="):
            providers = [p.strip() for p in arg.split("=", 1)[1].split(",") if p.strip()]
    for report in run_ab(
        include_live=live, trap_only=trap_only, providers=providers
    ):
        print(format_report(report))
        print()
    if not live:
        print(
            "hint: --live [--trap] [--providers=ntq|zhipu,deepseek] "
            "to score classifiers"
        )
