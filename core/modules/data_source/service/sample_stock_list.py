"""
样本股票池：由 ``data.json`` 的 ``use_sample_stock_list`` 统一配置。

池文件位于 ``core/modules/data_source/dev/stock_pool/``（进 Git 的 dev 名单）。

全局约束（下游无感）：
- ``ListService`` 读路径经 ``slice_stock_list`` 过滤；
- ``PersistenceService`` 写 per-stock 表前经 ``filter_records_by_sample_pool`` 过滤。
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.infra.project_context import ProjectContext

from core.modules.data_source.dev.stock_pool_paths import (
    dev_stock_pool_dir,
    resolve_dev_stock_pool_by_count,
)

logger = logging.getLogger(__name__)

_LOGGED = False
_POOL_IDS_CACHE: Optional[List[str]] = None

# (table_name, id_column)
_PER_STOCK_PRUNE_TABLES: Tuple[Tuple[str, str], ...] = (
    ("sys_stock_klines", "id"),
    ("sys_stock_indicators", "id"),
    ("sys_adj_factor_events", "id"),
    ("sys_corporate_finance", "id"),
    ("sys_stock_st_periods", "stock_id"),
    ("sys_stock_board_map", "stock_id"),
    ("sys_stock_market_map", "stock_id"),
    ("sys_stock_industry_map", "stock_id"),
    ("sys_stock_area_map", "stock_id"),
    ("sys_stock_list", "id"),
)


def sample_pool_count() -> Optional[int]:
    return ProjectContext.config.get_use_sample_stock_list()


def pool_stock_ids() -> List[str]:
    """当前配置的样本池股票 id 列表；未配置时为空。"""
    return list(_load_pool_ids())


def is_sample_active() -> bool:
    count = sample_pool_count()
    if not count:
        return False
    return pool_csv_path(count).is_file()


def pool_dir() -> Path:
    return dev_stock_pool_dir()


def pool_csv_path(count: int) -> Path:
    return resolve_dev_stock_pool_by_count(count)


def _load_pool_ids() -> List[str]:
    global _POOL_IDS_CACHE
    if _POOL_IDS_CACHE is not None:
        return _POOL_IDS_CACHE

    count = sample_pool_count()
    if not count:
        _POOL_IDS_CACHE = []
        return _POOL_IDS_CACHE

    p = pool_csv_path(count)
    if not p.is_file():
        logger.warning("use_sample_stock_list 文件不存在: %s", p)
        _POOL_IDS_CACHE = []
        return _POOL_IDS_CACHE

    ids: List[str] = []
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "id" not in reader.fieldnames:
            logger.warning("股票池 CSV 缺少 id 列: %s", p)
            _POOL_IDS_CACHE = []
            return _POOL_IDS_CACHE
        for row in reader:
            sid = str(row.get("id") or "").strip()
            if sid:
                ids.append(sid)

    seen: Set[str] = set()
    ordered: List[str] = []
    for sid in ids:
        if sid in seen:
            continue
        seen.add(sid)
        ordered.append(sid)
    _POOL_IDS_CACHE = ordered
    return _POOL_IDS_CACHE


def invalidate_pool_cache() -> None:
    global _POOL_IDS_CACHE, _LOGGED
    _POOL_IDS_CACHE = None
    _LOGGED = False


def _stock_id_from_row(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("id") or row.get("stock_id") or "").strip()
    return str(row).strip()


def _filter_rows_by_pool(rows: Sequence[Any], pool_ids: Sequence[str]) -> List[Any]:
    if not pool_ids:
        return list(rows)

    by_id: Dict[str, Any] = {}
    for row in rows:
        sid = _stock_id_from_row(row)
        if sid and sid not in by_id:
            by_id[sid] = row

    out: List[Any] = []
    for sid in pool_ids:
        if sid in by_id:
            out.append(by_id[sid])
    return out


_STOCK_ID_FIELDS: Tuple[str, ...] = ("id", "stock_id")


def stock_id_field_for_schema(schema: Any) -> Optional[str]:
    """从表 schema 推断 per-stock 主键字段；非 per-stock 表返回 None。"""
    if not schema or not isinstance(schema, dict):
        return None
    pk = schema.get("primaryKey")
    if isinstance(pk, str):
        keys = [pk]
    elif isinstance(pk, list):
        keys = [str(k) for k in pk if k]
    else:
        return None
    for field in keys:
        if field in _STOCK_ID_FIELDS:
            return field
    return None


def filter_records_by_sample_pool(
    records: List[Dict[str, Any]],
    schema: Any = None,
    *,
    id_field: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    将 per-stock 写入行限制在样本池内；未配置样本池或非 per-stock 表时原样返回。
    """
    if not records:
        return records

    pool_ids = _load_pool_ids()
    if not pool_ids:
        return records

    col = id_field or stock_id_field_for_schema(schema)
    if not col:
        return records

    allowed = set(pool_ids)
    out = [
        row
        for row in records
        if str(row.get(col) or "").strip() in allowed
    ]
    dropped = len(records) - len(out)
    if dropped:
        logger.info(
            "📎 use_sample_stock_list=%s: 写入过滤 %s → %s 行（丢弃池外 %s 行，field=%s）",
            sample_pool_count(),
            len(records),
            len(out),
            dropped,
            col,
        )
    return out


