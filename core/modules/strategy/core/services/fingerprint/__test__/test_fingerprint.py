"""execute_fp 白名单抽取与哈希。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings.execute_fp_whitelist import (
    EXECUTE_SETTINGS_FIELDS,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

pytestmark = pytest.mark.force_run


def _disk() -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "demo"},
        "simulation": {
            "execution": {
                "mode": "entity_based",
                "start_date": "20200101",
                "end_date": "20201231",
            },
            "risk_control": {
                "skip_enter_when": ["st"],
                "force_exit_when_draft": {"status": "x"},
            },
        },
        "data": {"base": {"data_key": "stock.kline.daily"}},
        "scanner": {"adapters": ["console"]},
        "core": {"n": 1},
        "analysis": {"enabled": True},
        "enumerator": {"max_workers": 4},
        "price_simulator": {"lookback": 20},
        "portfolio": {"initial_capital": 1_000_000},
        "market_profile": "china_a_stock",
    }


def _info(settings: dict):
    return SimpleNamespace(
        settings=settings,
        unique_relative_path="demo/x",
        hooks_class=None,
        hooks_module_path="",
        strategy_file="",
    )


def test_extract_empty_matches_canonical_defaults() -> None:
    """FED ``EXECUTE_SETTINGS_DEFAULTS`` 必须与这份投影对齐。"""
    out = StrategySettings.extract_execute_settings({})
    assert out["data"]["base"]["data_key"] == "stock.kline.daily"
    assert out["simulation"]["execution"]["mode"] == "entity_based"
    assert out["simulation"]["risk_control"]["pending_enter"]["max_wait_open_days"] == 5
    assert out["portfolio"]["initial_capital"] == 1_000_000
    assert "meta" not in out
    assert "scanner" not in out
    assert "analysis" not in out


def test_extract_keeps_whitelist_drops_others() -> None:
    out = StrategySettings.extract_execute_settings(_disk())
    assert set(out.keys()) <= set(EXECUTE_SETTINGS_FIELDS)
    assert "meta" not in out
    assert "scanner" not in out
    assert "enumerator" not in out
    assert "analysis" not in out
    assert "price_simulator" not in out
    assert "is_enabled" not in out
    assert out["core"] == {"n": 1}
    assert out["simulation"]["execution"]["mode"] == "entity_based"
    assert out["simulation"]["execution"]["start_date"] == "20200101"


def test_extract_drops_ui_draft_keys_and_empty_objects() -> None:
    out = StrategySettings.extract_execute_settings(_disk())
    risk = out["simulation"]["risk_control"]
    assert "force_exit_when_draft" not in risk
    assert risk["skip_enter_when"] == ["st"]

    raw = _disk()
    raw["core"] = {"n": 1, "placeholder": {}}
    with_empty = StrategySettings.extract_execute_settings(raw)
    assert with_empty["core"] == {"n": 1}


def test_extract_payload_puts_entity_ids_in_scope() -> None:
    payload = FingerprintCalculator.extract_execute_payload(
        _disk(),
        entity_ids=["000002.SZ", "000001.SZ", ""],
    )
    assert payload["scope"]["entity_ids"] == ["000001.SZ", "000002.SZ"]
    assert "entity_ids" not in payload["settings"]


def test_execute_fp_ignores_analysis_only_change() -> None:
    disk = _disk()
    effective_a, _ = StrategySettings.calculate_effective_settings(disk, {})
    user = {**disk, "analysis": {"enabled": False, "extra": 1}}
    effective_b, _ = StrategySettings.calculate_effective_settings(disk, user)
    ids = ["000001.SZ"]
    assert FingerprintCalculator.to_execute_fingerprint(
        effective_a, ids
    ) == FingerprintCalculator.to_execute_fingerprint(effective_b, ids)


def test_execute_fp_stable_after_round_trip() -> None:
    disk = _disk()
    effective, _ = StrategySettings.calculate_effective_settings(disk, {"core": {"n": 2}})
    ids = ["000001.SZ"]
    subset = StrategySettings.extract_execute_settings(effective)
    fp1 = FingerprintCalculator.to_execute_fingerprint(effective, ids)
    reloaded = StrategySettings.from_dict(
        {**disk, **StrategySettings.merge_disk_with_diff(disk, {"core": {"n": 2}})}
    )
    fp2 = FingerprintCalculator.to_execute_fingerprint(reloaded, ids)
    assert StrategySettings.extract_execute_settings(reloaded) == subset
    assert fp1 == fp2


def test_to_dict_does_not_mutate_execute_fp() -> None:
    import copy

    disk = _disk()
    effective, _ = StrategySettings.calculate_effective_settings(disk, {})
    ids = ["000001.SZ"]
    before = FingerprintCalculator.to_execute_fingerprint(effective, ids)
    raw_before = copy.deepcopy(effective.raw_settings)
    try:
        effective.to_dict()
    except ValueError:
        pass
    assert effective.raw_settings == raw_before
    assert FingerprintCalculator.to_execute_fingerprint(effective, ids) == before
    archived = dict(effective.raw_settings)
    assert FingerprintCalculator.to_execute_fingerprint(
        StrategySettings.from_dict(archived), ids
    ) == before


def test_execute_fp_changes_when_period_or_entity_ids_change() -> None:
    settings = StrategySettings.from_dict(_disk())
    base = FingerprintCalculator.to_execute_fingerprint(settings, ["000001.SZ"])
    other_ids = FingerprintCalculator.to_execute_fingerprint(settings, ["000002.SZ"])
    other_order = FingerprintCalculator.to_execute_fingerprint(
        settings, ["000002.SZ", "000001.SZ"]
    )
    same_order = FingerprintCalculator.to_execute_fingerprint(
        settings, ["000001.SZ", "000002.SZ"]
    )
    shifted = StrategySettings.from_dict(
        {
            **_disk(),
            "simulation": {
                "execution": {
                    "mode": "entity_based",
                    "start_date": "20200101",
                    "end_date": "20210101",
                }
            },
        }
    )
    other_period = FingerprintCalculator.to_execute_fingerprint(shifted, ["000001.SZ"])
    assert base != other_ids
    assert other_order == same_order
    assert base != other_period


def test_env_fp_ignores_period_mode_and_entity_ids() -> None:
    info = _info(_disk())
    env_a = FingerprintCalculator.to_env_fingerprint(info)
    info_shifted = _info(
        {
            **_disk(),
            "simulation": {
                "execution": {
                    "mode": "slice_based",
                    "start_date": "19900101",
                    "end_date": "19901231",
                }
            },
        }
    )
    env_b = FingerprintCalculator.to_env_fingerprint(info_shifted)
    assert env_a == env_b
    result = FingerprintCalculator.calculate_fingerprints(
        info, {}, entity_ids=["000001.SZ"]
    )
    result_other = FingerprintCalculator.calculate_fingerprints(
        info, {}, entity_ids=["000002.SZ"]
    )
    assert result.env_fp == result_other.env_fp
    assert result.execute_fp != result_other.execute_fp


def test_calculate_fingerprints_result_has_no_entity_cache() -> None:
    result = FingerprintCalculator.calculate_fingerprints(
        _info({"simulation": {"execution": {"mode": "entity_based"}}}),
        {},
        entity_ids=["000001.SZ"],
    )
    assert result.entity_ids == ["000001.SZ"]
    assert result.execute_fp
    assert result.env_fp
    assert not hasattr(result, "global_entity_cache")
    # 跑过 to_usable：缺省已填进 effective，后续运行与哈希同一份
    assert result.effective_settings.raw_settings["simulation"]["execution"]["mode"] == (
        "entity_based"
    )


def test_execute_fp_sparse_raw_matches_filled_defaults() -> None:
    ids = ["000001.SZ"]
    sparse = _disk()
    usable = StrategySettings.to_usable(sparse)
    filled_raw = dict(usable.raw_settings)
    dumped = usable.to_dict()
    fp_sparse = FingerprintCalculator.to_execute_fingerprint(sparse, ids)
    fp_filled = FingerprintCalculator.to_execute_fingerprint(filled_raw, ids)
    fp_dumped = FingerprintCalculator.to_execute_fingerprint(dumped, ids)
    assert fp_sparse == fp_filled
    assert fp_sparse == fp_dumped
    assert StrategySettings.extract_execute_settings(sparse) == (
        StrategySettings.extract_execute_settings(filled_raw)
    )


def test_execute_fp_rejects_unusable_settings() -> None:
    bad = {
        **_disk(),
        "simulation": {
            "execution": {
                "mode": "entity_based",
                "start_date": "20200101",
                "end_date": "20201231",
            },
            "risk_control": {"skip_enter_when": ["limit_up"]},
        },
    }
    with pytest.raises(ValueError, match="skip_enter_when"):
        FingerprintCalculator.to_execute_fingerprint(bad, ["000001.SZ"])
    with pytest.raises(ValueError, match="skip_enter_when"):
        StrategySettings.to_usable(bad)
