from __future__ import annotations

import pytest

from core.infra.utils.core.locale.locale_utils import LocaleUtils
from core.infra.utils.core.pkg_index import PkgIndex


@pytest.fixture(autouse=True)
def _reset_pkg_index():
    PkgIndex.reset_for_tests()
    yield
    PkgIndex.reset_for_tests()


def test_env_forces_china_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_CHINA_MIRROR", "1")
    monkeypatch.setattr(LocaleUtils, "is_china", staticmethod(lambda: False))
    monkeypatch.setattr(PkgIndex, "pypi_reachable", staticmethod(lambda: True))
    assert PkgIndex.use_china_mirror() is True
    flags = PkgIndex.pip_args()
    assert PkgIndex.PYPI_MIRROR in flags
    env = PkgIndex.npm_env({})
    assert env["npm_config_registry"] == PkgIndex.NPM_MIRROR
    assert env["npm_config_replace_registry_host"] == "always"


def test_env_forces_official(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_CHINA_MIRROR", "0")
    monkeypatch.setattr(LocaleUtils, "is_china", staticmethod(lambda: True))
    monkeypatch.setattr(PkgIndex, "pypi_reachable", staticmethod(lambda: False))
    assert PkgIndex.use_china_mirror() is False
    assert "-i" not in PkgIndex.pip_args()
    assert PkgIndex.npm_env({})["npm_config_registry"] == PkgIndex.NPM_OFFICIAL


def test_china_locale_uses_mirror_without_probing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USE_CHINA_MIRROR", raising=False)
    monkeypatch.setattr(LocaleUtils, "is_china", staticmethod(lambda: True))
    probed = []
    monkeypatch.setattr(
        PkgIndex,
        "pypi_reachable",
        staticmethod(lambda: probed.append(True) or True),
    )
    assert PkgIndex.use_china_mirror() is True
    assert probed == []


def test_overseas_uses_official_when_pypi_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USE_CHINA_MIRROR", raising=False)
    monkeypatch.setattr(LocaleUtils, "is_china", staticmethod(lambda: False))
    monkeypatch.setattr(PkgIndex, "pypi_reachable", staticmethod(lambda: True))
    assert PkgIndex.use_china_mirror() is False
    assert "-i" not in PkgIndex.pip_args()


def test_overseas_falls_back_to_mirror_when_pypi_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USE_CHINA_MIRROR", raising=False)
    monkeypatch.setattr(LocaleUtils, "is_china", staticmethod(lambda: False))
    monkeypatch.setattr(PkgIndex, "pypi_reachable", staticmethod(lambda: False))
    assert PkgIndex.use_china_mirror() is True
    assert PkgIndex.npm_env({})["npm_config_registry"] == PkgIndex.NPM_MIRROR


def test_run_pip_retries_next_china_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_CHINA_MIRROR", "1")
    calls: list[list[str]] = []

    def _run(cmd, **_kwargs):
        calls.append(list(cmd))
        # first attempt fails, second succeeds
        code = 0 if len(calls) > 1 else 1
        return type("Proc", (), {"returncode": code})()

    monkeypatch.setattr("core.infra.utils.core.pkg_index.subprocess.run", _run)
    assert PkgIndex.run_pip(["install", "xgboost>=2.0"]) == 0
    assert len(calls) == 2
    assert "pypi.mirrors.ustc.edu.cn" in " ".join(calls[0])
    assert "pypi.tuna.tsinghua.edu.cn" in " ".join(calls[1])
