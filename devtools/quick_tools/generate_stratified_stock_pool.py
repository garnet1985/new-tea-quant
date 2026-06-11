#!/usr/bin/env python3
"""
从 sys_stock_list 按「上市状态 × 板块 × 交易所」分层抽样，生成固定股票池文件。

默认 500 只、种子与 demo_exporter/config.py 对齐，便于与演示数据包一致。

用法（仓库根目录）::

    python devtools/quick_tools/generate_stratified_stock_pool.py
    python dev-cli.py -sample_stock_list -500
    python dev-cli.py -sample_stock_list -clear
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.modules.data_source.service.sample_stock_list import pool_csv_path
from devtools.demo_exporter.config import SAMPLE_RANDOM_SEED, TARGET_STOCK_COUNT
from devtools.quick_tools.stock_pool_ops import generate_stratified_pool_files


def main() -> int:
    parser = argparse.ArgumentParser(description="分层抽样生成股票池 CSV")
    parser.add_argument("--count", type=int, default=TARGET_STOCK_COUNT, help="目标股票数")
    parser.add_argument("--seed", type=int, default=SAMPLE_RANDOM_SEED, help="随机种子（可复现）")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出 CSV 路径（默认 core/modules/data_source/dev/stock_pool/stratified_{count}.csv）",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    try:
        out = args.output or pool_csv_path(args.count)
        generate_stratified_pool_files(
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
