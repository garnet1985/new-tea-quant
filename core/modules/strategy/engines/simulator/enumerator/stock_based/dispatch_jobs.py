"""枚举 dispatch job 分组（多股 / job）。"""
from __future__ import annotations

from typing import Any, Dict, List


def chunk_stock_ids(stock_ids: List[str], entities_per_job: int) -> List[List[str]]:
    size = max(1, int(entities_per_job))
    ids = [str(s).strip() for s in stock_ids if str(s).strip()]
    return [ids[i : i + size] for i in range(0, len(ids), size)]


def dispatch_job_id(batch_index: int, stock_ids: List[str]) -> str:
    if len(stock_ids) == 1:
        return str(stock_ids[0])
    return f"batch_{batch_index}:{stock_ids[0]}..{stock_ids[-1]}({len(stock_ids)})"


def count_stocks_in_dispatch_jobs(jobs: List[Dict[str, Any]]) -> int:
    total = 0
    for job in jobs:
        ids = job.get("stock_ids")
        if isinstance(ids, list) and ids:
            total += len(ids)
        elif job.get("stock_id"):
            total += 1
    return total


def stock_ids_from_dispatch_job(job: Dict[str, Any]) -> List[str]:
    ids = job.get("stock_ids")
    if isinstance(ids, list) and ids:
        return [str(s).strip() for s in ids if str(s).strip()]
    sid = job.get("stock_id")
    return [str(sid).strip()] if sid else []


def build_dispatch_jobs(
    *,
    strategy_name: str,
    settings_payload: Dict[str, Any],
    output_dir: str,
    worker_ref: Dict[str, str],
    stock_ids: List[str],
    start_date: str,
    end_date: str,
    entities_per_job: int = 1,
) -> List[Dict[str, Any]]:
    chunks = chunk_stock_ids(stock_ids, entities_per_job)
    jobs: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        if not chunk:
            continue
        job_id = dispatch_job_id(idx, chunk)
        row: Dict[str, Any] = {
            "job_id": job_id,
            "stock_ids": list(chunk),
            "strategy_name": strategy_name,
            "settings": settings_payload,
            "start_date": start_date,
            "end_date": end_date,
            "output_dir": output_dir,
            "worker_module_path": worker_ref["worker_module_path"],
            "worker_class_name": worker_ref["worker_class_name"],
            "worker_file_path": str(worker_ref.get("worker_file_path") or ""),
        }
        if len(chunk) == 1:
            row["stock_id"] = chunk[0]
        jobs.append(row)
    return jobs
