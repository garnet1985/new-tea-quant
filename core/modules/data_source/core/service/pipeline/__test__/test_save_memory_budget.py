"""写入预算按单笔大小拆在飞请求和缓冲区，不设 256MB 下限。"""
from core.modules.data_source.core.service.pipeline.save_memory_budget import SaveMemoryBudget


def test_tight_budget_keeps_one_request_and_one_frame():
    budget = SaveMemoryBudget(budget_bytes=500, cpu_cap=8, write_reserve_bytes=100)
    budget.observe(400)
    assert budget.in_flight == 1
    assert budget.buffer_cap == 400


def test_wide_budget_raises_in_flight_until_cpu_cap():
    budget = SaveMemoryBudget(budget_bytes=10_000, cpu_cap=3, write_reserve_bytes=1000)
    budget.observe(1000)
    assert budget.in_flight == 3
    assert budget.buffer_cap == 10_000 - 1000 - 3 * 1000


def test_rss_overshoot_shrinks_budget(monkeypatch):
    budget = SaveMemoryBudget(budget_bytes=1000, cpu_cap=2, write_reserve_bytes=0)
    budget.observe(100)
    budget.budget_bytes = 500
    monkeypatch.setattr(
        "core.modules.data_source.core.service.pipeline.save_memory_budget._process_rss_bytes",
        lambda: 800,
    )
    budget.note_rss()
    assert budget.budget_bytes == 200
