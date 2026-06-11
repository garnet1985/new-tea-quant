"""
data_adj_factor_event 表 Model

复权因子事件，只存储除权除息日的因子变化。
"""
from typing import List, Dict, Any, Optional, Literal, Union
from datetime import datetime
from pathlib import Path
import re
from core.infra.db import DbBaseModel
from core.tables.stock.adj_factor_events.schema import schema as _schema
from core.utils.io import csv_io, file_io


CSV_PREFERRED_COLUMNS = [
    "id",
    "event_date",
    "factor",
    "qfq_anchor",
    "raw_anchor",
    "qfq_diff",
    "last_update",
]


class DataAdjFactorEventModel(DbBaseModel):
    """复权因子事件表 Model（表名 data_adj_factor_event）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        return self.load("id = %s", (stock_id,), order_by="event_date ASC")

    def load_by_date_range(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        return self.load(
            "id = %s AND event_date BETWEEN %s AND %s",
            (stock_id, start_date.replace("-", ""), end_date.replace("-", "")),
            order_by="event_date ASC",
        )

    def load_factor_by_date(self, stock_id: str, date: str) -> Optional[Dict[str, Any]]:
        date_ymd = date.replace("-", "") if "-" in date else date
        return self.load_one(
            "id = %s AND event_date <= %s", (stock_id, date_ymd), order_by="event_date DESC"
        )

    def load_latest_factor(self, stock_id: str) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s", (stock_id,), order_by="event_date DESC")

    @staticmethod
    def _normalize_ymd(date_str: Any) -> Optional[str]:
        if date_str is None:
            return None
        s = str(date_str).replace("-", "").strip()
        if re.fullmatch(r"\d{8}", s):
            return s
        return None

    def load_effective_events_for_dates(
        self,
        stock_id: str,
        dates: List[str],
        *,
        is_strict: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        为一组日期返回“生效复权事件”映射（日期 -> 事件信息）。

        规则：
        - strict=True：仅使用 <= 当日 的最近事件；无则返回未复权。
        - strict=False：若当日前无历史事件，则用该股票最早可用事件作为起始补偿（is_inferred=True）。
        """
        normalized_dates = sorted(
            {d for d in (self._normalize_ymd(x) for x in dates) if d is not None}
        )
        if not normalized_dates:
            return {}

        max_date = normalized_dates[-1]
        events = self.load(
            "id = %s AND event_date <= %s",
            (stock_id, max_date),
            order_by="event_date ASC",
        ) or []

        earliest_event = None
        if not is_strict:
            earliest_event = self.load_one("id = %s", (stock_id,), order_by="event_date ASC")

        out: Dict[str, Dict[str, Any]] = {}
        event_idx = 0
        latest_event = None
        n = len(events)
        for d in normalized_dates:
            while event_idx < n:
                ed = self._normalize_ymd(events[event_idx].get("event_date"))
                if ed is not None and ed <= d:
                    latest_event = events[event_idx]
                    event_idx += 1
                else:
                    break

            selected = latest_event
            inferred = False
            if selected is None and (not is_strict) and earliest_event is not None:
                selected = earliest_event
                inferred = True

            if selected is None:
                out[d] = {
                    "event": None,
                    "qfq_diff": 0.0,
                    "is_adjusted": False,
                    "is_inferred": False,
                }
            else:
                qfq_diff = selected.get("qfq_diff") or 0.0
                out[d] = {
                    "event": selected,
                    "qfq_diff": qfq_diff,
                    "is_adjusted": True,
                    "is_inferred": inferred,
                }
        return out

    def load_effective_events_from_join_rows(
        self,
        *,
        stock_id: str,
        rows: List[Dict[str, Any]],
        is_strict: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        基于 K 线 JOIN 结果（含 adj_* 列）构建生效事件映射，尽量避免再次查库。

        约定：
        - strict=True：仅使用 join 中已命中的历史事件；
        - strict=False：
          - 若当前日期未命中历史事件，优先使用同批 rows 中最早命中的事件补偿；
          - 若整批 rows 都未命中，则回退到 load_effective_events_for_dates 查最早可用事件。
        """
        dates = [self._normalize_ymd(r.get("date")) for r in rows if r.get("date")]
        normalized_dates = sorted({d for d in dates if d is not None})
        if not normalized_dates:
            return {}

        has_join_columns = any(
            ("adj_event_date" in r) or ("adj_qfq_diff" in r) or ("adj_factor" in r)
            for r in rows
        )
        if not has_join_columns:
            return self.load_effective_events_for_dates(
                stock_id=stock_id,
                dates=normalized_dates,
                is_strict=is_strict,
            )

        # 先从 JOIN 结果提取“已命中的历史事件”
        by_date: Dict[str, Dict[str, Any]] = {}
        first_join_event: Optional[Dict[str, Any]] = None
        for row in rows:
            d = self._normalize_ymd(row.get("date"))
            if d is None:
                continue
            adj_event_date = self._normalize_ymd(row.get("adj_event_date"))
            qfq_diff = row.get("adj_qfq_diff") or 0.0

            if adj_event_date is not None:
                event = {
                    "id": row.get("id", stock_id),
                    "event_date": adj_event_date,
                    "factor": row.get("adj_factor"),
                    "qfq_anchor": row.get("adj_qfq_anchor"),
                    "raw_anchor": row.get("adj_raw_anchor"),
                    "qfq_diff": qfq_diff,
                }
                by_date[d] = {
                    "event": event,
                    "qfq_diff": qfq_diff,
                    "is_adjusted": True,
                    "is_inferred": False,
                }
                if first_join_event is None:
                    first_join_event = event

        # strict：仅保留命中，否则未复权
        if is_strict:
            out: Dict[str, Dict[str, Any]] = {}
            for d in normalized_dates:
                out[d] = by_date.get(
                    d,
                    {"event": None, "qfq_diff": 0.0, "is_adjusted": False, "is_inferred": False},
                )
            return out

        # default：先用同批 rows 中最早命中事件补齐；整批未命中时回退查库
        if first_join_event is None:
            return self.load_effective_events_for_dates(
                stock_id=stock_id,
                dates=normalized_dates,
                is_strict=False,
            )

        out = {}
        for d in normalized_dates:
            if d in by_date:
                out[d] = by_date[d]
            else:
                out[d] = {
                    "event": first_join_event,
                    "qfq_diff": first_join_event.get("qfq_diff") or 0.0,
                    "is_adjusted": True,
                    "is_inferred": True,
                }
        return out

    def save_events(self, events: List[Dict[str, Any]]) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        normalized: List[Dict[str, Any]] = []
        for e in events:
            row = dict(e)
            row.setdefault("last_update", now)
            if "event_date" in row:
                row["event_date"] = str(row["event_date"]).replace("-", "")[:8]
            normalized.append(row)
        return self.upsert_many(normalized, unique_keys=["id", "event_date"])

    def _parse_event_date_window(self, condition: str, params: tuple) -> Optional[tuple[str, str]]:
        """
        仅在形如 `event_date >= %s AND event_date <= %s` 的窗口条件下返回 (start, end)。
        """
        if len(params) < 2:
            return None
        normalized = re.sub(r"\s+", " ", (condition or "").strip().lower())
        if "event_date >= %s" not in normalized or "event_date <= %s" not in normalized:
            return None
        start_date = str(params[0])
        end_date = str(params[1])
        if not re.fullmatch(r"\d{8}", start_date) or not re.fullmatch(r"\d{8}", end_date):
            return None
        if start_date > end_date:
            return None
        return start_date, end_date

    def _build_rows_with_start_anchor(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        对窗口数据补齐起点锚点：
        - 先取窗口内事件；
        - 每个股票补一条 start_date 事件（优先 <= start_date 最近，否则 > start_date 最早）。
        """
        db = self.db
        if db is None:
            raise RuntimeError(f"{self.table_name} model 不可用：缺少 db 连接")

        stock_rows = db.execute_sync_query(
            """
            SELECT DISTINCT id
            FROM sys_stock_klines
            WHERE date >= %s AND date <= %s
            ORDER BY id ASC
            """,
            (start_date, end_date),
        )
        stock_ids = [r.get("id") for r in stock_rows or [] if r.get("id")]

        by_pk: Dict[tuple[str, str], Dict[str, Any]] = {}
        if stock_ids:
            placeholders = ",".join(["%s"] * len(stock_ids))
            in_range_rows = db.execute_sync_query(
                f"""
                SELECT id, event_date, factor, qfq_anchor, raw_anchor, qfq_diff, last_update
                FROM {self.table_name}
                WHERE id IN ({placeholders})
                  AND event_date >= %s
                  AND event_date <= %s
                ORDER BY id ASC, event_date ASC
                """,
                tuple(stock_ids) + (start_date, end_date),
            )
            for row in in_range_rows or []:
                sid = row.get("id")
                ed = row.get("event_date")
                if not sid or not ed:
                    continue
                by_pk[(sid, str(ed))] = dict(row)

        for sid in stock_ids:
            prev = db.execute_sync_query(
                f"""
                SELECT id, event_date, factor, qfq_anchor, raw_anchor, qfq_diff, last_update
                FROM {self.table_name}
                WHERE id = %s AND event_date <= %s
                ORDER BY event_date DESC
                LIMIT 1
                """,
                (sid, start_date),
            )
            anchor = prev[0] if prev else None
            if not anchor:
                nxt = db.execute_sync_query(
                    f"""
                    SELECT id, event_date, factor, qfq_anchor, raw_anchor, qfq_diff, last_update
                    FROM {self.table_name}
                    WHERE id = %s AND event_date > %s
                    ORDER BY event_date ASC
                    LIMIT 1
                    """,
                    (sid, start_date),
                )
                anchor = nxt[0] if nxt else None

            if not anchor:
                continue

            k = (sid, start_date)
            if k not in by_pk:
                by_pk[k] = {
                    "id": sid,
                    "event_date": start_date,
                    "factor": anchor.get("factor"),
                    "qfq_anchor": anchor.get("qfq_anchor"),
                    "raw_anchor": anchor.get("raw_anchor"),
                    "qfq_diff": anchor.get("qfq_diff"),
                    "last_update": anchor.get("last_update"),
                }

        return sorted(by_pk.values(), key=lambda r: (str(r.get("id", "")), str(r.get("event_date", ""))))

    def export_data(
        self,
        output_dir: Union[str, Path],
        *,
        archive_format: Literal["tar.gz", "zip"] = "tar.gz",
        template=None,
        condition: str = "1=1",
        params: tuple = (),
    ) -> List[Path]:
        """
        覆盖导出逻辑：在 event_date 时间窗口导出时，补齐 start_date 锚点事件。
        其他情况回退到基类通用导出。
        """
        window = self._parse_event_date_window(condition, params)
        if not window:
            return super().export_data(
                output_dir,
                archive_format=archive_format,
                template=template,
                condition=condition,
                params=params,
            )

        start_date, end_date = window
        rows = self._build_rows_with_start_anchor(start_date, end_date)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_bytes = csv_io.dicts_to_csv_bytes(rows)
        archive_path = file_io.write_archive(
            out_dir,
            archive_name=self.table_name,
            files={f"{self.table_name}.csv": csv_bytes},
            format="tar.gz" if archive_format == "tar.gz" else "zip",
        )
        return [archive_path]

    def update_last_update_for_stock(self, stock_id: str) -> int:
        """仅更新指定股票的 last_update 时间戳（无复权变化时调用）。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.execute_raw_update(
            "UPDATE sys_adj_factor_events SET last_update = %s WHERE id = %s",
            (now, stock_id),
        )

    @property
    def csv_dir(self) -> Path:
        """季度/全量 CSV 默认目录（userspace handler）。"""
        from core.infra.project_context import PathManager

        d = PathManager.data_source_handler("adj_factor_event")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def load_stock_last_update_map(self) -> Dict[str, Any]:
        """每股 ``MAX(last_update)``，用于交易日门控与断点补漏。"""
        rows = self.db.execute_sync_query(
            f"SELECT id, MAX(last_update) AS last_update "
            f"FROM {self.table_name} GROUP BY id",
            (),
        )
        out: Dict[str, Any] = {}
        for row in rows or []:
            sid = str((row or {}).get("id") or "").strip()
            if sid:
                out[sid] = row.get("last_update")
        return out

    def get_min_event_date(self) -> Optional[str]:
        rows = self.db.execute_sync_query(
            f"SELECT MIN(event_date) AS min_d FROM {self.table_name}", ()
        )
        if not rows or rows[0].get("min_d") is None:
            return None
        return str(rows[0]["min_d"])

    def get_max_event_date(self) -> Optional[str]:
        rows = self.db.execute_sync_query(
            f"SELECT MAX(event_date) AS max_d FROM {self.table_name}", ()
        )
        if not rows or rows[0].get("max_d") is None:
            return None
        return str(rows[0]["max_d"])

    def get_current_quarter_csv_name(self, base_date: Optional[str] = None) -> str:
        """``adj_factor_events_YYYYQn.csv``（base_date 默认今天）。"""
        from core.utils.date import DateUtils

        if base_date:
            d = str(base_date).replace("-", "")[:8]
        else:
            d = datetime.now().strftime("%Y%m%d")
        return f"adj_factor_events_{DateUtils.get_current_quarter(d)}.csv"

    def get_latest_csv_file(self) -> Optional[str]:
        """``csv_dir`` 下最新的 ``adj_factor_events_*.csv``。"""
        files = sorted(self.csv_dir.glob("adj_factor_events_*.csv"), key=lambda p: p.stat().st_mtime)
        return str(files[-1]) if files else None

    def export_to_csv(
        self,
        *,
        file_path: Union[str, Path],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """导出事件到 CSV；默认从库内最早 ``event_date`` 到最新。"""
        start = (
            str(start_date).replace("-", "")[:8]
            if start_date
            else self.get_min_event_date()
        )
        end = end_date or self.get_max_event_date()
        if not start or not end:
            csv_io.write_dicts_to_csv(file_path, [], preferred_order=CSV_PREFERRED_COLUMNS)
            return 0
        rows = self.load(
            "event_date >= %s AND event_date <= %s",
            (start, str(end).replace("-", "")[:8]),
            order_by="id ASC, event_date ASC",
        )
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        csv_io.write_dicts_to_csv(
            path,
            rows,
            preferred_order=CSV_PREFERRED_COLUMNS,
        )
        return len(rows)

    def import_from_csv(self, file_path: Optional[str] = None) -> int:
        """从 CSV 导入（默认 ``get_latest_csv_file()``）。"""
        import pandas as pd

        path = Path(file_path) if file_path else Path(self.get_latest_csv_file() or "")
        if not path.is_file():
            return 0
        df = pd.read_csv(path)
        events = df.to_dict("records")
        return self.save_events(events)
