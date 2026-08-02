#!/usr/bin/env python3
"""Clean BE performance artifacts under ``__performance__/`` only.

Safety: drops/deletes only registries named ``perf_test_tmp*`` created by this suite.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parents[4]  # .../scripts → repo root
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from common import (  # noqa: E402
    FAKE_DATA_DIR,
    REGISTRY_PATH,
    RESULTS_DIR,
    WORKDIR,
    _NAME_RE,
    ensure_layout,
    load_registry,
    save_registry,
)
from config import DB_NAME_PREFIX  # noqa: E402


def _safe_unlink(path: Path) -> None:
    if path.is_file():
        path.unlink()
        print(f"removed file {path}")


def clean_data() -> None:
    ensure_layout()
    for p in FAKE_DATA_DIR.iterdir():
        if p.name.startswith("."):
            continue
        if p.is_file():
            _safe_unlink(p)


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
                # must stay under WORKDIR
                try:
                    path.resolve().relative_to(WORKDIR.resolve())
                except ValueError:
                    print(f"refuse delete outside .workdir: {path}")
                    kept.append(e)
                    break
                else:
                    _safe_unlink(path)
                    _safe_unlink(Path(str(path) + ".wal"))
            else:
                print(f"removed duckdb entry {ename}")
                continue
            # if break from refuse, entry kept already
            continue
        if eng in ("mysql", "postgresql", "pgsql"):
            print(
                f"server db {eng}/{ename}: DROP not auto-run in this pass; "
                f"remove registry entry only after manual DROP"
            )
            # still remove registry if --force-registry? keep for safety
            kept.append(e)
            continue
        kept.append(e)

    # also sweep orphan duckdb files matching prefix under workdir
    if name is None:
        for p in WORKDIR.glob(f"{DB_NAME_PREFIX}*.duckdb"):
            _safe_unlink(p)
            _safe_unlink(Path(str(p) + ".wal"))

    reg["entries"] = kept
    save_registry(reg)
    if not kept and REGISTRY_PATH.is_file() and name is None:
        # keep empty registry file for clarity
        pass


def clean_local_results() -> None:
    local = RESULTS_DIR / "_local"
    if not local.is_dir():
        return
    for p in sorted(local.rglob("*"), reverse=True):
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            try:
                p.rmdir()
            except OSError:
                pass
    print(f"cleaned {local}")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Clean BE __performance__ artifacts")
    p.add_argument("--data", action="store_true", help="delete fake_data CSVs")
    p.add_argument("--db", action="store_true", help="delete registered perf_test_tmp* DBs")
    p.add_argument("--results", action="store_true", help="delete results/_local")
    p.add_argument("--all", action="store_true", help="data + db + local results")
    p.add_argument("--name", default=None, help="only clean this registry name")
    args = p.parse_args(argv)

    if not (args.data or args.db or args.results or args.all):
        p.print_help()
        print("\nSpecify at least one of --data/--db/--results/--all")
        return 2

    if args.all or args.data:
        clean_data()
    if args.all or args.db:
        clean_db(name=args.name)
    if args.all or args.results:
        clean_local_results()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
