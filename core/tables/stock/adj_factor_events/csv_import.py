"""
adj_factor_events CSV 冷启动导入：按 dev 契约过滤与校验。

规则（``data.json``）：
- ``use_sample_stock_list``：仅保留池内股票；池内缺股允许，renew 补全
- ``as_of_latest_completed_trading_date``：``event_date`` 截断；已导入股戳 ``last_update`` 至 as_of（除权日稀疏，``max(event)<as_of`` 仍视为 L0 已覆盖）
- ``default_start_date`` + ``sys_stock_list.list_date``：起点未覆盖的股跳过（renew 全量 refresh），其余照常导入
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = frozenset({"id", "event_date", "factor", "qfq_diff"})


class CsvImportRejected(Exception):
    """整批 CSV 导入被拒绝（表头/配置非法）。"""

    def __init__(self, message: str, *, offenders: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.offenders = offenders or []


@dataclass
class CsvImportReport:
    source_path: str = ""
    rows_read: int = 0
    rows_imported: int = 0
    stocks_in_csv: int = 0
    stocks_imported: int = 0
    stocks_dropped_outside_pool: int = 0
    pool_missing_stocks: List[str] = field(default_factory=list)
    stocks_partial_as_of: List[str] = field(default_factory=list)
    stocks_as_of_covered: List[str] = field(default_factory=list)
    stocks_skipped_start_coverage: List[str] = field(default_factory=list)
    default_start_date: str = ""
    as_of_date: Optional[str] = None
    sample_pool_active: bool = False


def _normalize_ymd(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    s = str(value).strip().replace("-", "")
    if "." in s:
        s = s.split(".", 1)[0]
    if re.fullmatch(r"\d{8}", s):
        return s
    return None


def _normalize_stock_id(value: Any) -> str:
    return str(value or "").strip()


def _covers_start_date(
    min_event_date: str,
    default_start: str,
    list_date: Optional[str],
) -> bool:
    """
    该股 CSV 是否覆盖回填起点。

    - 老股：``min(event_date) <= default_start``（须有过往除权链）
    - 新股（``list_date > default_start``）：首笔除权晚于上市日属正常，不判缺历史
    - 上市不晚于 default_start 且首笔除权晚于 default_start：缺早期链 → 不通过
    """
    ds = _normalize_ymd(default_start) or ""
    if not ds:
        return True
    if min_event_date <= ds:
        return True
    ld = _normalize_ymd(list_date)
    if ld and ld > ds:
        return True
    if ld and min_event_date <= ld:
        return True
    return False


def _parse_last_update(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    ymd = _normalize_ymd(s)
    if ymd:
        return datetime.strptime(ymd, "%Y%m%d")
    return None


def _format_last_update(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _cap_last_update_to_as_of(raw: Any, as_of: str) -> Optional[str]:
    as_of_ymd = _normalize_ymd(as_of)
    if not as_of_ymd:
        return None
    as_of_end = datetime.strptime(as_of_ymd, "%Y%m%d").replace(
        hour=23, minute=59, second=59
    )
    parsed = _parse_last_update(raw)
    if parsed is None:
        return _format_last_update(as_of_end)
    if parsed > as_of_end:
        return _format_last_update(as_of_end)
    return _format_last_update(parsed)


def validate_csv_columns(fieldnames: Optional[Iterable[str]]) -> None:
    if fieldnames is None:
        raise CsvImportRejected("CSV 无表头")
    cols = [str(c).strip() for c in fieldnames]
    if not cols:
        raise CsvImportRejected("CSV 无表头")
    missing = _REQUIRED_COLUMNS - set(cols)
    if missing:
        raise CsvImportRejected(f"CSV 缺少必需列: {sorted(missing)}")


def prepare_adj_factor_csv_import(
    raw_rows: List[Dict[str, Any]],
    *,
    default_start_date: str,
    as_of_date: Optional[str],
    pool_ids: Optional[Set[str]],
    list_date_by_id: Optional[Mapping[str, str]] = None,
    source_path: str = "",
) -> Tuple[List[Dict[str, Any]], CsvImportReport]:
    """
    按契约过滤 CSV 行；起点未覆盖的股跳过，其余导入。
    """
    report = CsvImportReport(
        source_path=source_path,
        rows_read=len(raw_rows),
        default_start_date=_normalize_ymd(default_start_date) or "",
        as_of_date=_normalize_ymd(as_of_date),
        sample_pool_active=bool(pool_ids),
    )
    list_dates = dict(list_date_by_id or {})

    normalized: List[Dict[str, Any]] = []
    dropped_outside_pool = 0
    for row in raw_rows:
        sid = _normalize_stock_id(row.get("id"))
        ed = _normalize_ymd(row.get("event_date"))
        if not sid or not ed:
            continue
        if pool_ids is not None and sid not in pool_ids:
            dropped_outside_pool += 1
            continue
        out = dict(row)
        out["id"] = sid
        out["event_date"] = ed
        normalized.append(out)

    report.stocks_dropped_outside_pool = dropped_outside_pool

    by_stock: Dict[str, List[Dict[str, Any]]] = {}
    for row in normalized:
        by_stock.setdefault(str(row["id"]), []).append(row)

    report.stocks_in_csv = len(by_stock)

    if pool_ids:
        report.pool_missing_stocks = sorted(pool_ids - set(by_stock.keys()))

    default_start = report.default_start_date
    if not default_start:
        raise CsvImportRejected("default_start_date 未配置，拒绝 CSV 导入")

    skipped_start: List[str] = []
    for sid in sorted(by_stock.keys()):
        rows = by_stock[sid]
        min_ed = min(str(r["event_date"]) for r in rows)
        ld = list_dates.get(sid)
        if not _covers_start_date(min_ed, default_start, ld):
            skipped_start.append(sid)
            del by_stock[sid]
    report.stocks_skipped_start_coverage = skipped_start

    as_of = report.as_of_date
    if as_of:
        for sid in list(by_stock.keys()):
            by_stock[sid] = [r for r in by_stock[sid] if str(r["event_date"]) <= as_of]

    out_rows: List[Dict[str, Any]] = []
    for sid, rows in sorted(by_stock.items()):
        if not rows:
            continue
        report.stocks_as_of_covered.append(sid)
        for row in rows:
            row = dict(row)
            if as_of:
                row["last_update"] = _cap_last_update_to_as_of(row.get("last_update"), as_of)
            else:
                row["last_update"] = None
            out_rows.append(row)

    report.rows_imported = len(out_rows)
    report.stocks_imported = len({str(r["id"]) for r in out_rows})
    return out_rows, report


def log_csv_import_report(report: CsvImportReport) -> None:
    logger.info(
        "adj_factor CSV 导入: %s → %d 行 / %d 股（读入 %d 行）",
        report.source_path or "<memory>",
        report.rows_imported,
        report.stocks_imported,
        report.rows_read,
    )
    if report.sample_pool_active:
        logger.info(
            "  样本池: 丢弃池外 %d 股事件，池内 CSV 缺失 %d 股（renew 将补）",
            report.stocks_dropped_outside_pool,
            len(report.pool_missing_stocks),
        )
        if report.pool_missing_stocks and len(report.pool_missing_stocks) <= 10:
            logger.info("  池内缺失: %s", ", ".join(report.pool_missing_stocks))
    if report.stocks_skipped_start_coverage:
        logger.info(
            "  起点未覆盖: 跳过 %d 股（renew 将全量 refresh）",
            len(report.stocks_skipped_start_coverage),
        )
        if len(report.stocks_skipped_start_coverage) <= 10:
            logger.info(
                "  跳过: %s",
                ", ".join(report.stocks_skipped_start_coverage),
            )
    if report.as_of_date:
        logger.info(
            "  as_of=%s: 已戳 last_update %d 股（L0 跳过）；"
            "renew 补: 池内缺失 %d + 起点跳过 %d",
            report.as_of_date,
            len(report.stocks_as_of_covered),
            len(report.pool_missing_stocks),
            len(report.stocks_skipped_start_coverage),
        )
