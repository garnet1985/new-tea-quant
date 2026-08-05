#!/usr/bin/env python3
"""Create a temporary DuckDB and inject synthetic market rows directly.

No CSV intermediate. IDs are continuous ``000000``..; OHLC follows a fixed pattern.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_CMD = Path(__file__).resolve().parent
if str(_CMD) not in sys.path:
    sys.path.insert(0, str(_CMD))
from common import (  # noqa: E402
    allocate_duckdb_base_name,
    dataset_fingerprint,
    desired_dataset_meta,
    duckdb_domain_paths,
    ensure_layout,
    register_db_entry,
    repo_root,
    utc_now_iso,
)
from config import (  # noqa: E402
    DEFAULT_END_DATE,
    DEFAULT_KLINE_TERM,
    DEFAULT_SEED,
    DEFAULT_START_DATE,
    DEFAULT_STOCK_COUNT,
)
from progress import Progress, step  # noqa: E402
from synthetic import (  # noqa: E402
    build_calendar,
    build_stock_list,
    iter_kline_batches,
    open_dates,
    stock_ids,
)

_REPO = repo_root()
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _build_duckdb_manager(base_name: str):
    from core.infra.db import Db

    paths = duckdb_domain_paths(base_name)
    for p in paths.values():
        if p.is_file():
            p.unlink()
        wal = Path(str(p) + ".wal")
        if wal.is_file():
            wal.unlink()

    step("db_creation", f"initialize duckdb base={base_name}")
    cfg = Db.duckdb.overlay_domain_paths(
        data=str(paths["data"]),
        tag=str(paths["tag"]),
        strategy=str(paths["strategy"]),
    )
    db = Db.manager.create(cfg, is_verbose=False)
    db.initialize()
    Db.manager.set_default(db)
    return db, paths


def _insert(model, rows, *, label: str) -> int:
    if not rows:
        step("db_creation", f"{label}: 0 rows")
        return 0
    step("db_creation", f"insert {label} ({len(rows):,} rows)")
    model.insert_many(rows)
    return len(rows)


def _seed_tables(dm, *, meta: Dict[str, Any]) -> Dict[str, int]:
    ids = stock_ids(int(meta["stock_count"]))
    dates = open_dates(str(meta["start_date"]), str(meta["end_date"]))
    calendar = build_calendar(str(meta["start_date"]), str(meta["end_date"]))
    stocks = build_stock_list(
        ids, list_date=str(meta["start_date"]), now=utc_now_iso()
    )

    counts: Dict[str, int] = {}
    stock_model = dm.get_table("sys_stock_list")
    cal_model = dm.get_table("sys_trade_calendar")
    kline_model = dm.get_table("sys_stock_klines")
    if stock_model is None or cal_model is None or kline_model is None:
        raise RuntimeError("required tables not registered")

    counts["sys_stock_list"] = _insert(stock_model, stocks, label="sys_stock_list")
    counts["sys_trade_calendar"] = _insert(
        cal_model, calendar, label="sys_trade_calendar"
    )

    expected = len(ids) * len(dates)
    step(
        "db_creation",
        f"insert sys_stock_klines "
        f"({len(ids)} stocks × {len(dates)} days ≈ {expected:,} rows)",
    )
    prog = Progress("db_creation/klines", expected, unit="rows")
    n_kline = 0
    for batch in iter_kline_batches(
        ids, dates, term=str(meta.get("term") or DEFAULT_KLINE_TERM)
    ):
        # empty strings → None for nullable cols consistency with old importer
        cleaned = [{k: (None if v == "" else v) for k, v in row.items()} for row in batch]
        kline_model.insert_many(cleaned)
        n_kline += len(batch)
        prog.update(len(batch))
    prog.finish()
    counts["sys_stock_klines"] = n_kline
    counts["sys_stock_st_periods"] = 0  # skipped; empty table is fine
    return counts


def create_duckdb(
    *,
    reuse: bool = False,
    stock_count: int = DEFAULT_STOCK_COUNT,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    seed: int = DEFAULT_SEED,
) -> Dict[str, Any]:
    from core.infra.db import Db
    from core.modules.data_manager import DataManager

    ensure_layout()
    desired = desired_dataset_meta(
        stock_count=stock_count,
        start_date=start_date,
        end_date=end_date,
        seed=seed,
    )

    if reuse:
        from common import active_duckdb_entry, drop_duckdb_entry

        existing = active_duckdb_entry()
        if existing:
            if dataset_fingerprint(existing.get("dataset")) == dataset_fingerprint(
                desired
            ):
                step(
                    "db_creation",
                    f"reuse existing duckdb entry: {existing.get('name')}",
                )
                return existing
            step(
                "db_creation",
                "dataset 与已有库不一致，重建 duckdb "
                f"(was stocks={((existing.get('dataset') or {}).get('stock_count'))}, "
                f"now stocks={desired.get('stock_count')})",
            )
            try:
                Db.manager.reset_default()
            except Exception:
                pass
            DataManager.reset_instance()
            drop_duckdb_entry(existing)

    base_name = allocate_duckdb_base_name()
    db, paths = _build_duckdb_manager(base_name)

    DataManager.reset_instance()
    dm = DataManager(db=db, is_verbose=False)
    counts = _seed_tables(dm, meta=desired)
    desired["open_days"] = len(
        open_dates(str(desired["start_date"]), str(desired["end_date"]))
    )
    desired["kline_rows"] = int(counts.get("sys_stock_klines") or 0)
    desired["generated_at"] = utc_now_iso()

    step("db_creation", "flush_writes…")
    try:
        db.flush_writes()
    except Exception:
        pass

    entry = {
        "engine": "duckdb",
        "name": base_name,
        "paths": {k: str(v) for k, v in paths.items()},
        "created_at": utc_now_iso(),
        "created_by": "backtest_engine.__performance__.db_creation",
        "dataset": desired,
        "row_counts": counts,
    }
    register_db_entry(entry)
    step("db_creation", f"seeded duckdb {base_name}")
    for k, v in paths.items():
        print(f"  {k}: {v}", flush=True)
    for t, n in counts.items():
        print(f"  {t}: {n:,} rows", flush=True)
    return entry


def create_server_db(engine: str) -> Dict[str, Any]:
    raise SystemExit(
        f"--db {engine} seed is stubbed; default duckdb first. "
        "Server DB will use name perf_test_tmp[_N] + registry."
    )


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(
        description="Create temp DuckDB and inject synthetic market data"
    )
    p.add_argument(
        "--db",
        choices=["duckdb", "mysql", "pgsql", "postgresql"],
        default="duckdb",
        help="engine (default: duckdb)",
    )
    p.add_argument(
        "--reuse",
        action="store_true",
        help="reuse latest registered duckdb if dataset fingerprint matches",
    )
    p.add_argument("--stocks", type=int, default=DEFAULT_STOCK_COUNT)
    p.add_argument("--start-date", default=DEFAULT_START_DATE)
    p.add_argument("--end-date", default=DEFAULT_END_DATE)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = p.parse_args(argv)
    engine = "postgresql" if args.db == "pgsql" else args.db

    if args.stocks <= 0:
        raise SystemExit("--stocks must be > 0")
    if args.start_date > args.end_date:
        raise SystemExit("date window invalid")

    if engine == "duckdb":
        create_duckdb(
            reuse=args.reuse,
            stock_count=args.stocks,
            start_date=args.start_date,
            end_date=args.end_date,
            seed=args.seed,
        )
        return 0
    create_server_db(engine)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
