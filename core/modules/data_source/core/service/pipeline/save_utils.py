"""Bundle 结果判定与写库后的检查点。"""
from __future__ import annotations

from typing import Any, Dict, Tuple

BundleSaveItem = Tuple[Any, Dict[str, Any]]


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

    from core.infra.db import Db

    logger = logging.getLogger(__name__)
    dm = context.get("data_manager")
    db = getattr(dm, "db", None) if dm is not None else None
    if db is None or not Db.duckdb.wal.should_checkpoint_after_batch(db.config):
        return
    if not is_duckdb_context(context):
        return
    try:
        db.checkpoint_duckdb()
    except Exception as e:
        logger.warning("批量写入后 CHECKPOINT 失败: %s", e)
