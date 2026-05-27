#!/usr/bin/env python3
"""DbCache result_report write_count audit."""

from core.modules.strategy.services.cache.simulator_res_db_cache.audit.result_report_audit import (
    attach_initial_write_meta,
    bump_write_count,
    exceeds_max_row_updates,
    get_write_count,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.config import (
    MAX_SNAPSHOT_ROW_UPDATES,
)


def test_write_count_bump_and_limit():
    r = attach_initial_write_meta({"enum": {"opportunities": 1}})
    assert get_write_count(r) == 1
    r, n = bump_write_count(r)
    assert n == 2
    assert not exceeds_max_row_updates(n)
    for _ in range(MAX_SNAPSHOT_ROW_UPDATES):
        r, n = bump_write_count(r)
    assert exceeds_max_row_updates(n)
