#!/usr/bin/env python3
"""
数据迁移：旧表 → sys_* 新表

从旧库表（stock_list、stock_kline、price_indexes 等）读取数据，按 docs/development/migration-tables-todo.md
的对应关系转换后写入新 sys_* 表。执行前请先运行 scripts/create_sys_tables.py 创建新表。

使用：
    python scripts/migrate_to_sys_tables.py
    或从项目根目录：python -m scripts.migrate_to_sys_tables

可选环境变量：
    MIGRATE_DRY_RUN=1  仅检查旧表存在并打印将迁移的行数，不写入新表
    MIGRATE_ONLY=step  仅执行指定步骤，如 kline_monthly / kline_weekly / kline_daily
    COMPARE_AND_FIX=1  先对比各表记录数，仅对数量不一致的步骤再次迁移
"""
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple

# 项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from core.modules.data_manager.data_manager import DataManager

# 大批量插入时每多少行打一次进度
PROGRESS_CHUNK = 500000


def _read_old_table(dm: DataManager, old_table: str) -> List[Dict[str, Any]]:
    """从旧表读取全部行；表不存在或出错时返回空列表。"""
    if not dm.db.is_table_exists(old_table):
        logger.warning(f"旧表不存在，跳过: {old_table}")
        return []
    logger.info(f"  正在读取 {old_table} ...")
    try:
        rows = dm.db.execute_sync_query(f"SELECT * FROM {old_table}")
        out = list(rows) if rows else []
        logger.info(f"  读取完成: {len(out)} 行")
        return out
    except Exception as e:
        logger.error(f"读取旧表失败 [{old_table}]: {e}")
        return []


def _get_table_order_by_columns(
    dm: DataManager, table_name: str, include_term: bool = False
) -> Optional[str]:
    """
    从数据库 information_schema 读取表实际列名，返回用于稳定分页的 ORDER BY 列名（如 'id, date'）。
    优先用 id，若无则用 ts_code；日期列用 date。若 include_term 且表有 term 列，则包含 term 以保证
    主键 (id, term, date) 唯一排序，避免 LIMIT/OFFSET 分页漏行或重复。
    """
    if not dm.db.is_table_exists(table_name):
        return None
    try:
        q = (
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s ORDER BY ordinal_position"
        )
        rows = dm.db.execute_sync_query(q, (table_name,))
        if not rows:
            return None
        columns = [r["column_name"] for r in rows]
        id_col = "id" if "id" in columns else ("ts_code" if "ts_code" in columns else None)
        date_col = "date" if "date" in columns else ("trade_date" if "trade_date" in columns else None)
        if id_col and date_col:
            if include_term and "term" in columns:
                return f"{id_col}, term, {date_col}"
            return f"{id_col}, {date_col}"
        return None
    except Exception as e:
        logger.warning(f"无法读取表 {table_name} 列信息: {e}")
        return None