def slice_stock_list(rows: List[Any]) -> List[Any]:
    """按 ``use_sample_stock_list`` 过滤 stock_list；未配置时原样返回。"""
    global _LOGGED
    if not rows:
        return rows

    pool_ids = _load_pool_ids()
    if not pool_ids:
        return rows

    sliced = _filter_rows_by_pool(rows, pool_ids)
    if not _LOGGED:
        _LOGGED = True
        logger.info(
            "📎 use_sample_stock_list=%s: 全量 %s 只 → 池内 %s 只 (file=%s)",
            sample_pool_count(),
            len(rows),
            len(sliced),
            pool_csv_path(sample_pool_count() or 0),
        )
    return sliced


def slice_stock_list_in_dependencies(deps: Dict[str, Any]) -> Dict[str, Any]:
    if "stock_list" not in deps:
        return deps
    raw = deps.get("stock_list")
    if not isinstance(raw, list):
        return deps
    sliced = slice_stock_list(raw)
    if sliced is raw:
        return deps
    out = dict(deps)
    out["stock_list"] = sliced
    return out


def filter_paired_stock_records(
    main_records: List[Dict[str, Any]],
    raw_records: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """``stock_list`` handler：主表与 raw 维度行同步过滤。"""
    pool_ids = _load_pool_ids()
    if not pool_ids:
        return main_records, raw_records

    allowed = set(pool_ids)
    main_out: List[Dict[str, Any]] = []
    raw_out: List[Dict[str, Any]] = []
    for i, row in enumerate(main_records):
        sid = str(row.get("id") or "").strip()
        if sid not in allowed:
            continue
        main_out.append(row)
        raw_out.append(raw_records[i] if i < len(raw_records) else {})
    return main_out, raw_out


def prune_stock_universe_to_sample_pool(data_manager: Any) -> int:
    """
    删除池外 per-stock 数据，使 DB 与 ``use_sample_stock_list`` 一致。

    Returns:
        删除行数合计（近似）。
    """
    pool_ids = _load_pool_ids()
    if not pool_ids or not data_manager or not getattr(data_manager, "db", None):
        return 0

    db = data_manager.db
    placeholders = ",".join(["%s"] * len(pool_ids))
    params = tuple(pool_ids)
    deleted = 0

    eng = getattr(db, "engine", None)
    if eng is None or not hasattr(eng, "execute_write"):
        logger.warning("DB engine 不支持 execute_write，跳过 prune")
        return 0

    for table, col in _PER_STOCK_PRUNE_TABLES:
        try:
            sql = f"DELETE FROM {table} WHERE {col} NOT IN ({placeholders})"
            n = int(eng.execute_write(sql, params) or 0)
            if n:
                deleted += n
                logger.info("prune %s: 删除 %s 行（保留池内 %s 只）", table, n, len(pool_ids))
        except Exception:
            logger.exception("prune %s 失败", table)

    try:
        sql = (
            f"DELETE FROM sys_tag_value WHERE entity_id NOT IN ({placeholders})"
        )
        n = int(eng.execute_write(sql, params) or 0)
        if n:
            deleted += n
            logger.info("prune sys_tag_value: 删除 %s 行", n)
    except Exception:
        logger.exception("prune sys_tag_value 失败")

    return deleted
