"""从 job 结果提取 opportunities（postprocess 共用）。"""
from __future__ import annotations

from typing import Any, Iterator, Tuple


def iter_opportunities_from_job_result(
    job_result: Any,
) -> Iterator[Tuple[str, list]]:
    status = getattr(job_result, "status", None)
    status_value = getattr(status, "value", str(status))
    if str(status_value).lower() != "completed":
        return

    result_payload = getattr(job_result, "result", None) or {}
    if not isinstance(result_payload, dict):
        return

    if result_payload.get("bulk") and isinstance(result_payload.get("stock_results"), list):
        for row in result_payload["stock_results"]:
            if not isinstance(row, dict):
                continue
            stock_id = str(row.get("stock_id") or "").strip()
            if not stock_id:
                continue
            opportunities = row.get("opportunities")
            if not isinstance(opportunities, list):
                raise ValueError(f"job_result.stock_results[{stock_id!r}] 缺少 opportunities list")
            yield stock_id, opportunities
        return

    stock_id = str(result_payload.get("stock_id") or "").strip()
    if not stock_id:
        raise ValueError("entity_based job_result 缺少 stock_id")
    opportunities = result_payload.get("opportunities")
    if not isinstance(opportunities, list):
        raise ValueError(f"job_result[{stock_id}] 缺少 opportunities list")
    yield stock_id, opportunities


__all__ = ["iter_opportunities_from_job_result"]
