"""按本表 renew 算出的区间，从官网翻页写入这一张表。"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager
from core.modules.data_source.core.catalog.display_names import DEFAULT_DISPLAY_NAMES

logger = logging.getLogger(__name__)


def pull_table(handler: Any, jobs: List[Any]) -> int:
    """没有任务表示这次不用更新。有任务时只拉计划里的起止。"""
    if not jobs:
        print(f"[{handler.get_key()}] 已是最新，跳过", flush=True)
        return 0
    bundle = jobs[0]
    config = handler.context.get("config")
    table = config.get_table_name()
    start = getattr(bundle, "start_date", None)
    end = getattr(bundle, "end_date", None)
    if not config.get_date_field():
        start = None
        end = None
    return _pull(handler, table, start, end)


def _pull(handler: Any, table: str, start: Optional[str], end: Optional[str]) -> int:
    provider = (handler.context.get("providers") or {}).get("ntq")
    if provider is None:
        raise ValueError("没有官网数据源 ntq")
    label = DEFAULT_DISPLAY_NAMES.get(handler.get_key(), table)
    progress = handler.progress
    saved = 0
    pages = 0
    begun = time.perf_counter()
    cursor = start
    while True:
        pages += 1
        progress.page(table, label, pages, saved)
        page = provider.sync(table, start=cursor, end=end)
        rows = page.get("rows") or []
        if rows and not handler.context.get("is_dry_run"):
            _upsert(handler, table, rows)
            saved += len(rows)
        nxt = page.get("next_start")
        if not nxt:
            break
        cursor = str(nxt)
    progress.table_done(table, label, saved, time.perf_counter() - begun)
    logger.info("官网同步 %s 写入 %s 行", table, saved)
    return saved


def _upsert(handler: Any, table: str, rows: List[Dict[str, Any]]) -> None:
    manager = handler.context.get("data_manager")
    if manager is None:
        manager = DataManager.get_instance() or DataManager()
    model = manager.get_table(table)
    if model is None or not hasattr(model, "upsert_many"):
        raise ValueError(f"本地表不能写入: {table}")
    schema = model.load_schema() or {}
    primary_key = schema.get("primaryKey")
    if isinstance(primary_key, str):
        unique_keys = [primary_key]
    elif isinstance(primary_key, list) and primary_key:
        unique_keys = list(primary_key)
    else:
        raise ValueError(f"{table} 没有主键，无法同步")
    model.upsert_many(rows, unique_keys)
