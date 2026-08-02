"""BE __performance__ 共享路径与 registry（产物不离开本模块 __performance__/）。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import (
    CSV_CALENDAR,
    CSV_KLINES,
    CSV_STOCK_LIST,
    DATASET_META,
    DB_NAME_PREFIX,
    UNIVERSE_TXT,
)

PERF_ROOT = Path(__file__).resolve().parents[1]
FAKE_DATA_DIR = PERF_ROOT / "fake_data"
WORKDIR = PERF_ROOT / ".workdir"
REGISTRY_PATH = WORKDIR / "db_registry.json"
RESULTS_DIR = PERF_ROOT / "results"

_NAME_RE = re.compile(rf"^{re.escape(DB_NAME_PREFIX)}(?:_(\d+))?$")


def ensure_layout() -> None:
    FAKE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    WORKDIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_registry() -> Dict[str, Any]:
    ensure_layout()
    if not REGISTRY_PATH.is_file():
        return {"entries": []}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(registry: Dict[str, Any]) -> None:
    ensure_layout()
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def list_registry_entries(*, engine: Optional[str] = None) -> List[Dict[str, Any]]:
    entries = list(load_registry().get("entries") or [])
    if engine:
        eng = engine.lower()
        entries = [e for e in entries if str(e.get("engine", "")).lower() == eng]
    return entries


def allocate_duckdb_base_name() -> str:
    """Return next free ``perf_test_tmp`` / ``perf_test_tmp_N`` under .workdir."""
    ensure_layout()
    used = set()
    for e in list_registry_entries(engine="duckdb"):
        name = str(e.get("name") or "")
        if _NAME_RE.match(name):
            used.add(name)
    for p in WORKDIR.glob("*.duckdb"):
        stem = p.stem
        if stem.endswith("_tag"):
            stem = stem[: -len("_tag")]
        elif stem.endswith("_strategy"):
            stem = stem[: -len("_strategy")]
        if _NAME_RE.match(stem):
            used.add(stem)
    if DB_NAME_PREFIX not in used:
        return DB_NAME_PREFIX
    n = 1
    while f"{DB_NAME_PREFIX}_{n}" in used:
        n += 1
    return f"{DB_NAME_PREFIX}_{n}"


def duckdb_domain_paths(base_name: str) -> Dict[str, Path]:
    """Absolute paths for data/tag/strategy domain files under .workdir."""
    ensure_layout()
    return {
        "data": (WORKDIR / f"{base_name}.duckdb").resolve(),
        "tag": (WORKDIR / f"{base_name}_tag.duckdb").resolve(),
        "strategy": (WORKDIR / f"{base_name}_strategy.duckdb").resolve(),
    }


def register_db_entry(entry: Dict[str, Any]) -> None:
    reg = load_registry()
    entries = list(reg.get("entries") or [])
    entries.append(entry)
    reg["entries"] = entries
    save_registry(reg)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dataset_files_present() -> bool:
    needed = [
        FAKE_DATA_DIR / CSV_STOCK_LIST,
        FAKE_DATA_DIR / CSV_KLINES,
        FAKE_DATA_DIR / CSV_CALENDAR,
        FAKE_DATA_DIR / UNIVERSE_TXT,
    ]
    return all(p.is_file() for p in needed)


def read_universe() -> List[str]:
    path = FAKE_DATA_DIR / UNIVERSE_TXT
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}; run data_gen.py first")
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def read_dataset_meta() -> Dict[str, Any]:
    path = FAKE_DATA_DIR / DATASET_META
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_fingerprint(meta: Optional[Dict[str, Any]]) -> tuple:
    """Stable key for fake_data ↔ imported DB matching."""
    m = dict(meta or {})
    return (
        m.get("dataset_id"),
        m.get("seed"),
        m.get("stock_count"),
        m.get("start_date"),
        m.get("end_date"),
        m.get("open_days"),
        m.get("kline_rows"),
        m.get("term"),
    )


def active_duckdb_entry() -> Optional[Dict[str, Any]]:
    """Most recent duckdb registry entry whose data file still exists."""
    entries = list_registry_entries(engine="duckdb")
    for e in reversed(entries):
        paths = e.get("paths") or {}
        data = paths.get("data")
        if data and Path(data).is_file():
            return e
    return None


def drop_duckdb_entry(entry: Dict[str, Any]) -> None:
    """Delete duckdb files for one registry entry and remove it from registry."""
    ensure_layout()
    paths = entry.get("paths") or {}
    for key in ("data", "tag", "strategy"):
        raw = paths.get(key)
        if not raw:
            continue
        path = Path(raw)
        try:
            path.resolve().relative_to(WORKDIR.resolve())
        except ValueError:
            print(f"refuse delete outside .workdir: {path}")
            continue
        if path.is_file():
            path.unlink()
        wal = Path(str(path) + ".wal")
        if wal.is_file():
            wal.unlink()

    name = str(entry.get("name") or "")
    reg = load_registry()
    reg["entries"] = [
        e
        for e in list(reg.get("entries") or [])
        if not (
            str(e.get("engine", "")).lower() == "duckdb"
            and str(e.get("name") or "") == name
        )
    ]
    save_registry(reg)
