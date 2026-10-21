"""两两关系：核心 = 相关 + 领先滞后 + 幅度系数；其余为补充。"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# 交集至少这么多点才报「可靠」相关/滞后
MIN_OVERLAP_RELIABLE = 20
# 低于此不报相关数字
MIN_OVERLAP_REPORT = 8
# |corr| 低于此视为弱相关
WEAK_CORR = 0.2
# 默认滚动窗（交集有序点个数，非自然日）
DEFAULT_ROLL_WINDOW = 60


def pairwise_summary(
    series_payload: Sequence[Mapping[str, Any]],
    *,
    max_lag: int = 20,
    roll_window: int = DEFAULT_ROLL_WINDOW,
    labels: Optional[Mapping[str, str]] = None,
) -> List[Dict[str, Any]]:
    """``points`` 含 ``date`` / ``norm``（形状）与 ``raw``（幅度系数）。"""
    name_of = dict(labels or {})
    by_norm: Dict[str, Dict[str, float]] = {}
    by_raw: Dict[str, Dict[str, float]] = {}
    order: List[str] = []
    for item in series_payload:
        sid = str(item.get("id") or "").strip()
        if not sid:
            continue
        if sid not in name_of:
            name_of[sid] = str(item.get("label") or sid)
        norms: Dict[str, float] = {}
        raws: Dict[str, float] = {}
        for point in item.get("points") or []:
            if not isinstance(point, Mapping):
                continue
            day = str(point.get("date") or "").strip()
            if not day:
                continue
            try:
                norms[day] = float(point.get("norm"))
            except (TypeError, ValueError):
                continue
            try:
                raws[day] = float(point.get("raw"))
            except (TypeError, ValueError):
                # 无 raw 时幅度退回 norm（可解释性变差）
                raws[day] = norms[day]
        by_norm[sid] = norms
        by_raw[sid] = raws
        order.append(sid)

    rows: List[Dict[str, Any]] = []
    for i, a in enumerate(order):
        for b in order[i + 1 :]:
            rows.append(
                _pair(
                    a,
                    b,
                    by_norm[a],
                    by_norm[b],
                    by_raw[a],
                    by_raw[b],
                    max_lag=max_lag,
                    roll_window=roll_window,
                    label_a=name_of.get(a, a),
                    label_b=name_of.get(b, b),
                )
            )
    return rows


def _pair(
    a: str,
    b: str,
    left_n: Mapping[str, float],
    right_n: Mapping[str, float],
    left_r: Mapping[str, float],
    right_r: Mapping[str, float],
    *,
    max_lag: int,
    roll_window: int,
    label_a: str,
    label_b: str,
) -> Dict[str, Any]:
    common = sorted(set(left_n) & set(right_n))
    n = len(common)
    warnings: List[str] = []
    empty_core = {
        "relation_text": (
            f"{label_a} 与 {label_b}：共同有数据的日子太少，"
            f"暂时说不清是否一起动、谁先动、波动差多少。"
        ),
        "lead_text": "",
        "scale_text": "",
    }
    if n < MIN_OVERLAP_REPORT:
        warnings.append(f"交集仅 {n} 点，低于报告门槛 {MIN_OVERLAP_REPORT}")
        return {
            "a": a,
            "b": b,
            "label_a": label_a,
            "label_b": label_b,
            "overlap_n": n,
            "reliable": False,
            "pearson": None,
            "spearman": None,
            "relation": "insufficient",
            "best_lag_days": None,
            "best_lag_corr": None,
            "lead": "insufficient",
            "beta_b_on_a": None,
            "beta_a_on_b": None,
            "alpha_b_on_a": None,
            "scale_r2": None,
            "shape_ok": False,
            "core": empty_core,
            "supplement": {"rolling": None},
            "warnings": warnings,
        }

    if n < MIN_OVERLAP_RELIABLE:
        warnings.append(
            f"交集 {n} 点 < {MIN_OVERLAP_RELIABLE}，结论仅供参考"
        )

    xs_n = [left_n[d] for d in common]
    ys_n = [right_n[d] for d in common]
    raw_days = [d for d in common if d in left_r and d in right_r]
    xs_r = [left_r[d] for d in raw_days]
    ys_r = [right_r[d] for d in raw_days]

    pearson = _corr(xs_n, ys_n)
    spearman = _corr(_ranks(xs_n), _ranks(ys_n))
    relation = _relation_tag(pearson)

    best_lag = 0
    best_corr = pearson
    lag_limit = max(0, int(max_lag))
    for lag in range(-lag_limit, lag_limit + 1):
        if lag == 0:
            continue
        paired = _lag_pairs(left_n, right_n, lag)
        if len(paired) < MIN_OVERLAP_REPORT:
            continue
        px, py = zip(*paired)
        c = _corr(list(px), list(py))
        if c is None:
            continue
        if best_corr is None or abs(c) > abs(best_corr):
            best_corr = c
            best_lag = lag

    lead = _lead_tag(best_lag)
    beta_b_on_a, alpha_b_on_a, scale_r2 = _ols_alpha_beta_r2(xs_r, ys_r)
    beta_a_on_b, _, _ = _ols_alpha_beta_r2(ys_r, xs_r)

    # 形状不像时：先后/幅度仍算出数，但标不可信并改写文案
    shape_ok = relation in ("positive", "negative")
    if not shape_ok:
        warnings.append(
            "走势不太像：谁先动、波动差多少仅供参考，请优先看「同向还是反向」"
        )

    core = {
        "relation_text": _relation_text(label_a, label_b, relation, pearson, spearman),
        "lead_text": _lead_text(
            label_a, label_b, lead, best_lag, best_corr, trusted=shape_ok
        ),
        "scale_text": _scale_text(
            label_a,
            label_b,
            beta_b_on_a,
            beta_a_on_b,
            alpha_b_on_a,
            scale_r2,
            trusted=shape_ok,
        ),
    }
    rolling = _rolling_spearman(xs_n, ys_n, roll_window)
    if rolling is None and n >= MIN_OVERLAP_REPORT:
        warnings.append(
            f"交集不足以计算滚动相关（需要约 {roll_window + 5} 点）"
        )

    return {
        "a": a,
        "b": b,
        "label_a": label_a,
        "label_b": label_b,
        "overlap_n": n,
        "reliable": n >= MIN_OVERLAP_RELIABLE,
        "pearson": pearson,
        "spearman": spearman,
        "relation": relation,
        "best_lag_days": best_lag,
        "best_lag_corr": best_corr,
        "lead": lead,
        "beta_b_on_a": beta_b_on_a,
        "beta_a_on_b": beta_a_on_b,
        "alpha_b_on_a": alpha_b_on_a,
        "scale_r2": scale_r2,
        "shape_ok": shape_ok,
        "core": core,
        "supplement": {"rolling": rolling},
        "warnings": warnings,
    }


def _ols_alpha_beta_r2(
    xs: Sequence[float],
    ys: Sequence[float],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """``y ≈ alpha + beta * x`` → (beta, alpha, R²)。"""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None, None, None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x < 1e-18:
        return None, None, None
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    beta = cov / var_x
    alpha = mean_y - beta * mean_x
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot < 1e-18:
        return beta, alpha, 1.0
    ss_res = sum((y - (alpha + beta * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot
    return beta, alpha, r2


def _relation_tag(corr: Optional[float]) -> str:
    if corr is None:
        return "insufficient"
    if abs(corr) < WEAK_CORR:
        return "weak"
    return "positive" if corr > 0 else "negative"


def _lead_tag(lag: Optional[int]) -> str:
    if lag is None:
        return "insufficient"
    if lag == 0:
        return "sync"
    if lag > 0:
        return "a"
    return "b"


def _relation_text(
    label_a: str,
    label_b: str,
    relation: str,
    pearson: Optional[float],
    spearman: Optional[float],
) -> str:
    from core.modules.series_relation.core.pipeline.format_num import fmt_corr

    if relation == "insufficient" or pearson is None:
        return f"{label_a} 与 {label_b}：算不出是否同向或反向。"
    p = fmt_corr(pearson)
    s = "-" if spearman is None else fmt_corr(spearman)
    stats = f"Pearson={p}，Spearman={s}"
    if relation == "positive":
        return (
            f"{label_a} 与 {label_b}：多数时候涨跌方向一致，"
            f"更像一起上、一起下（{stats}）。"
        )
    if relation == "negative":
        return (
            f"{label_a} 与 {label_b}：多数时候涨跌方向相反，"
            f"一个往上时另一个更常往下（{stats}）。"
        )
    return (
        f"{label_a} 与 {label_b}：看不出稳定的同向或反向关系，"
        f"涨跌步调比较散（{stats}）。"
    )


def _lead_text(
    label_a: str,
    label_b: str,
    lead: str,
    lag: Optional[int],
    lag_corr: Optional[float],
    *,
    trusted: bool = True,
) -> str:
    """口径：best_lag>0 表示 a 领先 b。"""
    from core.modules.series_relation.core.pipeline.format_num import fmt_corr

    if lead == "insufficient" or lag is None:
        return f"{label_a} 与 {label_b}：说不清谁更早动。"
    c = "-" if lag_corr is None else fmt_corr(lag_corr)
    days = abs(int(lag))
    caution = "" if trusted else "走势不太像，这条请谨慎看待。"
    caveat = "只是时间先后的统计，不能说明谁带动谁。"
    if lead == "sync":
        body = (
            f"{label_a} 与 {label_b}：起伏大致同步，没有明显谁先谁后"
            f"（最佳滞后 0 日，滞后相关={c}）。"
        )
        return f"{caution}{body}".strip()
    if lead == "a":
        body = (
            f"{label_a} 往往更早动，{label_b} 大约晚 {days} 天出现类似走势"
            f"（best_lag=+{days}，滞后相关={c}）。{caveat}"
        )
        return f"{caution}{body}".strip()
    body = (
        f"{label_b} 往往更早动，{label_a} 大约晚 {days} 天出现类似走势"
        f"（best_lag=-{days}，滞后相关={c}）。{caveat}"
    )
    return f"{caution}{body}".strip()


def _scale_text(
    label_a: str,
    label_b: str,
    beta_b_on_a: Optional[float],
    beta_a_on_b: Optional[float],
    alpha: Optional[float],
    r2: Optional[float],
    *,
    trusted: bool = True,
) -> str:
    """纵轴幅度：原始值上 B ≈ α + β·A。"""
    from core.modules.series_relation.core.pipeline.format_num import fmt_coef, fmt_corr

    if beta_b_on_a is None:
        return (
            f"{label_a} 与 {label_b}：波动大小比不出来"
            f"（方差过小或样本不足）。"
        )
    r2_s = "-" if r2 is None else fmt_corr(r2)
    inv_s = "-" if beta_a_on_b is None else fmt_coef(beta_a_on_b)
    alpha_s = "-" if alpha is None else fmt_coef(alpha)
    beta = float(beta_b_on_a)
    abs_beta = abs(beta)
    caution = "" if trusted else "走势不太像，这条请谨慎看待。"
    caveat = "这是价格数量关系的描述，不是因果。"
    stats = f"β≈{fmt_coef(beta)}，α≈{alpha_s}，R²={r2_s}；反过来 β≈{inv_s}"
    direction = "同向" if beta >= 0 else "反向"
    mult = _human_mult(abs_beta)

    if abs(beta - 1.0) < 0.15 and (r2 or 0) >= 0.5:
        plain = (
            f"{label_b} 与 {label_a} 的涨跌幅度差不多，"
            f"更像整体平移、而不是一只大一只小（{stats}）。{caveat}"
        )
    elif abs_beta >= 1.5 or (0 < abs_beta <= 0.67):
        plain = (
            f"{label_b} 相对 {label_a} 多为{direction}波动，"
            f"幅度大约是 {label_a} 的 {mult}；"
            f"更像按倍数放大或缩小，而不是两者几乎一样大（{stats}）。{caveat}"
        )
    else:
        plain = (
            f"{label_a} 每变动约 1 个价格单位时，{label_b} 大约{direction}跟着变 "
            f"{mult}（{stats}）。{caveat}"
        )
    return f"{caution}{plain}".strip()


def _human_mult(abs_beta: float) -> str:
    """把 |β| 说成「3.30 倍」这类口语（句子里自带「大约」）。"""
    from core.modules.series_relation.core.pipeline.format_num import fmt_coef

    if abs_beta <= 0:
        return "0.00 倍"
    return f"{fmt_coef(abs_beta)} 倍"


def _rolling_spearman(
    xs: Sequence[float],
    ys: Sequence[float],
    window: int,
) -> Optional[Dict[str, Any]]:
    w = int(window)
    n = len(xs)
    if w < 5 or n < w + 5:
        return None
    series: List[float] = []
    for end in range(w, n + 1):
        c = _corr(_ranks(xs[end - w : end]), _ranks(ys[end - w : end]))
        if c is not None:
            series.append(c)
    if len(series) < 3:
        return None
    flips = 0
    for i in range(1, len(series)):
        if series[i - 1] == 0 or series[i] == 0:
            continue
        if (series[i - 1] > 0) != (series[i] > 0):
            flips += 1
    n_windows = len(series)
    max_sign_flips = max(0, n_windows - 1)
    mean = sum(series) / n_windows
    recent = series[-1]
    return {
        "window": w,
        "mean": mean,
        "recent": recent,
        "sign_flips": flips,
        "n_windows": n_windows,
        "max_sign_flips": max_sign_flips,
        "stability": _stability_tag(mean, recent, flips, max_sign_flips),
    }


def _stability_tag(
    mean: float,
    recent: float,
    flips: int,
    max_flips: int,
) -> str:
    """stable | mostly_stable | unstable — 供文案与 JSON。"""
    rate = (flips / max_flips) if max_flips > 0 else 0.0
    mean_sign = 0 if abs(mean) < 0.05 else (1 if mean > 0 else -1)
    recent_sign = 0 if abs(recent) < 0.05 else (1 if recent > 0 else -1)
    sign_broke = (
        mean_sign != 0
        and recent_sign != 0
        and mean_sign != recent_sign
    )
    # 相关本身很弱时，即使很少翻转也不叫「稳」
    if abs(mean) < 0.12 and abs(recent) < 0.15:
        return "unstable"
    if sign_broke or rate > 0.12:
        return "unstable"
    if rate <= 0.03 and not sign_broke and abs(mean) >= 0.25:
        return "stable"
    if rate <= 0.08 and not sign_broke and abs(mean) >= 0.12:
        return "mostly_stable"
    return "unstable"


def _lag_pairs(
    left: Mapping[str, float],
    right: Mapping[str, float],
    lag: int,
) -> List[Tuple[float, float]]:
    calendar = sorted(set(left) | set(right))
    index = {day: i for i, day in enumerate(calendar)}
    out: List[Tuple[float, float]] = []
    for day, value in left.items():
        i = index.get(day)
        if i is None:
            continue
        j = i + int(lag)
        if j < 0 or j >= len(calendar):
            continue
        other_day = calendar[j]
        if other_day not in right:
            continue
        out.append((value, right[other_day]))
    return out


def _corr(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x < 1e-12 or den_y < 1e-12:
        return None
    return num / (den_x * den_y)


def _ranks(values: Sequence[float]) -> List[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for rank, index in enumerate(order, start=1):
        ranks[index] = float(rank)
    return ranks


__all__ = [
    "pairwise_summary",
    "MIN_OVERLAP_RELIABLE",
    "MIN_OVERLAP_REPORT",
]
