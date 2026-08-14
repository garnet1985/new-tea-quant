"""BE __performance__ 共享路径与 registry（产物不离开本模块 __performance__/）。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import (
    DATASET_ID,
    DB_NAME_PREFIX,
    DEFAULT_END_DATE,
    DEFAULT_KLINE_TERM,
    DEFAULT_SEED,
    DEFAULT_START_DATE,
    DEFAULT_STOCK_COUNT,
    SCALE_FRACTIONS,
)

# cmd/ → scripts/ → __performance__/
PERF_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = PERF_ROOT / ".db"
REGISTRY_PATH = DB_DIR / "db_registry.json"
RESULTS_DIR = PERF_ROOT / "results"  # legacy local scratch (gitignore)
REPORTS_DIR = PERF_ROOT / "reports"  # versioned archives + templates
TEST_STRATEGIES_DIR = PERF_ROOT / "scripts" / "test_strategies"

# Report folder names (user-facing); keep postgresql → pgsql.
_REPORT_ENGINE_DIR = {
    "duckdb": "duckdb",
    "mysql": "mysql",
    "postgresql": "pgsql",
    "pgsql": "pgsql",
}

_NAME_RE = re.compile(rf"^{re.escape(DB_NAME_PREFIX)}(?:_(\d+))?$")

_MODE_STRATEGY_DIR = {
    "entity_based": "entity_based",
    "slice_based": "slice_based",
}


def assert_safe_perf_db_name(name: str) -> str:
    """Only ``perf_test_tmp`` / ``perf_test_tmp_N`` may be created or dropped."""
    name = str(name or "").strip()
    if not _NAME_RE.match(name):
        raise SystemExit(
            f"拒绝操作非性能测试库名 {name!r} "
            f"（仅允许 {DB_NAME_PREFIX} / {DB_NAME_PREFIX}_N）。"
        )
    return name


def ensure_layout() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def report_engine_dirname(engine: str) -> str:
    eng = str(engine or "duckdb").strip().lower()
    if eng == "pgsql":
        eng = "postgresql"
    return _REPORT_ENGINE_DIR.get(eng, eng or "duckdb")


def read_yaml_version(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("version:"):
            return s.split(":", 1)[1].strip().strip("\"'")
    return None


def be_module_version() -> str:
    root = repo_root()
    ver = read_yaml_version(
        root / "core" / "modules" / "backtest_engine" / "module_info.yaml"
    )
    return ver or "unknown"


def collect_perf_versions() -> Dict[str, Any]:
    """BE + core + key dependency module versions for archive labeling."""
    root = repo_root()
    core_ver: Optional[str] = None
    try:
        from core.infra.project_context import ProjectContext

        core_ver = ProjectContext.meta.core_version()
    except Exception:
        meta = root / "core" / "core_meta.json"
        if meta.is_file():
            try:
                core_ver = str(json.loads(meta.read_text(encoding="utf-8")).get("version") or "") or None
            except (OSError, json.JSONDecodeError, TypeError):
                core_ver = None

    modules = {
        "backtest_engine": be_module_version(),
        "data_manager": read_yaml_version(
            root / "core" / "modules" / "data_manager" / "module_info.yaml"
        ),
        "strategy": read_yaml_version(
            root / "core" / "modules" / "strategy" / "module_info.yaml"
        ),
        "data_contract": read_yaml_version(
            root / "core" / "modules" / "data_contract" / "module_info.yaml"
        ),
    }
    return {
        "backtest_engine": modules["backtest_engine"],
        "core": core_ver or "unknown",
        "dependencies": {k: v for k, v in modules.items() if k != "backtest_engine"},
    }


def scale_stock_counts(max_stocks: int) -> List[int]:
    """Derive run sizes from max entity count × SCALE_FRACTIONS (deduped, ascending)."""
    n_max = max(1, int(max_stocks))
    out: List[int] = []
    for frac in SCALE_FRACTIONS:
        n = max(1, int(round(float(frac) * n_max)))
        n = min(n, n_max)
        if n not in out:
            out.append(n)
    if n_max not in out:
        out.append(n_max)
    return sorted(out)


def report_sample_dirname(stock_count: int) -> str:
    return f"N{int(stock_count)}"


def report_out_dir(
    *,
    be_version: str,
    mode: str,
    engine: str,
    stock_count: int,
) -> Path:
    """reports/{BE_version}/{mode}/N{stocks}/{duckdb|mysql|pgsql}/"""
    ver = str(be_version or "unknown").strip() or "unknown"
    return (
        REPORTS_DIR
        / ver
        / str(mode)
        / report_sample_dirname(stock_count)
        / report_engine_dirname(engine)
    )


def report_mode_dir(*, be_version: str, mode: str) -> Path:
    """reports/{BE_version}/{mode}/（放 OVERALL.md）"""
    ver = str(be_version or "unknown").strip() or "unknown"
    return REPORTS_DIR / ver / str(mode)


def report_fill_templates_dir() -> Path:
    """Human guides + machine fill templates live under reports/."""
    return REPORTS_DIR


def case_report_template_path() -> Path:
    return report_fill_templates_dir() / "CASE_REPORT.md"


def overall_report_template_path() -> Path:
    return report_fill_templates_dir() / "OVERALL_TEMPLATE.md"


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
    """Return next free ``perf_test_tmp`` / ``perf_test_tmp_N`` under .db."""
    ensure_layout()
    used = set()
    for e in list_registry_entries(engine="duckdb"):
        name = str(e.get("name") or "")
        if _NAME_RE.match(name):
            used.add(name)
    for p in DB_DIR.glob("*.duckdb"):
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
    """Absolute paths for data/tag/strategy domain files under .db."""
    ensure_layout()
    return {
        "data": (DB_DIR / f"{base_name}.duckdb").resolve(),
        "tag": (DB_DIR / f"{base_name}_tag.duckdb").resolve(),
        "strategy": (DB_DIR / f"{base_name}_strategy.duckdb").resolve(),
    }


def register_db_entry(entry: Dict[str, Any]) -> None:
    reg = load_registry()
    entries = list(reg.get("entries") or [])
    entries.append(entry)
    reg["entries"] = entries
    save_registry(reg)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def desired_dataset_meta(
    *,
    stock_count: int = DEFAULT_STOCK_COUNT,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    seed: int = DEFAULT_SEED,
    open_days: Optional[int] = None,
    kline_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Canonical dataset descriptor used for reuse fingerprint + run.py."""
    from synthetic import open_dates, stock_ids

    dates = open_dates(start_date, end_date)
    ids = stock_ids(stock_count)
    n_open = len(dates) if open_days is None else int(open_days)
    n_kline = (len(ids) * n_open) if kline_rows is None else int(kline_rows)
    return {
        "dataset_id": DATASET_ID,
        "seed": int(seed),
        "stock_count": int(stock_count),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "open_days": n_open,
        "kline_rows": n_kline,
        "term": DEFAULT_KLINE_TERM,
        "id_scheme": "continuous_000000",
        "inject": "direct",
    }


