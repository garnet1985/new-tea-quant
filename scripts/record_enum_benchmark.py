#!/usr/bin/env python3
"""
枚举 benchmark：跑一轮 -se 或把最新 enum 产出登记到 userspace/benchmarks/<label>/。

示例（你现在要记的 1000 股 baseline · 单股单 job）::

    # 先跑枚举（或你自己已跑完）
    python start-cli.py -se -f --strategy example --stocks 1000

    # 登记结果（从最新 enum/<version>/ 拷贝报告 + 写 manifest）
    python scripts/record_enum_benchmark.py --label enum_1000_1stock_per_job --strategy example

    # 一条龙
    python scripts/record_enum_benchmark.py --label enum_1000_1stock_per_job --strategy example --run --stocks 1000 -f
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_ROOT = REPO_ROOT / "userspace" / "benchmarks"
ENUM_ARTIFACTS = (
    "0_performance_report.json",
    "0_report_enum.json",
    "0_metadata.json",
)


def _git_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _load_database_type() -> str:
    p = REPO_ROOT / "userspace" / "system" / "config" / "database" / "common.json"
    if not p.is_file():
        return "unknown"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return str(data.get("database_type") or "unknown")
    except Exception:
        return "unknown"


def _enum_version_dir(strategy_name: str, version: str) -> Optional[Path]:
    enum_root = (
        REPO_ROOT
        / "userspace"
        / "strategies"
        / strategy_name
        / "results"
        / "simulations"
        / "enum"
    )
    child = enum_root / str(version)
    if child.is_dir() and (child / "0_performance_report.json").is_file():
        return child
    return None


def _latest_enum_version_dir(strategy_name: str) -> Optional[Path]:
    enum_root = (
        REPO_ROOT
        / "userspace"
        / "strategies"
        / strategy_name
        / "results"
        / "simulations"
        / "enum"
    )
    if not enum_root.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for child in enum_root.iterdir():
        if not child.is_dir():
            continue
        try:
            vid = int(child.name)
        except ValueError:
            continue
        if (child / "0_performance_report.json").is_file():
            candidates.append((vid, child))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def record_benchmark(
    *,
    label: str,
    strategy_name: str,
    stock_count: Optional[int],
    entities_per_job: int,
    command: str,
    enum_dir: Path,
) -> Path:
    dest = BENCHMARKS_ROOT / label
    dest.mkdir(parents=True, exist_ok=True)

    copied: Dict[str, str] = {}
    for name in ENUM_ARTIFACTS:
        src = enum_dir / name
        if src.is_file():
            shutil.copy2(src, dest / name)
            copied[name] = str((dest / name).relative_to(REPO_ROOT))

    perf_summary: Dict[str, Any] = {}
    perf_path = enum_dir / "0_performance_report.json"
    if perf_path.is_file():
        perf = _read_json(perf_path)
        perf_summary = dict(perf.get("summary") or {})
        if perf.get("time_breakdown"):
            perf_summary["time_breakdown"] = perf["time_breakdown"]
        if perf.get("data"):
            perf_summary["data"] = perf["data"]

    meta_path = enum_dir / "0_metadata.json"
    enum_meta: Dict[str, Any] = {}
    if meta_path.is_file():
        enum_meta = _read_json(meta_path)

    manifest: Dict[str, Any] = {
        "label": label,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_rev": _git_rev(),
        "database_type": _load_database_type(),
        "strategy": strategy_name,
        "benchmark_kind": "opportunity_enumeration",
        "dispatch_model": {
            "entities_per_job": entities_per_job,
            "description": "1 job = 1 stock (current default)",
        },
        "stock_count_requested": stock_count,
        "stock_count_actual": perf_summary.get("total_stocks")
        or enum_meta.get("stock_count"),
        "enum_output_version": enum_dir.name,
        "enum_output_dir": str(enum_dir.relative_to(REPO_ROOT)),
        "command": command,
        "performance_summary": perf_summary,
        "artifacts": copied,
    }
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="登记策略枚举 benchmark 产出")
    parser.add_argument("--label", required=True, help="benchmark 目录名，如 enum_1000_1stock_per_job")
    parser.add_argument("--strategy", default="example", help="策略目录名")
    parser.add_argument("--stocks", type=int, default=None, help="仅 --run 时传给 CLI")
    parser.add_argument(
        "--entities-per-job",
        type=int,
        default=1,
        help="记录用：当前调度模型（默认 1 股/job）",
    )
    parser.add_argument("--run", action="store_true", help="先执行 start-cli.py -se")
    parser.add_argument("-f", "--force", action="store_true", help="--run 时加 -f 跳过 DbCache")
    parser.add_argument(
        "--enum-version",
        type=str,
        default=None,
        help="指定 enum 输出版本目录名（如 16）；默认取最大版本号",
    )
    args = parser.parse_args(argv)

    cmd_parts = [
        sys.executable,
        str(REPO_ROOT / "start-cli.py"),
        "-se",
        "--strategy",
        args.strategy,
    ]
    if args.force:
        cmd_parts.append("-f")
    if args.stocks is not None:
        cmd_parts.extend(["--stocks", str(args.stocks)])
    command = " ".join(cmd_parts)

    if args.run:
        print(f"▶ {command}")
        rc = subprocess.run(cmd_parts, cwd=REPO_ROOT).returncode
        if rc != 0:
            print(f"枚举失败 exit={rc}", file=sys.stderr)
            return rc

    if args.enum_version:
        enum_dir = _enum_version_dir(args.strategy, args.enum_version)
    else:
        enum_dir = _latest_enum_version_dir(args.strategy)
    if enum_dir is None:
        print(
            f"未找到 {args.strategy} 的 enum 产出（需含 0_performance_report.json）",
            file=sys.stderr,
        )
        return 1

    manifest_path = record_benchmark(
        label=args.label,
        strategy_name=args.strategy,
        stock_count=args.stocks,
        entities_per_job=args.entities_per_job,
        command=command,
        enum_dir=enum_dir,
    )
    print(f"✅ benchmark 已登记: {manifest_path.relative_to(REPO_ROOT)}")
    print(f"   enum 版本目录: {enum_dir.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
