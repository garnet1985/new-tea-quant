"""Unit tests for JobBundleLoader windowed load API."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
    JobBundleLoader,
)


def _payload() -> dict:
    return {
        "entity_specified": [{"id": "a"}, {"id": "b"}],
        "entity_shared": {
            "kline": {
                "params": {},
                "start": "20200101",
                "end": "20201231",
                "indicators": {},
            }
        },
        "global": {},
        "shm_info": {},
    }


def test_load_per_entity_window_overrides_payload_bounds() -> None:
    contract = MagicMock()
    contract.is_loaded = True
    contract.data = {"a": []}

    with patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.ContractIssuer.issue",
        return_value=contract,
    ) as issue, patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.ContractIndicators.apply",
    ):
        out = JobBundleLoader.load_per_entity_window(
            _payload(),
            start="20200301",
            end="20200320",
        )

    assert out == {"kline": contract}
    runtime = issue.call_args.kwargs["runtime"]
    assert runtime["start"] == "20200301"
    assert runtime["end"] == "20200320"
    assert runtime["entity_ids"] == ["a", "b"]


def test_load_globals_skips_without_shm() -> None:
    assert JobBundleLoader.load_globals(_payload()) == {}


def test_load_still_uses_entity_shared_window() -> None:
    contract = MagicMock()
    contract.is_loaded = True
    contract.data = {"a": []}

    with patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.ContractIssuer.issue",
        return_value=contract,
    ) as issue, patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.ContractIndicators.apply",
    ):
        out = JobBundleLoader.load(_payload())

    assert out["entity_contracts"] == {"kline": contract}
    assert out["global_data"] == {}
    runtime = issue.call_args.kwargs["runtime"]
    assert runtime["start"] == "20200101"
    assert runtime["end"] == "20201231"
