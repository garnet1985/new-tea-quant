#!/usr/bin/env python3
"""
JobPipeline 样本 renew：从 DB 的 stock_list 顺序截取 N 只股票，试跑 per-entity 源。

不跑全量。默认只 renew ``stock_klines``（需 DB 里已有 stock_list；没有则先拉列表）。

用法（仓库根目录）::

    python devtools/quick_tools/renew_pipeline_sample.py
    python devtools/quick_tools/renew_pipeline_sample.py --n 120 --source stock_st_periods
    python devtools/quick_tools/renew_pipeline_sample.py --ensure-stock-list

环境变量（脚本会设置，也可自行 export）::

    NTQ_DS_SAMPLE_N=80   # 默认见 sample_stock_list.DEFAULT_SAMPLE_N
    NTQ_DS_SAMPLE_OFFSET=0
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

from core.modules.data_source.service.sample_stock_list import DEFAULT_SAMPLE_N

DEFAULT_SOURCE = "stock_klines"


def _configure_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    if verbose:
        logging.getLogger("core.modules.data_source").setLevel(logging.INFO)
        logging.getLogger("core.modules.data_source.service.pipeline").setLevel(logging.INFO)


def _apply_sample_env(n: int, offset: int) -> None:
    os.environ["NTQ_DS_SAMPLE_N"] = str(max(1, n))
    os.environ["NTQ_DS_SAMPLE_OFFSET"] = str(max(0, offset))


def _stock_list_count() -> int:
    from core.modules.data_manager import DataManager

    dm = DataManager.get_instance()
    if dm is None:
        dm = DataManager(is_verbose=False)
        dm.initialize()
    return len(dm.stock.list.load_all())


def main() -> int:
    parser = argparse.ArgumentParser(description="Data source JobPipeline 样本 renew")
    parser.add_argument(
        "--n",
        type=int,
        default=DEFAULT_SAMPLE_N,
        help=f"从 stock_list 截取只数（默认 {DEFAULT_SAMPLE_N}）",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="stock_list 起始下标（默认 0）",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"要 renew 的 data source key（默认 {DEFAULT_SOURCE}）",
    )
    parser.add_argument(
        "--ensure-stock-list",
        action="store_true",
        help="若 sys_stock_list 为空则先 renew stock_list（一次全量列表，仍很快）",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="INFO 日志")
    args = parser.parse_args()

    _configure_logging(args.verbose)
    _apply_sample_env(args.n, args.offset)

    from core.modules.data_source.data_source_manager import DataSourceManager

    mgr = DataSourceManager(is_verbose=args.verbose)
    count = _stock_list_count()
    if count == 0:
        if not args.ensure_stock_list:
            logger.error(
                "sys_stock_list 为空。请先 renew stock_list，或加 --ensure-stock-list"
            )
            return 1
        logger.info("sys_stock_list 为空，先执行 stock_list …")
        mgr.renew("stock_list")
        count = _stock_list_count()
        if count == 0:
            logger.error("stock_list renew 后仍为空")
            return 1

    logger.info(
        "样本 renew: source=%s, stock_list 全量 %s 只, 将截取 offset=%s n=%s",
        args.source,
        count,
        args.offset,
        args.n,
    )
    mgr.renew(args.source)
    logger.info("样本 renew 完成: %s", args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
