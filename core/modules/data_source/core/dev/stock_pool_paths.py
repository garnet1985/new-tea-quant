"""开发样本股票池路径（``core/modules/data_source/dev/stock_pool/``）。"""
from __future__ import annotations

from pathlib import Path

_MODULE_ROOT = Path(__file__).resolve().parent
DEV_STOCK_POOL_DIR = _MODULE_ROOT / "stock_pool"
DEFAULT_DEV_STOCK_POOL_COUNT = 500
DEFAULT_DEV_STOCK_POOL_FILE = f"stratified_{DEFAULT_DEV_STOCK_POOL_COUNT}.csv"


def dev_stock_pool_dir() -> Path:
    return DEV_STOCK_POOL_DIR


def resolve_dev_stock_pool_by_count(count: int) -> Path:
    """``use_sample_stock_list: N`` → ``stratified_N.csv``。"""
    n = int(count)
    if n <= 0:
        raise ValueError(f"use_sample_stock_list 须为正整数: {count!r}")
    return DEV_STOCK_POOL_DIR / f"stratified_{n}.csv"
