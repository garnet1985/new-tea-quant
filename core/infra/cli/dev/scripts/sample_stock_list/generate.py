#!/usr/bin/env python3
"""
从 sys_stock_list 按「上市状态 × 板块 × 交易所」分层抽样，生成固定样本名单文件。

默认 500 只、种子与 ``setup.core.scripts.init_data.config`` 对齐，便于与演示数据包一致。

用法（仓库根目录）::

    python -m core.infra.cli.dev.scripts.sample_stock_list
    python devcli.py ssp 500
    python devcli.py pc
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.modules.data_manager import DataManager
from core.infra.setup.core.scripts.init_data.config import SAMPLE_RANDOM_SEED, TARGET_STOCK_COUNT

from .sample_stock_list import SampleStockList


def main() -> int:
    parser = argparse.ArgumentParser(description="分层抽样生成样本股票名单 CSV")
    parser.add_argument("--count", type=int, default=TARGET_STOCK_COUNT, help="目标股票数")
    parser.add_argument("--seed", type=int, default=SAMPLE_RANDOM_SEED, help="随机种子（可复现）")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出 CSV 路径（默认 core/modules/data_manager/core/dev/sample_stock_list/stratified_{count}.csv）",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    try:
        out = args.output or DataManager.sample_universe.csv_path(args.count)
        SampleStockList.generate(
            count=args.count,
            seed=args.seed,
            output=out,
            verbose=args.verbose,
        )
    except (RuntimeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
