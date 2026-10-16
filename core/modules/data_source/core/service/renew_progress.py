"""
数据源已经更新到哪一天。

计划和下一次要拉的起点都读 sys_meta_data_renew_progress，不再对业务表做 GROUP BY。
已有库第一次使用时，按业务表现有的最大日期补记一次。
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.infra.project_context import ProjectContext

logger = logging.getLogger(__name__)

TABLE_NAME = "sys_meta_data_renew_progress"
GLOBAL_ENTITY = "_global"
MARKER_SOURCE = "__renew_progress__"
MARKER_ENTITY = "backfill"
MARKER_DATE = "done"
KLINE_TERMS = ("daily", "weekly", "monthly")
DEMO_END = "20251231"
PAID_POINTS = 1000
_PROFILE_TTL_SECONDS = 60
_BACKFILL_RETRY_SECONDS = 60

_lock = threading.Lock()
_profile_cache: Dict[str, Any] = {"at": 0.0, "cap": DEMO_END, "loaded": False}
_backfill_failed_until = 0.0
_cap_logged = False


def plain_date(value: Any) -> str:
    """把库里的日期收成 YYYYMMDD、YYYYMM 或 2025Q4。"""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    if not text:
        return ""
    upper = text.upper().replace("-", "")
    if "Q" in upper:
        return upper
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        return digits[:8]
    if len(digits) >= 6:
        return digits[:6]
    return text


def keep_forward(current: str, proposed: str) -> str:
    """已经更新到的日期只允许改得更晚。"""
    current = (current or "").strip()
    proposed = (proposed or "").strip()
    if not proposed:
        return current
    if not current or proposed > current:
        return proposed
    return current


def apply_member_cap(day: str, cap: Optional[str]) -> str:
    """data.json 给出的截止日，再被会员能拿到的最后一天挡住。"""
    day = (day or "").strip()
    if cap and (not day or day > cap):
        return cap
    return day


def fold_progress(rows: Sequence[Dict[str, Any]], *, termed: bool) -> Dict[str, str]:
    """
    收成 {实体: 已经更新到的数据日期}。

    有周期时，日、周、月都有记录才算这个实体更新过，日期取三者里最早的一天。
    缺任何一个周期，这个实体就不出现在结果里，下次从默认起点拉。
    """
    if not termed:
        folded: Dict[str, str] = {}
        for row in rows:
            entity = str(row.get("entity_id") or "").strip()
            updated = str(row.get("last_update_date") or "").strip()
            if entity and updated:
                folded[entity] = updated
        return folded

    by_entity: Dict[str, Dict[str, str]] = {}
    for row in rows:
        entity = str(row.get("entity_id") or "").strip()
        term = str(row.get("term") or "").strip()
        updated = str(row.get("last_update_date") or "").strip()
        if entity and term and updated:
            by_entity.setdefault(entity, {})[term] = updated
    folded = {}
    for entity, terms in by_entity.items():
        dates: List[str] = []
        complete = True
        for term in KLINE_TERMS:
            value = terms.get(term)
            if not value:
                complete = False
                break
            dates.append(value)
        if complete:
            folded[entity] = min(dates)
    return folded


def member_end_cap() -> Optional[str]:
    """
    点数不满 1000、没有凭证、凭证被拒绝，或点数暂时读不到时，截止到 20251231。
    点数达到 1000 则不再加这一层。结果缓存一小会儿，避免每个数据源都去问一次官网。
    """
    global _cap_logged
    now = time.monotonic()
    if _profile_cache.get("loaded") and now - float(_profile_cache["at"]) < _PROFILE_TTL_SECONDS:
        return _profile_cache["cap"]
    from core.modules.ntq_external.member_profile import member_profile

    profile = member_profile()
    signed_in = bool(profile.get("signed_in"))
    points = profile.get("points")
    if signed_in and isinstance(points, int) and points >= PAID_POINTS:
        cap: Optional[str] = None
    else:
        cap = DEMO_END
        if not _cap_logged:
            _cap_logged = True
            if profile.get("reason") == "unreachable":
                logger.info("会员点数暂时读不到，更新截止按 %s", DEMO_END)
            elif not signed_in:
                logger.info("当前没有可用会员凭证，更新截止按 %s", DEMO_END)
            else:
                logger.info("会员点数未满 %s，更新截止按 %s", PAID_POINTS, DEMO_END)
    _profile_cache["at"] = now
    _profile_cache["cap"] = cap
    _profile_cache["loaded"] = True
    return cap


def resolve_uptodate_day(data_manager=None) -> str:
    """
    这次计划和“是否还要更新”用的截止数据日。

    先取 data.json 的 as_of，并落到该日或之前最近的开市日；没配 as_of 就用交易日历。
    然后再被会员能拿到的最后一天挡住。
    """
    return apply_member_cap(_market_day(data_manager), member_end_cap())


def ensure_backfill(data_manager) -> bool:
    """
    进度表里还没有补记标记时，按各业务表现有最大日期写一次。

    补记中途失败不写标记，下次还会再试。已经补记过则直接返回。
    """
    global _backfill_failed_until
    if data_manager is None:
        return False
    with _lock:
        model = _progress_model(data_manager)
        if model is None:
            return False
        if _marker_exists(model):
            return True
        now = time.monotonic()
        if now < _backfill_failed_until:
            return False
        try:
            _run_backfill(data_manager, model)
        except Exception:
            _backfill_failed_until = time.monotonic() + _BACKFILL_RETRY_SECONDS
            logger.warning("补记更新进度失败，这次仍按原表统计", exc_info=True)
            return False
        return True


def last_updates_for(data_manager, config) -> Optional[Dict[str, str]]:
    """
    这个数据源各实体已经更新到的数据日期。

    进度表还不可用时返回 None，调用方继续扫业务表。
    补记完成后，没有记录就返回空字典，表示这些实体都还没更新过。
    """
    if data_manager is None or config is None:
        return None
    if not ensure_backfill(data_manager):
        return None
    source = ""
    if hasattr(config, "get_data_source_key"):
        source = str(config.get_data_source_key() or "").strip()
    if not source:
        return None
    model = _progress_model(data_manager)
    if model is None:
        return None
    rows = model.load("source = %s", (source,)) or []
    if not isinstance(rows, list):
        return None
    return fold_progress(rows, termed=_source_is_termed(data_manager, config))


def remember_written_rows(handler: Any, rows: Sequence[Dict[str, Any]]) -> None:
    """一批行已经写入后，把其中出现的实体和周期推进到这批里最晚的数据日期。"""
    if not rows or _is_dry_run(handler):
        return
    config = _config(handler)
    source = _source_key(handler)
    if config is None or not source:
        return
    date_field = config.get_date_field()
    if not date_field:
        return
    per_entity = bool(config.get_needs_stock_grouping() or config.is_per_entity())
    entity_field = config.get_group_by_key() or "id"
    termed = _handler_has_term(handler)
    proposed: Dict[Tuple[str, str], str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        updated = plain_date(row.get(date_field))
        if not updated:
            continue
        if per_entity:
            entity = str(row.get(entity_field) or row.get("id") or "").strip()
            if not entity:
                continue
        else:
            entity = GLOBAL_ENTITY
        term = str(row.get("term") or "").strip() if termed else ""
        key = (entity, term)
        proposed[key] = keep_forward(proposed.get(key, ""), updated)
    _write_forward(_progress_model(_manager(handler)), source, proposed)


def remember_settled(handler: Any, entity_id: Optional[str], settled: str) -> None:
    """
    官网说这个区间已经读完。

    有周期的股票把日、周、月都推进到这个数据日期，这样停牌日没 K 线也不会一直显示要更新。
    整表数据源只推进 _global。
    """
    updated = plain_date(settled)
    if not updated or _is_dry_run(handler):
        return
    source = _source_key(handler)
    if not source:
        return
    entity = str(entity_id or "").strip() or GLOBAL_ENTITY
    if entity != GLOBAL_ENTITY and _handler_has_term(handler):
        terms: Iterable[str] = KLINE_TERMS
    else:
        terms = ("",)
    proposed = {(entity, term): updated for term in terms}
    _write_forward(_progress_model(_manager(handler)), source, proposed)


def _market_day(data_manager) -> str:
    configured = ProjectContext.config.get_as_of_latest_completed_trading_date()
    if configured:
        if data_manager and getattr(data_manager, "_data_service", None):
            try:
                derived = data_manager.service.calendar._derive_completed_from_trade_calendar(
                    as_of_date=configured
                )
                if derived:
                    return str(derived).strip()
            except Exception:
                logger.debug("as_of 没能落到开市日", exc_info=True)
        return str(configured).strip()
    if data_manager and getattr(data_manager, "_data_service", None):
        try:
            return str(
                data_manager.service.calendar.get_latest_completed_trading_date() or ""
            ).strip()
        except Exception:
            logger.warning("读取最近开市日失败", exc_info=True)
    return ""


def _run_backfill(data_manager, model) -> None:
    logger.info("已有数据还没记过更新进度，正在按各表里最晚的数据日期补记")
    total = 0
    for source, config in _enabled_sources():
        count = _backfill_source(data_manager, model, source, config)
        total += count
        if count:
            logger.info("补记 %s：%s 条", source, count)
    model.save_records([
        {
            "source": MARKER_SOURCE,
            "entity_id": MARKER_ENTITY,
            "term": "",
            "last_update_date": MARKER_DATE,
        }
    ])
    logger.info("更新进度已补记完成，共 %s 条", total)


def _enabled_sources():
    from core.modules.data_source.core.data_source_manager import DataSourceManager

    manager = DataSourceManager()
    mappings = manager._discover_mappings()
    for source in mappings.get_enabled().keys():
        config = manager._discover_config(source)
        if config is not None:
            yield source, config


def _backfill_source(data_manager, progress, source: str, config) -> int:
    date_field = config.get_date_field()
    if not date_field:
        return 0
    table_name = config.get_table_name()
    fact = data_manager.get_table(table_name)
    if fact is None:
        raise RuntimeError(f"{source}：无法加载表 {table_name}")
    termed = _schema_has(fact, "term")
    per_entity = bool(config.get_needs_stock_grouping() or config.is_per_entity())
    records: List[Dict[str, str]] = []
    if not per_entity:
        latest = fact.load_one("1=1", order_by=f"{date_field} DESC")
        updated = plain_date((latest or {}).get(date_field))
        if updated:
            records.append(_progress_row(source, GLOBAL_ENTITY, "", updated))
    else:
        groups = list(config.get_group_fields() or ["id"])
        if termed and "term" not in groups:
            groups.append("term")
        entity_field = groups[0]
        found = fact.load_latests(date_field, groups) or []
        if not found and fact.load_one("1=1"):
            raise RuntimeError(f"{source}：表 {table_name} 有数据，但没能读出每个实体已经更新到的日期")
        for item in found:
            entity = str(item.get(entity_field) or "").strip()
            updated = plain_date(item.get(date_field))
            term = str(item.get("term") or "").strip() if termed else ""
            if entity and updated:
                records.append(_progress_row(source, entity, term, updated))
    for chunk in _chunks(records, 1000):
        progress.save_records(chunk)
    return len(records)


def _write_forward(model, source: str, proposed: Dict[Tuple[str, str], str]) -> None:
    if model is None or not proposed:
        return
    entities = sorted({entity for entity, _term in proposed})
    existing: Dict[Tuple[str, str], str] = {}
    for chunk in _chunks(entities, 500):
        marks = ", ".join(["%s"] * len(chunk))
        rows = model.load(
            f"source = %s AND entity_id IN ({marks})",
            tuple([source, *chunk]),
        ) or []
        for row in rows:
            existing[(str(row.get("entity_id") or ""), str(row.get("term") or ""))] = str(
                row.get("last_update_date") or ""
            )
    records = []
    for key, updated in proposed.items():
        nxt = keep_forward(existing.get(key, ""), updated)
        if nxt and nxt != existing.get(key, ""):
            records.append(_progress_row(source, key[0], key[1], nxt))
    for chunk in _chunks(records, 1000):
        model.save_records(chunk)


def _progress_row(source: str, entity: str, term: str, updated: str) -> Dict[str, str]:
    return {
        "source": source,
        "entity_id": entity,
        "term": term or "",
        "last_update_date": updated,
    }


def _progress_model(data_manager):
    if data_manager is None:
        return None
    try:
        return data_manager.get_table(TABLE_NAME)
    except Exception:
        logger.debug("读取更新进度表失败", exc_info=True)
        return None


def _marker_exists(model) -> bool:
    row = model.load_one(
        "source = %s AND entity_id = %s AND term = %s",
        (MARKER_SOURCE, MARKER_ENTITY, ""),
    )
    if not isinstance(row, dict):
        return False
    return (
        str(row.get("entity_id") or "") == MARKER_ENTITY
        and str(row.get("last_update_date") or "") == MARKER_DATE
    )


def _source_is_termed(data_manager, config) -> bool:
    if not (config.get_needs_stock_grouping() or config.is_per_entity()):
        return False
    fact = data_manager.get_table(config.get_table_name())
    return _schema_has(fact, "term")


def _handler_has_term(handler: Any) -> bool:
    config = _config(handler)
    manager = _manager(handler)
    if config is None or manager is None:
        return False
    fact = manager.get_table(config.get_table_name())
    return _schema_has(fact, "term")


def _schema_has(model, field_name: str) -> bool:
    if model is None or not hasattr(model, "load_schema"):
        return False
    schema = model.load_schema() or {}
    if not isinstance(schema, dict):
        return False
    fields = schema.get("fields") or []
    if not isinstance(fields, list):
        return False
    for field in fields:
        if isinstance(field, dict) and field.get("name") == field_name:
            return True
    return False


def _config(handler: Any):
    context = getattr(handler, "context", None) or {}
    return context.get("config")


def _manager(handler: Any):
    context = getattr(handler, "context", None) or {}
    manager = context.get("data_manager")
    if manager is not None:
        return manager
    from core.modules.data_manager import DataManager

    return DataManager.get_instance()


def _source_key(handler: Any) -> str:
    get_key = getattr(handler, "get_key", None)
    if not callable(get_key):
        return ""
    return str(get_key() or "").strip()


def _is_dry_run(handler: Any) -> bool:
    context = getattr(handler, "context", None) or {}
    return bool(context.get("is_dry_run"))


def _chunks(items: Sequence[Any], size: int):
    chunk: List[Any] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
