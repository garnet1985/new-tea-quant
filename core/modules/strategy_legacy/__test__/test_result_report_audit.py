#!/usr/bin/env python3
"""DbCache result_report write_count audit."""

from core.modules.strategy.services.cache.simulator_res_db_cache.audit.result_report_audit import (
    attach_initial_write_meta,
    bump_write_count,
    get_write_count,
)


def test_write_count_bump():
    r = attach_initial_write_meta({"enum": {"opportunities": 1}})
    assert get_write_count(r) == 1
    r, n = bump_write_count(r)
    assert n == 2
    assert get_write_count(r) == 2
