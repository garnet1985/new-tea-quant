"""bootstrap_worker_data_manager：主进程 suspend 时不得重开 DuckDB。"""

from __future__ import annotations

import multiprocessing as mp
from unittest.mock import MagicMock, patch

import pytest

from core.modules.backtest_engine.core.shared.worker_data_runtime import (
    bootstrap_worker_data_manager,
)

pytestmark = pytest.mark.force_run


def test_main_process_skips_reopen_when_duckdb_pool_suspended() -> None:
    sentinel = object()
    main_proc = MagicMock()
    main_proc.name = "MainProcess"

    with patch.object(mp, "current_process", return_value=main_proc), patch(
        "core.infra.db.Db.duckdb.worker_pool.is_main_active",
        return_value=True,
    ), patch("core.modules.data_manager.DataManager") as dm_cls:
        dm_cls.get_instance.return_value = sentinel
        dm_cls.side_effect = AssertionError(
            "must not construct DataManager while suspended"
        )
        out = bootstrap_worker_data_manager()

    assert out is sentinel
    dm_cls.assert_not_called()
    dm_cls.get_instance.assert_called()
