"""StockSampler 关键边界（空列表 / 未知策略 / 可复现随机 / 权重兜底）。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.services.entity_loader.stock_sampling import StockSampler

pytestmark = pytest.mark.force_run


def test_sample_empty_list() -> None:
    assert StockSampler.sample([], {"strategy": "uniform", "sampling_amount": 3}) == []


def test_sample_unknown_strategy_takes_prefix() -> None:
    stocks = [f"{i:06d}.SZ" for i in range(1, 6)]
    out = StockSampler.sample(
        stocks,
        {"strategy": "not_a_real_strategy", "sampling_amount": 2},
    )
    assert out == stocks[:2]


def test_sample_uniform_amount_ge_len_returns_all() -> None:
    stocks = ["000001.SZ", "000002.SZ"]
    out = StockSampler.sample(
        stocks,
        {"strategy": "uniform", "sampling_amount": 10},
    )
    assert out == stocks


def test_sample_random_with_seed_is_deterministic() -> None:
    stocks = [f"{i:06d}.SZ" for i in range(1, 21)]
    cfg = {"strategy": "random", "sampling_amount": 5, "random": {"seed": 42}}
    assert StockSampler.sample(stocks, cfg) == StockSampler.sample(stocks, cfg)


def test_sample_weighted_all_zero_falls_back_to_uniform() -> None:
    stocks = ["a", "b", "c", "d"]
    out = StockSampler.sample(
        stocks,
        {
            "strategy": "weighted",
            "sampling_amount": 2,
            "weighted": {"weights": {"a": 0, "b": 0, "c": 0, "d": 0}, "seed": 1},
        },
    )
    # uniform fallback with amount=2 on len=4 → step=2 → [a, c]
    assert out == ["a", "c"]
