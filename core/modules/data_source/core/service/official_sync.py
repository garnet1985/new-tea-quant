"""按本表 renew 算出的区间，从官网翻页写入这一张表。"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager
from core.modules.data_source.core.catalog.display_names import DEFAULT_DISPLAY_NAMES
from core.infra.progress import Progress

logger = logging.getLogger(__name__)


def pull_table(handler: Any, jobs: List[Any]) -> int:
    """没有股票维度的表仍整表翻页。没有任务表示这次不用更新。"""
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


def pull_entities(handler: Any, jobs: List[Any]) -> int:
    """一只股票一次要完再入库。多路并发先不开。"""
    if not jobs:
        print(f"[{handler.get_key()}] 已是最新，跳过", flush=True)
        return 0
    provider = (handler.context.get("providers") or {}).get("ntq")
    if provider is None:
        raise ValueError("没有官网数据源 ntq")
    config = handler.context.get("config")
    table = config.get_table_name()
    jobs, saved = _apply_remote_plan(handler, provider, table, jobs)
    total = len(jobs)
    if total == 0:
        print(f"[{handler.get_key()}] 缓存已覆盖，无需按股票拉取", flush=True)
        return saved
    for index, bundle in enumerate(jobs, start=1):
        entity_id = _entity_id(bundle)
        if entity_id:
            page = provider.sync(
                table,
                start=getattr(bundle, "start_date", None),
                end=getattr(bundle, "end_date", None),
                entity_id=entity_id,
            )
            rows = page.get("rows") or []
            if rows and not handler.context.get("is_dry_run"):
                _upsert(handler, table, rows)
                saved += len(rows)
            if not page.get("next_start"):
                _note_settled(handler, entity_id, page)
        handler.progress.bundles(index, total, saved)
    print(f"[{handler.get_key()}] 抓取结束 {total}/{total}，已写入 {saved} 行", flush=True)
    return saved


def _pull(handler: Any, table: str, start: Optional[str], end: Optional[str]) -> int:
    provider = (handler.context.get("providers") or {}).get("ntq")
    if provider is None:
        raise ValueError("没有官网数据源 ntq")
    label = DEFAULT_DISPLAY_NAMES.get(handler.get_key(), table)
    progress = handler.progress
    pages = 0
    saved = 0
    total: Optional[int] = None
    begun = time.perf_counter()
    cursor = start
    while True:
        pages += 1
        progress.page(table, label, pages, saved, total)
        page = provider.sync(table, start=cursor, end=end)
        if total is None and isinstance(page.get("total"), int):
            total = page["total"]
        rows = page.get("rows") or []
        if rows and not handler.context.get("is_dry_run"):
            _upsert(handler, table, rows)
            saved += len(rows)
        nxt = page.get("next_start")
        if not nxt:
            _note_settled(handler, None, page)
            break
        cursor = str(nxt)
    progress.table_done(table, label, saved, time.perf_counter() - begun)
    logger.info("官网同步 %s 写入 %s 行", table, saved)
    return saved


def _apply_remote_plan(handler: Any, provider: Any, table: str, jobs: List[Any]) -> tuple:
    """一次把缺口交给远端。先导入它指定的文件，再只留下它点名的单股区间。"""
    if not hasattr(provider, "plan_entities"):
        return jobs, 0
    ranges = []
    for job in jobs:
        entity_id = _entity_id(job)
        start = str(getattr(job, "start_date", "") or "")
        end = str(getattr(job, "end_date", "") or "")
        if entity_id and start and end:
            ranges.append({"id": entity_id, "start": start, "end": end})
    if not ranges:
        return jobs, 0
    try:
        plan = provider.plan_entities(table, ranges, "all")
    except Exception:
        print(f"[{handler.get_key()}] 远端没有返回更新计划，改为按股票拉取", flush=True)
        logger.warning("官网没有返回更新计划，改为按股票拉取", exc_info=True)
        return jobs, 0
    files = [item for item in (plan.get("files") or []) if isinstance(item, dict) and item.get("path")]
    left = []
    for item in plan.get("stocks") or []:
        if not isinstance(item, dict):
            continue
        entity_id = str(item.get("id") or "")
        start = str(item.get("start") or "")
        end = str(item.get("end") or "")
        if entity_id and start and end:
            left.append(_planned_job(entity_id, start, end))
    if not files:
        print(f"[{handler.get_key()}] 远端计划：没有缓存文件，按股票拉取 {len(left)} 只", flush=True)
    else:
        spans = []
        for item in files:
            label = f"{item.get('from') or '?'}–{item.get('through') or '?'}"
            if label not in spans:
                spans.append(label)
        spans = "，".join(spans)
        print(
            f"[{handler.get_key()}] 远端计划：{len(files)} 个数据包（{spans}），导入后再按股票补 {len(left)} 只",
            flush=True,
        )
    saved = 0
    total_files = len(files)
    for index, item in enumerate(files, start=1):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        through = str(item.get("through") or "")
        try:
            imported = _import_snapshot(handler, provider, table, path)
        except Exception:
            print(f"[{handler.get_key()}] 数据包导入失败，改为按股票拉取", flush=True)
            logger.warning("数据包导入失败", exc_info=True)
            return jobs, saved
        saved += imported
        Progress.sub(index, total_files, source=str(handler.get_key() or ""))
        print(
            f"[{handler.get_key()}] 数据包 {index}/{total_files} 已导入 {imported} 行，截止 {through}",
            flush=True,
        )
    return left, saved


def _planned_job(entity_id: str, start: str, end: str) -> Any:
    job = type("Planned", (), {})()
    job.start_date = start
    job.end_date = end
    job.apis = [type("Api", (), {"params": {"id": entity_id}})()]
    return job


def _import_snapshot(handler: Any, provider: Any, table: str, path: str) -> int:
    if handler.context.get("is_dry_run"):
        return 0
    if not path:
        raise ValueError("数据包没有地址")
    payload = provider.download(path)
    import csv
    import gzip
    import io

    if payload.startswith(b"\x1f\x8b"):
        payload = gzip.decompress(payload)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    saved = 0
    chunk: List[Dict[str, Any]] = []
    for row in reader:
        chunk.append(dict(row))
        if len(chunk) >= 1000:
            _upsert(handler, table, chunk)
            saved += len(chunk)
            chunk = []
    if chunk:
        _upsert(handler, table, chunk)
        saved += len(chunk)
    return saved


def _entity_id(bundle: Any) -> str:
    for api in getattr(bundle, "apis", None) or []:
        params = getattr(api, "params", None) or {}
        entity_id = params.get("id")
        if entity_id:
            return str(entity_id)
    return ""


def list_rows(handler: Any) -> List[Dict[str, Any]]:
    """股票列表和行业分类要交给下游当实体名单，不能只交空列表。"""
    if handler.get_key() not in ("stock_list", "sw_industry"):
        return []
    manager = handler.context.get("data_manager")
    if manager is None:
        manager = DataManager.get_instance()
    config = handler.context.get("config")
    if manager is None or config is None:
        return []
    model = manager.get_table(config.get_table_name())
    if model is None or not hasattr(model, "load"):
        return []
    try:
        rows = model.load() or []
    except Exception:
        logger.warning("读取 %s 作为下游名单失败", handler.get_key(), exc_info=True)
        return []
    return list(rows)


_BLANK_AS_NULL = {"float", "double", "decimal", "int", "integer", "bigint", "smallint", "tinyint", "date", "datetime"}


def _blank_as_null(schema: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    """CSV 里的空单元格是空字符串。数字和日期列要写成 NULL。"""
    names = set()
    for field in schema.get("fields") or []:
        if not isinstance(field, dict):
            continue
        if str(field.get("type") or "").lower() in _BLANK_AS_NULL and field.get("name"):
            names.add(field["name"])
    if not names:
        return
    for row in rows:
        for name in names:
            value = row.get(name)
            if isinstance(value, str) and value.strip() == "":
                row[name] = None


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
    _blank_as_null(schema, rows)
    model.upsert_many(rows, unique_keys)
    _note_rows(handler, rows)


def _note_rows(handler: Any, rows: List[Dict[str, Any]]) -> None:
    try:
        from core.modules.data_source.core.service.renew_progress import remember_written_rows

        remember_written_rows(handler, rows)
    except Exception:
        logger.warning("写入后没能记下已经更新到的数据日期", exc_info=True)


def _note_settled(handler: Any, entity_id: Optional[str], page: Dict[str, Any]) -> None:
    settled = page.get("settled_through") if isinstance(page, dict) else None
    if not isinstance(settled, str) or not settled.strip():
        return
    rows = page.get("rows") if isinstance(page, dict) else None
    # 区间被判成空的（一页都没有，total 也是 0）不能当成已经读完。
    if not rows and page.get("total") == 0:
        return
    try:
        from core.modules.data_source.core.service.renew_progress import remember_settled

        remember_settled(handler, entity_id, settled)
    except Exception:
        logger.warning("没能记下官网已经读完的数据日期", exc_info=True)
