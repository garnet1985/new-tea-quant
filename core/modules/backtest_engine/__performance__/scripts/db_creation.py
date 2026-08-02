#!/usr/bin/env python3
"""Create a temporary DB and import ``fake_data/`` CSVs.

Default engine: duckdb (files under ``__performance__/.workdir/``).
Optional: ``--db mysql|pgsql`` (creates ``perf_test_tmp[_N]`` on server; registry required for clean).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parents[4]  # .../scripts → repo root
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from common import (  # noqa: E402
    FAKE_DATA_DIR,
    allocate_duckdb_base_name,
    dataset_files_present,
    duckdb_domain_paths,
    ensure_layout,
    read_dataset_meta,
    register_db_entry,
    utc_now_iso,
)
from config import (  # noqa: E402
    CSV_CALENDAR,
    CSV_KLINES,
    CSV_ST,
    CSV_STOCK_LIST,
)
from progress import Progress, step  # noqa: E402

_INSERT_BATCH = 5000


def _count_csv_data_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8", newline="") as f:
        # header + data rows
        n = sum(1 for _ in f)
    return max(0, n - 1)


def _iter_csv_batches(path: Path, size: int = _INSERT_BATCH):
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        buf: List[Dict[str, Any]] = []
        for row in reader:
            buf.append({k: (None if v == "" else v) for k, v in row.items()})
            if len(buf) >= size:
                yield buf
                buf = []
        if buf:
            yield buf


def _build_duckdb_manager(base_name: str):
    from core.infra.db import Db

    paths = duckdb_domain_paths(base_name)
    # remove stale files for this base name if any
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


def _import_tables(dm) -> Dict[str, int]:
    mapping = {
        "sys_stock_list": FAKE_DATA_DIR / CSV_STOCK_LIST,
        "sys_trade_calendar": FAKE_DATA_DIR / CSV_CALENDAR,
        "sys_stock_klines": FAKE_DATA_DIR / CSV_KLINES,
        "sys_stock_st_periods": FAKE_DATA_DIR / CSV_ST,
    }
    counts: Dict[str, int] = {}
    for table, path in mapping.items():
        model = dm.get_table(table)
        if model is None:
            raise RuntimeError(f"table not registered: {table}")
        total = _count_csv_data_rows(path)
        step(
            "db_creation",
            f"import {table} from {path.name} (~{total:,} rows)",
        )
        prog = Progress(f"db_creation/{table}", total, unit="rows")
        n = 0
        for batch in _iter_csv_batches(path):
            model.insert_many(batch)
            n += len(batch)
            prog.update(len(batch))
        prog.finish()
        counts[table] = n
    return counts


def create_duckdb(*, reuse: bool = False) -> Dict[str, Any]:
    from core.infra.db import Db
    from core.modules.data_manager import DataManager

    ensure_layout()
    if not dataset_files_present():
        raise SystemExit("fake_data missing; run data_gen.py first")

    meta = read_dataset_meta()
    if reuse:
        from common import (
            active_duckdb_entry,
            dataset_fingerprint,
            drop_duckdb_entry,
        )

        existing = active_duckdb_entry()
        if existing:
            if dataset_fingerprint(existing.get("dataset")) == dataset_fingerprint(meta):
                step(
                    "db_creation",
                    f"reuse existing duckdb entry: {existing.get('name')}",
                )
                return existing
            step(
                "db_creation",
                "fake_data 与已导入库不一致，重建 duckdb "
                f"(was stocks={((existing.get('dataset') or {}).get('stock_count'))}, "
                f"now stocks={meta.get('stock_count')})",
            )
            # release any process-wide handles before unlinking files
            try:
                from core.infra.db import Db

                Db.manager.reset_default()
            except Exception:
                pass
            DataManager.reset_instance()
            drop_duckdb_entry(existing)

    base_name = allocate_duckdb_base_name()
    db, paths = _build_duckdb_manager(base_name)

    DataManager.reset_instance()
    # singleton path so subsequent loads share this DB
    dm = DataManager(db=db, is_verbose=False)
    counts = _import_tables(dm)
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
        "dataset": meta,
        "row_counts": counts,
    }
    register_db_entry(entry)
    step("db_creation", f"created duckdb {base_name}")
    for k, v in paths.items():
        print(f"  {k}: {v}", flush=True)
    for t, n in counts.items():
        print(f"  {t}: {n:,} rows", flush=True)
    return entry


def create_server_db(engine: str) -> Dict[str, Any]:
    raise SystemExit(
        f"--db {engine} import is stubbed in this experiment pass; "
        "default duckdb first. Server DB will use name perf_test_tmp[_N] + registry."
    )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Create temp DB and import fake_data")
    p.add_argument(
        "--db",
        choices=["duckdb", "mysql", "pgsql", "postgresql"],
        default="duckdb",
        help="engine (default: duckdb)",
    )
    p.add_argument(
        "--reuse",
        action="store_true",
        help="reuse latest registered duckdb if files still exist",
    )
    args = p.parse_args(argv)
    engine = "postgresql" if args.db == "pgsql" else args.db

    if engine == "duckdb":
        create_duckdb(reuse=args.reuse)
        return 0
    create_server_db(engine)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