def _read_old_table_paged(
    dm: DataManager,
    old_table: str,
    where_clause: str,
    params: tuple,
    limit: int,
    offset: int,
    order_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """从旧表分页读取；order_by 用于稳定分页（避免 LIMIT/OFFSET 漏行或重复）。不猜测列名，由调用方传入或通过 _get_table_order_by_columns 从库中读取。"""
    if not dm.db.is_table_exists(old_table):
        return []
    try:
        sql = f"SELECT * FROM {old_table} WHERE {where_clause}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        sql += " LIMIT %s OFFSET %s"
        rows = dm.db.execute_sync_query(sql, params + (limit, offset))
        return list(rows) if rows else []
    except Exception as e:
        logger.error(f"分页读取失败 [{old_table}]: {e}")
        return []


def _insert_batch_or_diagnose(
    model: Any,
    rows: List[Dict[str, Any]],
    unique_keys: List[str],
    step_name: str,
) -> int:
    """批量插入；若返回 0 且 rows 非空则试插单行并打印异常，便于排查。"""
    if not rows:
        return 0
    n = model.insert(rows, unique_keys=unique_keys, use_batch=True)
    if n == 0 and len(rows) > 0:
        logger.warning(f"  {step_name}: 本批插入返回 0，试插单行以获取错误信息...")
        try:
            model.insert([rows[0]], unique_keys=unique_keys, use_batch=True)
        except Exception as e:
            logger.error(f"  单行插入异常: {e}")
            logger.info(f"  首行键: {list(rows[0].keys())}")
            logger.info(f"  首行 id/date: {rows[0].get('id')!r}, {rows[0].get('date')!r}")
        else:
            logger.warning("  单行插入未抛异常但批量返回 0，可能是 DB 层静默失败，请查 DataManager/Adapter 日志")
    return n


def _insert_with_progress(
    model: Any,
    rows: List[Dict[str, Any]],
    unique_keys: List[str],
    step_name: str,
    chunk_size: int = PROGRESS_CHUNK,
) -> int:
    """分批插入并打印进度（每 chunk_size 行或最后一批打一条日志）。"""
    if not rows:
        return 0
    total = len(rows)
    if total <= chunk_size:
        n = model.insert(rows, unique_keys=unique_keys, use_batch=True)
        logger.info(f"  {step_name}: 已写入 {n} 行")
        return n
    written = 0
    for i in range(0, total, chunk_size):
        chunk = rows[i : i + chunk_size]
        n = model.insert(chunk, unique_keys=unique_keys, use_batch=True)
        written += n
        pct = min(100, round(100 * (i + len(chunk)) / total, 1))
        logger.info(f"  {step_name}: 已写入 {written} / {total} 行 ({pct}%)")
    return written


def _count_table(
    dm: DataManager,
    table: str,
    where_clause: Optional[str] = None,
    params: tuple = (),
) -> int:
    """查询表记录数；表不存在或出错返回 -1。"""
    if not dm.db.is_table_exists(table):
        return -1
    try:
        if where_clause:
            q = f"SELECT count(*) AS cnt FROM {table} WHERE {where_clause}"
            rows = dm.db.execute_sync_query(q, params)
        else:
            rows = dm.db.execute_sync_query(f"SELECT count(*) AS cnt FROM {table}", ())
        if rows and len(rows) > 0:
            return int(rows[0].get("cnt", 0))
        return 0
    except Exception as e:
        logger.warning(f"统计表 {table} 行数失败: {e}")
        return -1


def _pick_columns(row: Dict[str, Any], new_columns: List[str], renames: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """从 row 中取 new_columns 中的键。优先用新列名（与当前表一致），若无再用 renames 的旧名。"""
    renames = renames or {}
    inv = {v: k for k, v in renames.items()}  # new -> old
    out = {}
    for col in new_columns:
        if col in row:
            out[col] = row[col]
        else:
            old_name = inv.get(col, col)
            if old_name in row:
                out[col] = row[old_name]
    return out


def migrate_one_to_one(
    dm: DataManager,
    old_table: str,
    new_table_name: str,
    new_columns: List[str],
    renames: Optional[Dict[str, str]] = None,
    unique_keys: Optional[List[str]] = None,
    dry_run: bool = False,
) -> int:
    """一对一迁移：从 old_table 读，列对齐到 new_columns（renames 为 旧名->新名），写入 new_table_name。unique_keys 不为空时用 insert+ON CONFLICT DO NOTHING，只补缺失行、不覆盖已有数据。"""
    rows = _read_old_table(dm, old_table)
    if not rows:
        return 0
    model = dm.get_table(new_table_name)
    if not model:
        logger.warning(f"新表 Model 未注册: {new_table_name}")
        return 0
    out = [_pick_columns(r, new_columns, renames) for r in rows]
    if dry_run:
        logger.info(f"[DRY RUN] {old_table} -> {new_table_name}: {len(out)} 行")
        return len(out)
    # 统一用 insert；有 unique_keys 时走 ON CONFLICT DO NOTHING，只插入新表中不存在的行
    n = model.insert(out, unique_keys=unique_keys, use_batch=True)
    logger.info(f"{old_table} -> {new_table_name}: {n} 行")
    return n


def migrate_system_cache(dm: DataManager, dry_run: bool = False) -> int:
    """system_cache -> sys_cache；value 保持文本，补充 created_at / last_updated。"""
    old = "system_cache"
    rows = _read_old_table(dm, old)
    if not rows:
        return 0
    model = dm.get_table("sys_cache")
    if not model:
        return 0
    now = datetime.now()
    out = []
    for r in rows:
        key = r.get("key")
        if key is None:
            continue
        last_updated = r.get("last_updated") or r.get("last_update") or now
        created_at = last_updated  # 有 last_update 则创建时间等于更新时间，否则均为 now
        o = {
            "key": key,
            "value": r.get("value") or r.get("val") or "",
            "created_at": created_at,
            "last_updated": last_updated,
        }
        out.append(o)
    if dry_run:
        logger.info(f"[DRY RUN] {old} -> sys_cache: {len(out)} 行")
        return len(out)
    n = model.replace(out, unique_keys=["key"], use_batch=True)
    logger.info(f"{old} -> sys_cache: {n} 行")
    return n


def migrate_meta_info(dm: DataManager, dry_run: bool = False) -> int:
    """meta_info -> sys_meta_info；info -> value (JSON)，补充 created_at / last_updated。"""
    old = "meta_info"
    rows = _read_old_table(dm, old)
    if not rows:
        return 0
    model = dm.get_table("sys_meta_info")
    if not model:
        return 0
    now = datetime.now()
    out = []
    for r in rows:
        val = r.get("value")
        if val is None:
            val = r.get("info")
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                val = {"raw": val}
        # sys_meta_info.value 为 JSON 列，须为 dict/list；数字等包装为 {"v": val}
        if not isinstance(val, (dict, list)):
            val = {"v": val}
        last_updated = r.get("last_updated") or r.get("last_update") or now
        created_at = last_updated  # 有 last_update 则创建时间等于更新时间，否则均为 now
        o = {
            "value": val,
            "created_at": created_at,
            "last_updated": last_updated,
        }
        out.append(o)
    if dry_run:
        logger.info(f"[DRY RUN] {old} -> sys_meta_info: {len(out)} 行")
        return len(out)
    n = model.insert(out, use_batch=True)
    logger.info(f"{old} -> sys_meta_info: {n} 行")
    return n


def migrate_industries_from_stock_list(dm: DataManager, dry_run: bool = False) -> int:
    """从 stock_list.industry 去重生成 sys_industries，再写 sys_stock_industries。"""
    old = "stock_list"
    rows = _read_old_table(dm, old)
    industry_col = "industry"
    if not rows or not any(industry_col in r and r.get(industry_col) for r in rows):
        logger.warning("stock_list 无 industry 列或全空，跳过行业衍生")
        return 0
    unique_industries = []
    seen = set()
    for r in rows:
        v = r.get(industry_col)
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            continue
        s = str(v).strip()
        if s not in seen:
            seen.add(s)
            unique_industries.append(s)
    if not unique_industries:
        return 0
    ind_model = dm.get_table("sys_industries")
    si_model = dm.get_table("sys_stock_industries")
    if not ind_model or not si_model:
        return 0
    # id 1..n for industries
    ind_rows = [
        {"id": i, "value": v, "is_alive": 1}
        for i, v in enumerate(unique_industries, start=1)
    ]
    value_to_id = {v: i for i, v in enumerate(unique_industries, start=1)}
    si_rows = []
    for r in rows:
        stock_id = r.get("id") or r.get("ts_code")
        v = r.get(industry_col)
        if not stock_id or not v or str(v).strip() not in value_to_id:
            continue
        si_rows.append({"stock_id": stock_id, "industry_id": value_to_id[str(v).strip()]})
    if dry_run:
        logger.info(f"[DRY RUN] stock_list.industry -> sys_industries: {len(ind_rows)} 行, sys_stock_industries: {len(si_rows)} 行")
        return len(ind_rows) + len(si_rows)
    ind_model.replace(ind_rows, unique_keys=["id"], use_batch=True)
    si_model.replace(si_rows, unique_keys=["stock_id", "industry_id"], use_batch=True)
    logger.info(f"stock_list.industry -> sys_industries: {len(ind_rows)}, sys_stock_industries: {len(si_rows)}")
    return len(ind_rows) + len(si_rows)


def migrate_stock_list(dm: DataManager, dry_run: bool = False) -> int:
    """stock_list -> sys_stock_list；只迁 id/name/is_active/last_update，industry_id/market_id/board_id 留空由 renew 填充。"""
    return migrate_one_to_one(
        dm,
        "stock_list",
        "sys_stock_list",
        ["id", "name", "industry_id", "market_id", "board_id", "is_active", "last_update"],
        renames={"ts_code": "id"},
        unique_keys=["id"],
        dry_run=dry_run,
    )


def _transform_kline_batch(
    rows: List[Dict],
    kline_columns: List[str],
    old_to_new: Dict[str, str],
    term: Optional[str] = None,
) -> List[Dict]:
    """将一批 kline 行转为新表列结构；term 不为空时写入 term 列（用于 sys_stock_klines）。"""
    out = []
    for r in rows:
        o = _pick_columns(r, kline_columns, old_to_new)
        if o.get("id") is None and "ts_code" in r:
            o["id"] = r["ts_code"]
        if term is not None:
            o["term"] = term
        if len(o) >= 2:
            for col in kline_columns:
                if col not in o:
                    o[col] = None
            out.append(o)
    return out


def migrate_kline_by_term(dm: DataManager, term: str, new_table: str, dry_run: bool = False) -> int:
    """从 stock_kline 按页读取 term 匹配的行，写入 new_table（sys_stock_klines 时保留 term 列）。不整表读入内存。"""
    logger.info(f"[K线-{term}] {new_table} 开始（分页读取，每页 {PROGRESS_CHUNK} 行）...")
    model = dm.get_table(new_table)
    if not model:
        return 0
    # sys_stock_klines 含 term 列，主键 (id, term, date)
    include_term = new_table == "sys_stock_klines"
    kline_columns = ["id", "term", "date", "open", "close", "highest", "lowest", "price_change_delta", "price_change_rate_delta", "pre_close", "volume", "amount"] if include_term else ["id", "date", "open", "close", "highest", "lowest", "price_change_delta", "price_change_rate_delta", "pre_close", "volume", "amount"]
    old_to_new = {"ts_code": "id", "high": "highest", "low": "lowest", "vol": "volume", "trade_date": "date"}
    unique_keys = ["id", "term", "date"] if include_term else ["id", "date"]
    total_written = 0
    offset = 0
    page = 0
    # 分页必须 ORDER BY 主键顺序 (id, term, date)，否则 LIMIT/OFFSET 会漏行或重复
    order_by = _get_table_order_by_columns(dm, "stock_kline", include_term=True)
    if not order_by:
        logger.warning("无法从 stock_kline 读取分页排序列，将不带 ORDER BY 分页（可能漏行或重复）")
    if dry_run:
        # dry_run 只统计：用分页读直到空，不写入
        while True:
            batch = _read_old_table_paged(dm, "stock_kline", "term = %s", (term,), PROGRESS_CHUNK, offset, order_by=order_by)
            if not batch:
                break
            total_written += len(batch)
            offset += len(batch)
            page += 1
            logger.info(f"  [DRY RUN] 已扫描 {total_written} 行（第 {page} 页）")
            if len(batch) < PROGRESS_CHUNK:
                break
        logger.info(f"[DRY RUN] stock_kline (term={term}) -> {new_table}: 共 {total_written} 行")
        return total_written
    while True:
        batch = _read_old_table_paged(dm, "stock_kline", "term = %s", (term,), PROGRESS_CHUNK, offset, order_by=order_by)
        if not batch:
            break
        out = _transform_kline_batch(batch, kline_columns, old_to_new, term=term if include_term else None)
        if out:
            n = _insert_batch_or_diagnose(model, out, unique_keys, new_table)
            total_written += n
            page += 1
            logger.info(f"  {new_table}: 已写入本页 {len(out)} 行，累计 {total_written} 行（第 {page} 页）")
        offset += len(batch)
        if len(batch) < PROGRESS_CHUNK:
            break
    logger.info(f"[K线-{term}] {new_table} 完成: 共写入 {total_written} 行")
    return total_written


def migrate_stock_indicators_from_kline(dm: DataManager, dry_run: bool = False) -> int:
    """从 stock_kline 按页读取 term=daily 的行，抽取 daily_basic 列写入 sys_stock_indicators。不整表读入内存。"""
    logger.info(f"[指标表] sys_stock_indicators 开始（分页读取 term=daily，每页 {PROGRESS_CHUNK} 行）...")
    model = dm.get_table("sys_stock_indicators")
    if not model:
        return 0
    cols = ["id", "date", "turnover_rate", "free_turnover_rate", "volume_ratio", "pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm", "total_share", "float_share", "free_share", "total_market_value", "circ_market_value"]
    renames = {"ts_code": "id"}
    total_written = 0
    offset = 0
    page = 0
    order_by = _get_table_order_by_columns(dm, "stock_kline")
    if not order_by:
        logger.warning("无法从 stock_kline 读取分页排序列，将不带 ORDER BY 分页（可能漏行或重复）")
    if dry_run:
        while True:
            batch = _read_old_table_paged(dm, "stock_kline", "term = %s", ("daily",), PROGRESS_CHUNK, offset, order_by=order_by)
            if not batch:
                break
            total_written += len(batch)
            offset += len(batch)
            page += 1
            logger.info(f"  [DRY RUN] 已扫描 {total_written} 行（第 {page} 页）")
            if len(batch) < PROGRESS_CHUNK:
                break
        logger.info(f"[DRY RUN] stock_kline daily_basic -> sys_stock_indicators: 共 {total_written} 行")
        return total_written
    while True:
        batch = _read_old_table_paged(dm, "stock_kline", "term = %s", ("daily",), PROGRESS_CHUNK, offset, order_by=order_by)
        if not batch:
            break
        out = []
        for r in batch:
            o = _pick_columns(r, cols, renames)
            if o.get("id") is None and "ts_code" in r:
                o["id"] = r["ts_code"]
            if o.get("id") and o.get("date"):
                out.append(o)
        if out:
            n = model.insert(out, unique_keys=["id", "date"], use_batch=True)
            total_written += n
            page += 1
            logger.info(f"  sys_stock_indicators: 已写入本页 {len(out)} 行，累计 {total_written} 行（第 {page} 页）")
        offset += len(batch)
        if len(batch) < PROGRESS_CHUNK:
            break
    logger.info(f"[指标表] sys_stock_indicators 完成: 共写入 {total_written} 行")
    return total_written


def migrate_price_indexes_split(dm: DataManager, dry_run: bool = False) -> int:
    """price_indexes 按类型拆到 sys_cpi / sys_ppi / sys_pmi / sys_money_supply。"""
    rows = _read_old_table(dm, "price_indexes")
    if not rows:
        return 0
    total = 0
    # CPI
    cpi_cols = ["date", "cpi", "cpi_yoy", "cpi_mom"]
    cpi_rows = [_pick_columns(r, cpi_cols) for r in rows if any(r.get(k) is not None for k in cpi_cols[1:])]
    if cpi_rows:
        m = dm.get_table("sys_cpi")
        if m:
            if dry_run:
                logger.info(f"[DRY RUN] price_indexes -> sys_cpi: {len(cpi_rows)} 行")
            else:
                total += m.replace(cpi_rows, unique_keys=["date"], use_batch=True)
                logger.info(f"price_indexes -> sys_cpi: {len(cpi_rows)} 行")
    # PPI
    ppi_cols = ["date", "ppi", "ppi_yoy", "ppi_mom"]
    ppi_rows = [_pick_columns(r, ppi_cols) for r in rows if any(r.get(k) is not None for k in ppi_cols[1:])]
    if ppi_rows:
        m = dm.get_table("sys_ppi")
        if m:
            if dry_run:
                logger.info(f"[DRY RUN] price_indexes -> sys_ppi: {len(ppi_rows)} 行")
            else:
                total += m.replace(ppi_rows, unique_keys=["date"], use_batch=True)
                logger.info(f"price_indexes -> sys_ppi: {len(ppi_rows)} 行")
    # PMI
    pmi_cols = ["date", "pmi", "pmi_l_scale", "pmi_m_scale", "pmi_s_scale"]
    pmi_rows = [_pick_columns(r, pmi_cols) for r in rows if any(r.get(k) is not None for k in pmi_cols[1:])]
    if pmi_rows:
        m = dm.get_table("sys_pmi")
        if m:
            if dry_run:
                logger.info(f"[DRY RUN] price_indexes -> sys_pmi: {len(pmi_rows)} 行")
            else:
                n = m.replace(pmi_rows, unique_keys=["date"], use_batch=True)
                total += n
                logger.info(f"price_indexes -> sys_pmi: {len(pmi_rows)} 行")
    # money_supply
    ms_cols = ["date", "m0", "m1", "m2", "m0_yoy", "m1_yoy", "m2_yoy", "m0_mom", "m1_mom", "m2_mom"]
    ms_rows = [_pick_columns(r, ms_cols) for r in rows if any(r.get(k) is not None for k in ["m0", "m1", "m2"])]
    if ms_rows:
        m = dm.get_table("sys_money_supply")
        if m:
            if dry_run:
                logger.info(f"[DRY RUN] price_indexes -> sys_money_supply: {len(ms_rows)} 行")
            else:
                n = m.replace(ms_rows, unique_keys=["date"], use_batch=True)
                total += n
                logger.info(f"price_indexes -> sys_money_supply: {len(ms_rows)} 行")
    return total


def _compare_migration_counts(dm: DataManager) -> List[Tuple[str, str, int, int]]:
    """对比各迁移步骤的旧表与新表记录数，返回 (step_id, label, old_count, new_count)。"""
    results = []
    # 一对一表
    one_to_one = [
        ("gdp", "gdp -> sys_gdp", "gdp", "sys_gdp"),
        ("lpr", "lpr -> sys_lpr", "lpr", "sys_lpr"),
        ("shibor", "shibor -> sys_shibor", "shibor", "sys_shibor"),
        ("tag_scenario", "tag_scenario -> sys_tag_scenario", "tag_scenario", "sys_tag_scenario"),
        ("tag_definition", "tag_definition -> sys_tag_definition", "tag_definition", "sys_tag_definition"),
        ("tag_value", "tag_value -> sys_tag_value", "tag_value", "sys_tag_value"),
        ("system_cache", "system_cache -> sys_cache", "system_cache", "sys_cache"),
        ("meta_info", "meta_info -> sys_meta_info", "meta_info", "sys_meta_info"),
        ("stock_list", "stock_list -> sys_stock_list", "stock_list", "sys_stock_list"),
        ("adj_factor_event", "adj_factor_event -> sys_adj_factor_events", "adj_factor_event", "sys_adj_factor_events"),
        ("corporate_finance", "corporate_finance -> sys_corporate_finance", "corporate_finance", "sys_corporate_finance"),
        ("stock_index_indicator", "stock_index_indicator -> sys_index_klines", "stock_index_indicator", "sys_index_klines"),
        ("stock_index_indicator_weight", "stock_index_indicator_weight -> sys_index_weight", "stock_index_indicator_weight", "sys_index_weight"),
    ]
    for step_id, label, old_t, new_t in one_to_one:
        old_c = _count_table(dm, old_t)
        new_c = _count_table(dm, new_t)
        if old_c >= 0 or new_c >= 0:
            results.append((step_id, label, old_c, new_c))
    # industries: 比较 sys_industries 与 stock_list 中去重 industry 数；sys_stock_industries 与 stock_list 有 industry 的行数
    if dm.db.is_table_exists("stock_list"):
        try:
            r = dm.db.execute_sync_query(
                "SELECT count(DISTINCT industry) AS cnt FROM stock_list WHERE industry IS NOT NULL AND trim(industry::text) != ''", ()
            )
            old_ind = int(r[0]["cnt"]) if r else 0
        except Exception:
            old_ind = -1
        new_ind = _count_table(dm, "sys_industries")
        results.append(("industries", "stock_list.industry -> sys_industries (distinct)", old_ind, new_ind))
        try:
            r = dm.db.execute_sync_query(
                "SELECT count(*) AS cnt FROM stock_list WHERE industry IS NOT NULL AND trim(industry::text) != ''", ()
            )
            old_si = int(r[0]["cnt"]) if r else 0
        except Exception:
            old_si = -1
        new_si = _count_table(dm, "sys_stock_industries")
        results.append(("stock_industries", "stock_list.industry -> sys_stock_industries", old_si, new_si))
    # K 线：按 term 比较 stock_kline 与 sys_stock_klines
    for term in ("daily", "weekly", "monthly"):
        step_id = f"kline_{term}"
        label = f"stock_kline (term={term}) -> sys_stock_klines"
        old_c = _count_table(dm, "stock_kline", "term = %s", (term,))
        new_c = _count_table(dm, "sys_stock_klines", "term = %s", (term,))
        if old_c >= 0 or new_c >= 0:
            results.append((step_id, label, old_c, new_c))
    # K 线：总行数对比（stock_kline 全表 vs sys_stock_klines 全表）
    old_kline_total = _count_table(dm, "stock_kline")
    new_kline_total = _count_table(dm, "sys_stock_klines")
    results.append(("kline_total", "stock_kline (总) -> sys_stock_klines (总)", old_kline_total, new_kline_total))
    # 指标表：stock_kline term=daily 行数 vs sys_stock_indicators
    old_indicators = _count_table(dm, "stock_kline", "term = %s", ("daily",))
    new_indicators = _count_table(dm, "sys_stock_indicators")
    results.append(("stock_indicators", "stock_kline daily -> sys_stock_indicators", old_indicators, new_indicators))
    # price_indexes 拆成多表，只比较旧表总行数与新表总行数（近似）
    old_pi = _count_table(dm, "price_indexes")
    new_cpi = _count_table(dm, "sys_cpi")
    new_ppi = _count_table(dm, "sys_ppi")
    new_pmi = _count_table(dm, "sys_pmi")
    new_ms = _count_table(dm, "sys_money_supply")
    new_pi_total = (new_cpi if new_cpi >= 0 else 0) + (new_ppi if new_ppi >= 0 else 0) + (new_pmi if new_pmi >= 0 else 0) + (new_ms if new_ms >= 0 else 0)
    results.append(("price_indexes", "price_indexes -> sys_cpi/ppi/pmi/money_supply (sum)", old_pi, new_pi_total))
    # investment_operations / investment_trades 不迁移，不参与对比
    return results


def _run_single_step(dm: DataManager, step_id: str, dry_run: bool = False) -> None:
    """仅执行指定步骤（step_id 与 run_migration 中 only 或 compare 返回的 step_id 一致）。"""
    if step_id == "kline_total":
        migrate_kline_by_term(dm, "daily", "sys_stock_klines", dry_run=dry_run)
        migrate_kline_by_term(dm, "weekly", "sys_stock_klines", dry_run=dry_run)
        migrate_kline_by_term(dm, "monthly", "sys_stock_klines", dry_run=dry_run)
        return
    if step_id == "kline_monthly":
        migrate_kline_by_term(dm, "monthly", "sys_stock_klines", dry_run=dry_run)
        return
    if step_id == "kline_weekly":
        migrate_kline_by_term(dm, "weekly", "sys_stock_klines", dry_run=dry_run)
        return
    if step_id == "kline_daily":
        migrate_kline_by_term(dm, "daily", "sys_stock_klines", dry_run=dry_run)
        return
    if step_id == "industries" or step_id == "stock_industries":
        migrate_industries_from_stock_list(dm, dry_run=dry_run)
        return
    if step_id == "stock_indicators":
        migrate_stock_indicators_from_kline(dm, dry_run=dry_run)
        return
    if step_id == "price_indexes":
        migrate_price_indexes_split(dm, dry_run=dry_run)
        return
    one_to_one_map = {
        "gdp": ("gdp", "sys_gdp", ["quarter", "gdp", "gdp_yoy", "primary_industry", "primary_industry_yoy", "secondary_industry", "secondary_industry_yoy", "tertiary_industry", "tertiary_industry_yoy"], {"date": "quarter"}, ["quarter"]),
        "lpr": ("lpr", "sys_lpr", ["date", "lpr_1_y", "lpr_5_y"], {"lpr_1y": "lpr_1_y", "lpr_5y": "lpr_5_y"}, ["date"]),
        "shibor": ("shibor", "sys_shibor", ["date", "one_night", "one_week", "one_month", "three_month", "one_year"], {"on": "one_night"}, ["date"]),
        "tag_scenario": ("tag_scenario", "sys_tag_scenario", ["id", "name", "display_name", "description", "created_at", "updated_at"], None, ["id"]),
        "tag_definition": ("tag_definition", "sys_tag_definition", ["id", "scenario_id", "name", "display_name", "description", "created_at", "updated_at"], None, ["id"]),
        "tag_value": ("tag_value", "sys_tag_value", ["entity_type", "entity_id", "tag_definition_id", "as_of_date", "start_date", "end_date", "json_value", "calculated_at"], {"definition_id": "tag_definition_id", "value": "json_value"}, ["entity_id", "tag_definition_id", "as_of_date"]),
        "system_cache": None,
        "meta_info": None,
        "stock_list": ("stock_list", "sys_stock_list", ["id", "name", "industry_id", "market_id", "board_id", "is_active", "last_update"], {"ts_code": "id"}, ["id"]),
        "adj_factor_event": ("adj_factor_event", "sys_adj_factor_events", ["id", "event_date", "factor", "qfq_diff", "last_update"], {"ts_code": "id", "ann_date": "event_date"}, ["id", "event_date"]),
        "corporate_finance": ("corporate_finance", "sys_corporate_finance", ["id", "quarter", "eps", "dt_eps", "roe_dt", "roe", "roa", "netprofit_margin", "gross_profit_margin", "op_income", "roic", "ebit", "ebitda", "dtprofit_to_profit", "profit_dedt", "or_yoy", "netprofit_yoy", "basic_eps_yoy", "dt_eps_yoy", "tr_yoy", "netdebt", "debt_to_eqt", "debt_to_assets", "interestdebt", "assets_to_eqt", "quick_ratio", "current_ratio", "ar_turn", "bps", "ocfps", "fcff", "fcfe"], {"ts_code": "id", "ann_date": "quarter"}, ["id", "quarter"]),
        "stock_index_indicator": ("stock_index_indicator", "sys_index_klines", ["id", "term", "date", "open", "close", "highest", "lowest", "price_change_delta", "price_change_rate_delta", "pre_close", "volume", "amount"], {"high": "highest", "low": "lowest"}, ["id", "term", "date"]),
        "stock_index_indicator_weight": ("stock_index_indicator_weight", "sys_index_weight", ["id", "date", "stock_id", "weight"], {"con_code": "stock_id", "trade_date": "date"}, ["id", "date", "stock_id"]),
    }
    if step_id == "system_cache":
        migrate_system_cache(dm, dry_run=dry_run)
        return
    if step_id == "meta_info":
        migrate_meta_info(dm, dry_run=dry_run)
        return
    item = one_to_one_map.get(step_id)
    if item and item is not None:
        old, new, cols, renames, unique_keys = item[0], item[1], item[2], item[3], item[4]
        migrate_one_to_one(dm, old, new, cols, renames=renames, unique_keys=unique_keys, dry_run=dry_run)
        return
    logger.warning(f"未知步骤: {step_id}")


def run_migration(dm: DataManager, dry_run: bool = False, only: Optional[str] = None) -> None:
    """按依赖顺序执行迁移。only 不为空时仅执行该步骤（如 kline_monthly / kline_weekly / kline_daily / klines）。"""
    if only == "kline_monthly":
        migrate_kline_by_term(dm, "monthly", "sys_stock_klines", dry_run=dry_run)
        return
    if only == "kline_weekly":
        migrate_kline_by_term(dm, "weekly", "sys_stock_klines", dry_run=dry_run)
        return
    if only == "kline_daily":
        migrate_kline_by_term(dm, "daily", "sys_stock_klines", dry_run=dry_run)
        return
    if only == "klines":
        migrate_kline_by_term(dm, "daily", "sys_stock_klines", dry_run=dry_run)
        migrate_kline_by_term(dm, "weekly", "sys_stock_klines", dry_run=dry_run)
        migrate_kline_by_term(dm, "monthly", "sys_stock_klines", dry_run=dry_run)
        return
    if only is not None:
        logger.warning(f"未知 MIGRATE_ONLY={only}，已忽略")
        return

    step = 0
    def _step(msg: str):
        nonlocal step
        step += 1
        logger.info(f"[{step}] {msg}")

    one_to_one = [
        ("gdp", "sys_gdp", ["quarter", "gdp", "gdp_yoy", "primary_industry", "primary_industry_yoy", "secondary_industry", "secondary_industry_yoy", "tertiary_industry", "tertiary_industry_yoy"], {"date": "quarter"}, ["quarter"]),
        ("lpr", "sys_lpr", ["date", "lpr_1_y", "lpr_5_y"], {"lpr_1y": "lpr_1_y", "lpr_5y": "lpr_5_y"}, ["date"]),
        ("shibor", "sys_shibor", ["date", "one_night", "one_week", "one_month", "three_month", "one_year"], {"on": "one_night"}, ["date"]),
        ("tag_scenario", "sys_tag_scenario", ["id", "name", "display_name", "description", "created_at", "updated_at"], None, ["id"]),
        ("tag_definition", "sys_tag_definition", ["id", "scenario_id", "name", "display_name", "description", "created_at", "updated_at"], None, ["id"]),
        ("tag_value", "sys_tag_value", ["entity_type", "entity_id", "tag_definition_id", "as_of_date", "start_date", "end_date", "json_value", "calculated_at"], {"definition_id": "tag_definition_id", "value": "json_value"}, ["entity_id", "tag_definition_id", "as_of_date"]),
    ]
    for item in one_to_one:
        old, new, cols, renames, unique_keys = item[0], item[1], item[2], item[3] if len(item) > 3 else None, item[4] if len(item) > 4 else None
        _step(f"{old} -> {new}")
        migrate_one_to_one(dm, old, new, cols, renames=renames, unique_keys=unique_keys, dry_run=dry_run)

    _step("system_cache -> sys_cache")
    migrate_system_cache(dm, dry_run=dry_run)
    _step("meta_info -> sys_meta_info")
    migrate_meta_info(dm, dry_run=dry_run)
    _step("stock_list.industry -> sys_industries + sys_stock_industries")
    migrate_industries_from_stock_list(dm, dry_run=dry_run)
    _step("stock_list -> sys_stock_list")
    migrate_stock_list(dm, dry_run=dry_run)
    _step("adj_factor_event -> sys_adj_factor_events")
    migrate_one_to_one(dm, "adj_factor_event", "sys_adj_factor_events", ["id", "event_date", "factor", "qfq_diff", "last_update"], renames={"ts_code": "id", "ann_date": "event_date"}, unique_keys=["id", "event_date"], dry_run=dry_run)
    _step("corporate_finance -> sys_corporate_finance")
    migrate_one_to_one(
        dm,
        "corporate_finance",
        "sys_corporate_finance",
        ["id", "quarter", "eps", "dt_eps", "roe_dt", "roe", "roa", "netprofit_margin", "gross_profit_margin", "op_income", "roic", "ebit", "ebitda", "dtprofit_to_profit", "profit_dedt", "or_yoy", "netprofit_yoy", "basic_eps_yoy", "dt_eps_yoy", "tr_yoy", "netdebt", "debt_to_eqt", "debt_to_assets", "interestdebt", "assets_to_eqt", "quick_ratio", "current_ratio", "ar_turn", "bps", "ocfps", "fcff", "fcfe"],
        renames={"ts_code": "id", "ann_date": "quarter"},
        unique_keys=["id", "quarter"],
        dry_run=dry_run,
    )
    _step("stock_index_indicator -> sys_index_klines")
    migrate_one_to_one(dm, "stock_index_indicator", "sys_index_klines", ["id", "term", "date", "open", "close", "highest", "lowest", "price_change_delta", "price_change_rate_delta", "pre_close", "volume", "amount"], renames={"high": "highest", "low": "lowest"}, unique_keys=["id", "term", "date"], dry_run=dry_run)
    _step("stock_index_indicator_weight -> sys_index_weight")
    migrate_one_to_one(dm, "stock_index_indicator_weight", "sys_index_weight", ["id", "date", "stock_id", "weight"], renames={"con_code": "stock_id", "trade_date": "date"}, unique_keys=["id", "date", "stock_id"], dry_run=dry_run)

    migrate_kline_by_term(dm, "daily", "sys_stock_klines", dry_run=dry_run)
    migrate_kline_by_term(dm, "weekly", "sys_stock_klines", dry_run=dry_run)
    migrate_kline_by_term(dm, "monthly", "sys_stock_klines", dry_run=dry_run)
    migrate_stock_indicators_from_kline(dm, dry_run=dry_run)
    migrate_price_indexes_split(dm, dry_run=dry_run)
    # investment_operations / investment_trades 不迁移


def main():
    dry_run = os.environ.get("MIGRATE_DRY_RUN", "").strip() == "1"
    only = os.environ.get("MIGRATE_ONLY", "").strip() or None
    compare_and_fix = os.environ.get("COMPARE_AND_FIX", "").strip() == "1"
    if dry_run:
        logger.info("MIGRATE_DRY_RUN=1：仅检查并统计，不写入新表")
    if only:
        logger.info(f"MIGRATE_ONLY={only}：仅执行该步骤")
    if compare_and_fix:
        logger.info("COMPARE_AND_FIX=1：先对比记录数，仅对不一致的步骤再次迁移")
    logger.info("数据迁移：旧表 -> sys_* 新表 ...")
    dm = DataManager(is_verbose=True)
    dm.initialize()

    if compare_and_fix:
        results = _compare_migration_counts(dm)
        logger.info("========== 记录数对比 ==========")
        mismatched = []
        for step_id, label, old_c, new_c in results:
            old_s = str(old_c) if old_c >= 0 else "N/A"
            new_s = str(new_c) if new_c >= 0 else "N/A"
            ok = (old_c >= 0 and new_c >= 0 and old_c == new_c)
            status = "✓" if ok else "✗ 不一致"
            logger.info(f"  {label}: 旧表={old_s}, 新表={new_s}  {status}")
            if not ok and old_c >= 0 and new_c >= 0 and old_c != new_c:
                mismatched.append(step_id)
            elif old_c >= 0 and new_c < 0:
                mismatched.append(step_id)
            elif old_c < 0 and new_c >= 0:
                pass  # 旧表不存在，不补迁
        # industries 与 stock_industries 同属一次迁移，只执行一次
        if "stock_industries" in mismatched and "industries" not in mismatched:
            mismatched.append("industries")
        if "stock_industries" in mismatched:
            mismatched = [s for s in mismatched if s != "stock_industries"]
        # kline_total 表示全量 K 线，执行一次即可（daily+weekly+monthly），去掉按 term 的重复项
        if "kline_total" in mismatched:
            mismatched = [s for s in mismatched if s not in ("kline_daily", "kline_weekly", "kline_monthly")]
        if not mismatched:
            logger.info("所有表记录数一致，无需再次迁移。")
        else:
            logger.info(f"将对以下 {len(mismatched)} 个步骤再次迁移: {mismatched}")
            for step_id in mismatched:
                logger.info(f"  >> 执行步骤: {step_id}")
                _run_single_step(dm, step_id, dry_run=False)
        logger.info("迁移流程结束。")
        return

    run_migration(dm, dry_run=dry_run, only=only)
    logger.info("迁移流程结束。")


if __name__ == "__main__":
    main()