def dataset_fingerprint(meta: Optional[Dict[str, Any]]) -> tuple:
    """Stable key for desired config ↔ seeded DB matching."""
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
        m.get("id_scheme"),
        m.get("inject"),
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


def read_dataset_meta(*, engine: Optional[str] = None) -> Dict[str, Any]:
    """Dataset meta from active registry entry (duckdb by default, or given engine)."""
    eng = str(engine or "duckdb").lower()
    if eng == "pgsql":
        eng = "postgresql"
    entry = active_perf_entry(engine=eng)
    if not entry:
        return {}
    meta = entry.get("dataset")
    return dict(meta) if isinstance(meta, dict) else {}


def active_perf_entry(*, engine: str) -> Optional[Dict[str, Any]]:
    eng = str(engine or "").lower()
    if eng == "pgsql":
        eng = "postgresql"
    if eng == "duckdb":
        return active_duckdb_entry()
    if eng == "mysql":
        from mysql_support import active_mysql_entry

        return active_mysql_entry()
    if eng == "postgresql":
        from postgresql_support import active_postgresql_entry

        return active_postgresql_entry()
    entries = list_registry_entries(engine=eng)
    return entries[-1] if entries else None


def universe_ids_from_meta(meta: Optional[Dict[str, Any]] = None) -> List[str]:
    from synthetic import stock_ids

    m = meta if meta is not None else read_dataset_meta()
    return stock_ids(int(m.get("stock_count") or DEFAULT_STOCK_COUNT))


def open_dates_from_meta(meta: Optional[Dict[str, Any]] = None) -> List[str]:
    from synthetic import open_dates

    m = meta if meta is not None else read_dataset_meta()
    start = str(m.get("start_date") or DEFAULT_START_DATE)
    end = str(m.get("end_date") or DEFAULT_END_DATE)
    return open_dates(start, end)


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
            path.resolve().relative_to(DB_DIR.resolve())
        except ValueError:
            print(f"refuse delete outside .db: {path}")
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


def strategy_dir_for_mode(mode: str) -> Path:
    folder = _MODE_STRATEGY_DIR.get(mode)
    if not folder:
        raise ValueError(f"unknown mode: {mode!r}")
    path = TEST_STRATEGIES_DIR / folder
    if not path.is_dir():
        raise FileNotFoundError(f"missing baseline strategy: {path}")
    return path


def repo_root() -> Path:
    """Repository root (directory containing ``devcli.py``)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "devcli.py").is_file():
            return parent
    raise RuntimeError("cannot locate repo root from cmd/common.py")
