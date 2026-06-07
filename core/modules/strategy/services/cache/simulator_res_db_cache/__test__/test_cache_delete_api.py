"""DbCache 快照行删除：全表 / 按 version（mock 表，避免占用 userspace DuckDB 锁）。"""

from unittest.mock import MagicMock, patch

from core.modules.strategy.launcher.workbench import (
    clear_workbench_simulation_cache_all,
    clear_workbench_simulation_cache_by_version,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
    SimulatorResDbCacheService,
)

_SN_A = "__test_cache_del_a__"
_SN_B = "__test_cache_del_b__"
_SVC_IMPORT = (
    "core.modules.strategy.services.cache.simulator_res_db_cache.cache_service"
    ".SimulatorResDbCacheService"
)


def _svc_with_model(model) -> SimulatorResDbCacheService:
    svc = SimulatorResDbCacheService.__new__(SimulatorResDbCacheService)
    svc.table_operator = model
    svc._row_retention = None
    return svc


def _mock_table_operator(*, list_rows, load_row=None, delete_ok=1):
    model = MagicMock()
    model.table_name = "sys_strategy_workbench_snapshot"
    model.execute_raw_query.return_value = list_rows
    if load_row is None:
        model.load_by_strategy_version.return_value = {"result_report": {"enum": {}}}
    else:
        model.load_by_strategy_version.side_effect = load_row
    model.delete_version_row.return_value = delete_ok
    return model


def test_delete_all_cache_removes_seeded_rows():
    svc = _svc_with_model(
        _mock_table_operator(
            list_rows=[
                {"strategy_name": _SN_A, "version": 1},
                {"strategy_name": _SN_B, "version": 2},
            ]
        )
    )
    n = svc.delete_all_cache()
    assert n == 2
    assert svc.table_operator.delete_version_row.call_count == 2


def test_delete_cache_by_version_missing_row():
    svc = _svc_with_model(
        _mock_table_operator(
            list_rows=[],
            load_row=lambda _sn, _v: None,
        )
    )
    assert svc.delete_cache_by_version(_SN_A, 9) is False


def test_delete_cache_by_version_success():
    svc = _svc_with_model(_mock_table_operator(list_rows=[]))
    assert svc.delete_cache_by_version(_SN_A, 3) is True
    svc.table_operator.delete_version_row.assert_called_once_with(_SN_A, 3)


@patch(_SVC_IMPORT)
def test_clear_workbench_simulation_cache_by_version(mock_svc_cls):
    mock_svc = MagicMock()
    mock_svc.table_operator = MagicMock()
    mock_svc.delete_cache_by_version.side_effect = [True, False]
    mock_svc_cls.return_value = mock_svc

    out = clear_workbench_simulation_cache_by_version(_SN_A, 5)
    assert out["ok"] is True
    assert out["version_id"] == "v5"

    missing = clear_workbench_simulation_cache_by_version(_SN_A, 5)
    assert missing["ok"] is False
    assert missing["error"] == "快照不存在"


@patch(_SVC_IMPORT)
def test_clear_workbench_simulation_cache_all(mock_svc_cls):
    mock_svc = MagicMock()
    mock_svc.table_operator = MagicMock()
    mock_svc.delete_all_cache.return_value = 4
    mock_svc_cls.return_value = mock_svc

    out = clear_workbench_simulation_cache_all()
    assert out["ok"] is True
    assert out["deleted_count"] == 4
