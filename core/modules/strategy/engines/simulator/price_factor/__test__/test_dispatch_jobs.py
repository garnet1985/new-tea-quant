from core.modules.strategy.engines.simulator.price_factor.dispatch_jobs import (
    build_price_dispatch_jobs,
)


def test_build_price_dispatch_jobs_chunks():
    per_stock = [
        {"stock_id": f"s{i}", "config": {"k": 1}, "strategy_name": "demo"}
        for i in range(5)
    ]
    jobs = build_price_dispatch_jobs(per_stock_jobs=per_stock, entities_per_job=2)
    assert len(jobs) == 3
    assert jobs[0]["stock_ids"] == ["s0", "s1"]
    assert len(jobs[0]["stock_jobs"]) == 2
    assert jobs[-1]["stock_ids"] == ["s4"]
