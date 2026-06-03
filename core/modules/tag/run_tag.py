#!/usr/bin/env python3
"""
运行 Tag 场景（TagManager + JobPipeline）。

用法（仓库根目录）::

    python -m core.modules.tag --list
    python -m core.modules.tag my_scenario
    python -m core.modules.tag my_scenario -v
    python -m core.modules.tag my_scenario -v --execute-mode batch --batch-size 50
    python -m core.modules.tag --all -v
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Union


def _repo_root() -> Path:
    # core/modules/tag/run_tag.py → 向上 3 层到 core，再 1 层到仓库根
    return Path(__file__).resolve().parents[3]


def _ensure_import_path() -> None:
    root = str(_repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def _parse_max_workers(raw: str) -> Union[str, int]:
    if raw.lower() == "auto":
        return "auto"
    return int(raw)


def main(argv: list[str] | None = None) -> int:
    _ensure_import_path()

    parser = argparse.ArgumentParser(description="Run Tag scenario(s) via TagManager")
    parser.add_argument(
        "scenario",
        nargs="?",
        help="scenario 名称；省略且未指定 --all 时仅列出可用场景",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="执行 userspace/tags 下全部已启用场景",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出已发现的 scenario 名称并退出",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="输出 INFO 日志（含 JobPipeline 进度）",
    )
    parser.add_argument(
        "--execute-mode",
        choices=("queue", "batch", "elastic"),
        help="覆盖 settings.performance.execute_mode（JobPipeline ExecuteMode）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        metavar="N",
        help="覆盖 settings.performance.batch_size（仅 batch 模式）",
    )
    parser.add_argument(
        "--max-workers",
        metavar="N|auto",
        help="覆盖 settings.performance.max_workers",
    )
    parser.add_argument(
        "--prefetch-ahead",
        type=int,
        metavar="N",
        help="覆盖 settings.performance.prefetch_ahead（queue 模式）",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="启用 TagRunProfile（等同 performance.profile / NTQ_TAG_PROFILE）",
    )
    parser.add_argument(
        "--entities-per-job",
        type=int,
        metavar="N",
        help="覆盖 settings.performance.entities_per_job（一 job N 股 bulk stage）",
    )
    parser.add_argument(
        "--no-stage-in-worker",
        action="store_true",
        help="关闭子进程内 bulk stage（默认在 execute 内 stage）",
    )
    parser.add_argument(
        "--stage-spill-rows",
        type=int,
        metavar="N",
        help="DuckDB + stage_in_worker：内存缓冲达 N 行则 spill Parquet（默认 50000）",
    )
    parser.add_argument(
        "--stock-limit",
        type=int,
        metavar="N",
        help="只跑前 N 只股票（试验对比用）",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    from core.modules.tag import TagManager

    dispatch_overrides: Dict[str, Any] = {}
    if args.execute_mode:
        dispatch_overrides["execute_mode"] = args.execute_mode
    if args.batch_size is not None:
        dispatch_overrides["batch_size"] = args.batch_size
    if args.max_workers is not None:
        dispatch_overrides["max_workers"] = _parse_max_workers(args.max_workers)
    if args.prefetch_ahead is not None:
        dispatch_overrides["prefetch_ahead"] = args.prefetch_ahead
    if args.profile:
        dispatch_overrides["profile"] = True
    if args.entities_per_job is not None:
        dispatch_overrides["entities_per_job"] = max(1, int(args.entities_per_job))
    if args.no_stage_in_worker:
        dispatch_overrides["stage_in_worker"] = False
    if args.stage_spill_rows is not None:
        dispatch_overrides["stage_spill_rows"] = max(1, int(args.stage_spill_rows))
    if args.stock_limit is not None:
        dispatch_overrides["stock_limit"] = max(1, int(args.stock_limit))

    mgr = TagManager(is_verbose=args.verbose, dispatch_overrides=dispatch_overrides)

    if args.list or (not args.all and not args.scenario):
        names = sorted(mgr.scenario_cache.keys())
        if not names:
            print("未发现 scenario（检查 userspace/tags 下 settings.py）")
            return 1
        print("可用 scenario:")
        for name in names:
            print(f"  - {name}")
        if args.list:
            return 0
        print("\n示例: python -m core.modules.tag <scenario> -v")
        print("调度: --execute-mode queue|batch|elastic [--batch-size N]")
        return 0

    if args.all:
        mgr.execute()
    else:
        mgr.execute(scenario_name=args.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
