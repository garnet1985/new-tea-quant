"""DbCache 快照行删除：全表 / 按 version。"""

from core.modules.strategy.launcher.workbench import (
    clear_workbench_simulation_cache_all,
    clear_workbench_simulation_cache_by_version,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
    SimulatorResDbCacheService,
)

_SN_A = "__test_cache_del_a__"
_SN_B = "__test_cache_del_b__"


def _seed_row(strategy_name: str, *, tag: str) -> int:
    svc = SimulatorResDbCacheService()
    model = svc.table_operator
    assert model is not None
    model._ensure_table_ready()
    created = model.create_snapshot(
        strategy_name,
        {"simulation": {"template": "standard"}},
        {"enum": {"opportunities": 1}},
        settings_finger_print_id=f"fp-{tag}",
        env_fingerprint_id=f"env-{tag}",
    )
    return int((created or {}).get("version") or 0)


def _cleanup_test_strategies() -> None:
    svc = SimulatorResDbCacheService()
    for name in (_SN_A, _SN_B):
        svc.delete_cache_for_strategy(name)


def test_delete_all_cache_removes_seeded_rows():
    _cleanup_test_strategies()
    _seed_row(_SN_A, tag="a1")
    _seed_row(_SN_B, tag="b1")
    svc = SimulatorResDbCacheService()
    n = svc.delete_all_cache()
    assert n >= 2
    assert svc.delete_all_cache() == 0
    _cleanup_test_strategies()


def test_delete_cache_by_version():
    _cleanup_test_strategies()
    sid = _seed_row(_SN_A, tag="one")
    out = clear_workbench_simulation_cache_by_version(_SN_A, sid)
    assert out["ok"] is True
    assert out["deleted"] is True
    assert out["version_id"] == f"v{sid}"
    missing = clear_workbench_simulation_cache_by_version(_SN_A, sid)
    assert missing["ok"] is False
    assert missing["error"] == "快照不存在"
    _cleanup_test_strategies()
