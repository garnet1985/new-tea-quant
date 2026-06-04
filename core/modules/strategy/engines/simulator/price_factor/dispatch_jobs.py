"""价格因子 dispatch job 分组。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.engines.simulator.enumerator.dispatch_jobs import (
    chunk_stock_ids,
    dispatch_job_id,
)


def build_price_dispatch_jobs(
    *,
    per_stock_jobs: List[Dict[str, Any]],
    entities_per_job: int,
) -> List[Dict[str, Any]]:
    """将逐股 job 模板按 stock_id 分 chunk，合成多股 dispatch job。"""
    if not per_stock_jobs:
        return []

    by_id: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in per_stock_jobs:
        sid = str(row.get("stock_id") or "").strip()
        if not sid:
            continue
        if sid not in by_id:
            order.append(sid)
        by_id[sid] = dict(row)

    chunks = chunk_stock_ids(order, entities_per_job)
    dispatch_jobs: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        stock_jobs = [by_id[sid] for sid in chunk if sid in by_id]
        if not stock_jobs:
            continue
        head = stock_jobs[0]
        job: Dict[str, Any] = {
            "job_id": dispatch_job_id(idx, chunk),
            "stock_ids": list(chunk),
            "stock_jobs": stock_jobs,
            "strategy_name": head.get("strategy_name"),
            "output_version_dir": head.get("output_version_dir"),
            "config": head.get("config"),
            "market_profile_id": head.get("market_profile_id"),
            "backtest_calendar": head.get("backtest_calendar"),
        }
        if len(chunk) == 1:
            job.update(stock_jobs[0])
        dispatch_jobs.append(job)
    return dispatch_jobs


__all__ = ["build_price_dispatch_jobs"]
