#!/usr/bin/env python3
"""Clean BE performance artifacts under ``__performance__/`` only.

Safety: drops/deletes only registries named ``perf_test_tmp*`` created by this suite.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

_CMD = Path(__file__).resolve().parent
if str(_CMD) not in sys.path:
    sys.path.insert(0, str(_CMD))
from common import (  # noqa: E402
    DB_DIR,
    REGISTRY_PATH,
    RESULTS_DIR,
    TEST_STRATEGIES_DIR,
    _NAME_RE,
    ensure_layout,
    load_registry,
    repo_root,
    save_registry,
)

_REPO = repo_root()
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
from config import DB_NAME_PREFIX  # noqa: E402


def _safe_unlink(path: Path) -> None:
    if path.is_file():
        path.unlink()
        print(f"removed file {path}")


def clean_db(*, name: Optional[str] = None) -> None:
    ensure_layout()
    reg = load_registry()
    entries = list(reg.get("entries") or [])
    kept = []
    for e in entries:
        eng = str(e.get("engine") or "").lower()
        ename = str(e.get("name") or "")
        if name and ename != name:
            kept.append(e)
            continue
        if not _NAME_RE.match(ename):
            print(f"skip non-perf name (not deleted): {ename}")
            kept.append(e)
            continue
        if eng == "duckdb":
            paths = e.get("paths") or {}
            for key in ("data", "tag", "strategy"):
                p = paths.get(key)
                if not p:
                    continue
                path = Path(p)
                try:
                    path.resolve().relative_to(DB_DIR.resolve())
                except ValueError:
                    print(f"refuse delete outside .db: {path}")
                    kept.append(e)
                    break
                else:
                    _safe_unlink(path)
                    _safe_unlink(Path(str(path) + ".wal"))
            else:
                print(f"removed duckdb entry {ename}")
                continue
            continue
        if eng in ("mysql", "postgresql", "pgsql"):
            if eng == "pgsql":
                eng = "postgresql"
            try:
                if eng == "mysql":
                    from mysql_support import drop_mysql_entry

                    drop_mysql_entry(e)
                    print(f"removed mysql database {ename}")
                else:
                    from postgresql_support import drop_postgresql_entry

                    drop_postgresql_entry(e)
                    print(f"removed postgresql database {ename}")
            except SystemExit as exc:
                print(f"skip {eng} {ename}: {exc}")
                kept.append(e)
            except Exception as exc:
                print(f"failed to drop {eng} {ename}: {exc}")
                kept.append(e)
            continue
        kept.append(e)

    if name is None:
        for p in DB_DIR.glob(f"{DB_NAME_PREFIX}*.duckdb"):
            _safe_unlink(p)
            _safe_unlink(Path(str(p) + ".wal"))

    reg["entries"] = kept
    save_registry(reg)
    _ = REGISTRY_PATH


def clean_local_results() -> None:
    local = RESULTS_DIR / "_local"
    if local.is_dir():
        for p in sorted(local.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
        print(f"cleaned {local}")

    # Strategy run artifacts now live under discovered test_strategies folder.
    for mode_dir in ("entity_based", "slice_based"):
        results = TEST_STRATEGIES_DIR / mode_dir / "results"
        if results.is_dir():
            import shutil

            shutil.rmtree(results)
            print(f"cleaned {results}")

    # Legacy mistaken dumps under userspace/strategies/{entity,slice}_based/
    try:
        from core.infra.project_context import ProjectContext

        strategies_root = ProjectContext.path.get_strategies_root()
    except Exception:
        strategies_root = repo_root() / "userspace" / "strategies"
    for legacy_name in ("entity_based", "slice_based"):
        legacy = strategies_root / legacy_name
        if not legacy.is_dir():
            continue
        # Only remove if it looks like our perf dump (results only / no strategy.py)
        if (legacy / "strategy.py").is_file():
            print(f"skip userspace strategy (has strategy.py): {legacy}")
            continue
        import shutil

        shutil.rmtree(legacy)
        print(f"cleaned legacy perf dump {legacy}")


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Clean BE __performance__ artifacts")
    p.add_argument("--db", action="store_true", help="delete registered perf_test_tmp* DBs under .db/")
    p.add_argument(
        "--results",
        action="store_true",
        help="delete test_strategies/*/results + legacy local dumps（不删 reports/{版本} 留档）",
    )
    p.add_argument("--all", action="store_true", help="db + results（不删版本留档）")
    p.add_argument("--name", default=None, help="only clean this registry name")
    args = p.parse_args(argv)

    if not (args.db or args.results or args.all):
        p.print_help()
        print("\nSpecify at least one of --db/--results/--all")
        return 2

    if args.all or args.db:
        clean_db(name=args.name)
    if args.all or args.results:
        clean_local_results()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
