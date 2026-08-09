import pytest

from core.modules.data_source.core.dev.stock_pool_paths import (
    DEFAULT_DEV_STOCK_POOL_COUNT,
    DEFAULT_DEV_STOCK_POOL_FILE,
    resolve_dev_stock_pool_by_count,
)


def test_resolve_dev_stock_pool_by_count():
    p = resolve_dev_stock_pool_by_count(500)
    assert p.name == "stratified_500.csv"
    assert p.parent.name == "stock_pool"


def test_default_pool_file_matches_default_count():
    assert DEFAULT_DEV_STOCK_POOL_FILE == f"stratified_{DEFAULT_DEV_STOCK_POOL_COUNT}.csv"


def test_resolve_rejects_non_positive():
    with pytest.raises(ValueError):
        resolve_dev_stock_pool_by_count(0)
