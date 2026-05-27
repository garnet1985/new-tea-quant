"""
按上市状态 × 板块 × 交易所分层抽样，构建小而全的演示股票池。
"""
from __future__ import annotations

import logging
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

StratumKey = Tuple[str, str, str]  # (list_status, board, market)


@dataclass(frozen=True)
class StockUniverseRow:
    stock_id: str
    list_status: str
    board: str
    market: str


@dataclass
class SamplingReport:
    universe_size: int
    sample_size: int
    status_counts_universe: Dict[str, int]
    status_counts_sample: Dict[str, int]
    stratum_rows: List[Dict[str, Any]]


def _norm_status(raw: Optional[str]) -> str:
    s = (raw or "").strip().upper()
    return s if s in ("L", "D", "P") else "?"


def _norm_label(raw: Optional[str], *, fallback: str) -> str:
    v = (raw or "").strip()
    return v if v else fallback


def load_stock_universe(dm) -> List[StockUniverseRow]:
    """从 DB 加载股票并挂上板块、交易所标签。"""
    stock_model = dm.get_table("sys_stock_list")
    if stock_model is None:
        raise RuntimeError("未注册 sys_stock_list")

    board_map_model = dm.get_table("sys_stock_board_map")
    market_map_model = dm.get_table("sys_stock_market_map")
    boards_model = dm.get_table("sys_boards")
    markets_model = dm.get_table("sys_markets")
    if not all([board_map_model, market_map_model, boards_model, markets_model]):
        raise RuntimeError("缺少板块/交易所维表，无法分层抽样")

    stocks = stock_model.load("1=1")
    board_by_stock: Dict[str, int] = {}
    for row in board_map_model.load("1=1"):
        sid = row.get("stock_id")
        if sid and sid not in board_by_stock:
            board_by_stock[sid] = int(row["board_id"])

    market_by_stock: Dict[str, int] = {}
    for row in market_map_model.load("1=1"):
        sid = row.get("stock_id")
        if sid and sid not in market_by_stock:
            market_by_stock[sid] = int(row["market_id"])

    board_labels = {int(r["id"]): _norm_label(r.get("value"), fallback="未知板块") for r in boards_model.load("1=1")}
    market_labels = {
        int(r["id"]): _norm_label(r.get("value"), fallback="未知交易所") for r in markets_model.load("1=1")
    }

    out: List[StockUniverseRow] = []
    for row in stocks:
        sid = row.get("id")
        if not sid:
            continue
        bid = board_by_stock.get(sid)
        mid = market_by_stock.get(sid)
        out.append(
            StockUniverseRow(
                stock_id=str(sid),
                list_status=_norm_status(row.get("list_status")),
                board=board_labels.get(bid, "未映射板块") if bid is not None else "未映射板块",
                market=market_labels.get(mid, "未映射交易所") if mid is not None else "未映射交易所",
            )
        )
    return out


def _stratum_key(row: StockUniverseRow) -> StratumKey:
    return (row.list_status, row.board, row.market)


def _allocate_sample_sizes(
    strata: Mapping[StratumKey, List[StockUniverseRow]],
    *,
    target_n: int,
    min_per_stratum: int,
) -> Dict[StratumKey, int]:
    """按各分层人口比例分配样本数（最大余数法），并尊重分层容量。"""
    total = sum(len(v) for v in strata.values())
    if total == 0:
        return {}
    if target_n >= total:
        return {k: len(v) for k, v in strata.items()}

    keys = sorted(strata.keys())
    counts = [len(strata[k]) for k in keys]
    ideal = [target_n * (c / total) for c in counts]
    use_min = min_per_stratum if len(keys) <= target_n else 0
    alloc = [max(use_min if c > 0 else 0, int(x)) for x, c in zip(ideal, counts)]

    def _cap() -> None:
        for i, k in enumerate(keys):
            alloc[i] = min(alloc[i], counts[i])

    _cap()

    while sum(alloc) > target_n:
        reducible = [i for i, c in enumerate(counts) if alloc[i] > (use_min if c > 0 else 0)]
        if not reducible:
            break
        i = max(reducible, key=lambda j: alloc[j] - ideal[j])
        alloc[i] -= 1

    while sum(alloc) < target_n:
        growable = [i for i, c in enumerate(counts) if alloc[i] < c]
        if not growable:
            break
        i = max(growable, key=lambda j: ideal[j] - alloc[j])
        alloc[i] += 1

    return {keys[i]: alloc[i] for i in range(len(keys))}


def sample_stratified_stock_pool(
    universe: Sequence[StockUniverseRow],
    *,
    target_n: int,
    seed: int,
    min_per_stratum: int = 1,
) -> Tuple[List[str], SamplingReport]:
    """分层随机抽样，返回股票 id 列表及统计报告。"""
    if not universe:
        raise RuntimeError("股票池为空，无法抽样")

    strata: Dict[StratumKey, List[StockUniverseRow]] = defaultdict(list)
    for row in universe:
        strata[_stratum_key(row)].append(row)

    sizes = _allocate_sample_sizes(strata, target_n=target_n, min_per_stratum=min_per_stratum)
    rng = random.Random(seed)

    picked: List[str] = []
    stratum_rows: List[Dict[str, Any]] = []
    for key in sorted(sizes.keys()):
        rows = strata[key]
        n = sizes[key]
        if n <= 0:
            continue
        chosen = rng.sample(rows, n) if n < len(rows) else list(rows)
        picked.extend(r.stock_id for r in chosen)
        status, board, market = key
        stratum_rows.append(
            {
                "list_status": status,
                "board": board,
                "market": market,
                "universe": len(rows),
                "sample": len(chosen),
                "universe_pct": round(100.0 * len(rows) / len(universe), 2),
                "sample_pct": round(100.0 * len(chosen) / max(1, target_n), 2),
            }
        )

    picked = sorted(set(picked))
    if len(picked) > target_n:
        picked = picked[:target_n]

    status_u = Counter(r.list_status for r in universe)
    by_id = {r.stock_id: r for r in universe}
    status_s = Counter(by_id[sid].list_status for sid in picked if sid in by_id)

    report = SamplingReport(
        universe_size=len(universe),
        sample_size=len(picked),
        status_counts_universe=dict(status_u),
        status_counts_sample=dict(status_s),
        stratum_rows=stratum_rows,
    )
    return picked, report


def log_sampling_report(report: SamplingReport, *, status_labels: Mapping[str, str]) -> None:
    u = report.universe_size
    s = report.sample_size
    logger.info("全市场股票 %d 只 → 演示池 %d 只", u, s)

    for code in ("L", "D", "P", "?"):
        cu = report.status_counts_universe.get(code, 0)
        cs = report.status_counts_sample.get(code, 0)
        if cu == 0 and cs == 0:
            continue
        label = status_labels.get(code, code)
        pct_u = 100.0 * cu / u if u else 0
        pct_s = 100.0 * cs / s if s else 0
        logger.info(
            "  状态 %s：全市场 %d (%.1f%%) → 样本 %d (%.1f%%)",
            label,
            cu,
            pct_u,
            cs,
            pct_s,
        )

    logger.info("分层明细（状态 × 板块 × 交易所）：")
    for row in report.stratum_rows:
        logger.info(
            "  %s / %s / %s：%d → %d (占全市场 %.2f%%, 占样本 %.2f%%)",
            row["list_status"],
            row["board"],
            row["market"],
            row["universe"],
            row["sample"],
            row["universe_pct"],
            row["sample_pct"],
        )
