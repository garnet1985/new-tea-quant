"""CLI ``sa``：省略 ``--version`` 时展示该 step 最近一次归因。"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from core.infra.cli.user.handlers import UserHandlers

pytestmark = pytest.mark.force_run


def _args(**overrides):
    payload = {
        "output_dir": None,
        "strategy": "rsi_v1",
        "step": "enum",
        "version": None,
    }
    payload.update(overrides)
    return Namespace(**payload)


def test_analyze_omitted_version_presents_latest(monkeypatch):
    presented = []

    class FakeStrategy:
        @staticmethod
        def find(explicit, enabled_only=True):
            return {"key": "rsi_v1"}

        @staticmethod
        def resolve_folder(key):
            return Path("/strat")

        @staticmethod
        def present_analysis_report(path, stream=None):
            presented.append(Path(path))

        @staticmethod
        def resolve_simulation_output_dirs(*_a, **_k):
            raise AssertionError("explicit version path should not run")

    class FakeStore:
        @classmethod
        def latest(cls, folder, kind=None):
            store = cls()
            store.output_dir = Path("/strat/results/simulations/4/enum")
            store.version_id = "4"
            return store

    monkeypatch.setattr("core.modules.strategy.Strategy", FakeStrategy)
    monkeypatch.setattr(
        "core.modules.strategy.core.services.artifacts.ArtifactStore",
        FakeStore,
    )

    UserHandlers._run_strategy_analyze(_args())
    assert presented == [Path("/strat/results/simulations/4/enum")]


def test_analyze_omitted_version_exits_when_no_latest(monkeypatch):
    class FakeStrategy:
        @staticmethod
        def find(explicit, enabled_only=True):
            return {"key": "rsi_v1"}

        @staticmethod
        def resolve_folder(key):
            return Path("/strat")

        @staticmethod
        def present_analysis_report(path, stream=None):
            raise AssertionError("should not present")

    class FakeStore:
        @classmethod
        def latest(cls, folder, kind=None):
            return None

    monkeypatch.setattr("core.modules.strategy.Strategy", FakeStrategy)
    monkeypatch.setattr(
        "core.modules.strategy.core.services.artifacts.ArtifactStore",
        FakeStore,
    )

    with pytest.raises(SystemExit) as exc:
        UserHandlers._run_strategy_analyze(_args())
    assert exc.value.code == 1


def test_analyze_explicit_version_uses_that_dir(tmp_path, monkeypatch):
    presented = []
    step_dir = tmp_path / "2" / "enum"
    step_dir.mkdir(parents=True)

    class FakeStrategy:
        @staticmethod
        def find(explicit, enabled_only=True):
            return {"key": "rsi_v1"}

        @staticmethod
        def present_analysis_report(path, stream=None):
            presented.append(Path(path))

        @staticmethod
        def resolve_simulation_output_dirs(*_a, **_k):
            return [step_dir]

    monkeypatch.setattr("core.modules.strategy.Strategy", FakeStrategy)

    UserHandlers._run_strategy_analyze(_args(version="2"))
    assert presented == [step_dir]
