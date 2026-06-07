"""Bundle 保存与结果判定（JobPipeline on_result 与 handler 钩子共用）。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

BundleSaveItem = Tuple[Any, Dict[str, Any]]


def invoke_bundle_save(
    context: Dict[str, Any],
    batch_items: List[BundleSaveItem],
    save_mode: str,
    on_single_bundle_complete: Callable[[Dict[str, Any], Any, Dict[str, Any]], Any],
    on_batch_bundles_complete: Callable[[Dict[str, Any], List[BundleSaveItem]], Any],
) -> int:
    """
    batch：N 个 bundle 合并一次 on_batch_bundles_complete。
    immediate：逐 bundle 调用 on_single_bundle_complete。
    """
    if not batch_items:
        return 0
    if save_mode == "batch":
        on_batch_bundles_complete(context, batch_items)
        return len(batch_items)
    for job_bundle, fetched in batch_items:
        on_single_bundle_complete(context, job_bundle, fetched)
    return len(batch_items)


def has_actual_data(result_dict: Dict[str, Any]) -> bool:
    """检查结果字典是否包含可落库数据。"""
    if not isinstance(result_dict, dict) or not result_dict:
        return False

    import pandas as pd

    for _job_id, result_data in result_dict.items():
        if result_data is None:
            continue
        if isinstance(result_data, pd.DataFrame):
            if not result_data.empty:
                return True
        elif isinstance(result_data, (list, tuple)):
            if len(result_data) > 0:
                return True
        elif result_data:
            return True
    return False


def is_duckdb_context(context: Dict[str, Any]) -> bool:
    dm = context.get("data_manager")
    db = getattr(dm, "db", None) if dm is not None else None
    if db is None:
        return False
    return str(db.config.get("database_type") or "").lower() == "duckdb"


def checkpoint_after_batch_save(context: Dict[str, Any]) -> None:
    """batch 合并写入后 CHECKPOINT。"""
    import logging

    from core.infra.db.engines.duckdb.wal_policy import should_checkpoint_after_batch

    logger = logging.getLogger(__name__)
    dm = context.get("data_manager")
    db = getattr(dm, "db", None) if dm is not None else None
    if db is None or not should_checkpoint_after_batch(db.config):
        return
    if not is_duckdb_context(context):
        return
    try:
        db.checkpoint_duckdb()
    except Exception as e:
        logger.warning("批量写入后 CHECKPOINT 失败: %s", e)
