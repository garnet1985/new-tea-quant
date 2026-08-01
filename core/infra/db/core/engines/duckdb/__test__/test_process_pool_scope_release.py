"""process_pool_scope：从 DataManager 收集并释放主进程 DB 句柄。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.force_run

from core.infra.db.core.engines.duckdb.process_pool_scope import (
    _collect_db_managers_from_data_mgr,
    release_all_main_db_handles,
)


def test_collect_includes_calendar_model_db():
    from core.infra.db import DatabaseManager

    calendar_db = MagicMock(spec=DatabaseManager)
    calendar_db._initialized = True
    trade_cal = MagicMock()
    trade_cal.db = calendar_db

    calendar_svc = MagicMock()
    calendar_svc.db = None
    calendar_svc._trade_calendar = trade_cal

    data_mgr = MagicMock()
    data_mgr.db = MagicMock(spec=DatabaseManager)
    data_mgr.db._initialized = True
    data_mgr._data_service = MagicMock()
    data_mgr._data_service.calendar = calendar_svc
    data_mgr._data_service.stock = None
    data_mgr._data_service.macro = None
    data_mgr._data_service.index = None
    data_mgr._data_service.db_cache = None
    data_mgr._data_service.backup_restore = None

    with patch.object(DatabaseManager, "_default_instance", data_mgr.db):
        found = _collect_db_managers_from_data_mgr(data_mgr)

    assert data_mgr.db in found
    assert calendar_db in found


def test_release_all_closes_calendar_model_db():
    from core.infra.db import DatabaseManager

    calendar_db = MagicMock(spec=DatabaseManager)
    calendar_db._initialized = True
    trade_cal = MagicMock()
    trade_cal.db = calendar_db

    calendar_svc = MagicMock()
    calendar_svc.db = None
    calendar_svc._trade_calendar = trade_cal

    main_db = MagicMock(spec=DatabaseManager)
    main_db._initialized = True

    data_mgr = MagicMock()
    data_mgr.db = main_db
    data_mgr._data_service = MagicMock()
    data_mgr._data_service.calendar = calendar_svc
    for name in ("stock", "macro", "index", "db_cache", "backup_restore"):
        setattr(data_mgr._data_service, name, None)

    with patch.object(DatabaseManager, "_default_instance", main_db), patch.object(
        DatabaseManager, "reset_default"
    ) as reset:
        release_all_main_db_handles(data_mgr)

    main_db.close.assert_called_once()
    calendar_db.close.assert_called()
    reset.assert_called_once()
    assert trade_cal.db is None
