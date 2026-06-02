#!/usr/bin/env python3
"""
运行 Tag 场景（TagManager + JobDispatcher）。

用法（仓库根目录）::

    python -m core.modules.tag --list
    python -m core.modules.tag my_scenario
    python -m core.modules.tag my_scenario -v
    python -m core.modules.tag --all -v
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def _repo_root() -> Path:
    # core/modules/tag/run_tag.py → 向上 3 层到 core，再 1 层到仓库根
    return Path(__file__).resolve().parents[3]


def _ensure_import_path() -> None:
    root = str(_repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


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
        help="输出 INFO 日志（含 JobDispatcher 进度）",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from core.modules.tag import TagManager

    mgr = TagManager(is_verbose=args.verbose)

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
        return 0

    if args.all:
        mgr.execute()
    else:
        mgr.execute(scenario_name=args.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
