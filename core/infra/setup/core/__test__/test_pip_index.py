from __future__ import annotations

import pytest

from core.infra.setup.core import pip_index as pi


@pytest.fixture(autouse=True)
def _reset_pip_index():
    pi.reset_for_tests()
    yield
    pi.reset_for_tests()


def test_env_forces_china_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_CHINA_MIRROR", "1")
    monkeypatch.setattr(pi.Utils, "is_china", staticmethod(lambda: False))
    monkeypatch.setattr(pi, "pypi_reachable", lambda: True)
    assert pi.use_china_mirror() is True
    flags = pi.pip_net_flags()
    assert pi.TSINGHUA_SIMPLE in flags


def test_env_forces_official_pypi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_CHINA_MIRROR", "0")
    monkeypatch.setattr(pi.Utils, "is_china", staticmethod(lambda: True))
    monkeypatch.setattr(pi, "pypi_reachable", lambda: False)
    assert pi.use_china_mirror() is False
    assert "-i" not in pi.pip_net_flags()


def test_china_locale_uses_mirror_without_probing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USE_CHINA_MIRROR", raising=False)
    monkeypatch.setattr(pi.Utils, "is_china", staticmethod(lambda: True))
    probed = []
    monkeypatch.setattr(pi, "pypi_reachable", lambda: probed.append(True) or True)
    assert pi.use_china_mirror() is True
    assert probed == []


def test_overseas_uses_pypi_when_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USE_CHINA_MIRROR", raising=False)
    monkeypatch.setattr(pi.Utils, "is_china", staticmethod(lambda: False))
    monkeypatch.setattr(pi, "pypi_reachable", lambda: True)
    assert pi.use_china_mirror() is False
    assert "-i" not in pi.pip_net_flags()


def test_overseas_falls_back_to_mirror_when_pypi_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USE_CHINA_MIRROR", raising=False)
    monkeypatch.setattr(pi.Utils, "is_china", staticmethod(lambda: False))
    monkeypatch.setattr(pi, "pypi_reachable", lambda: False)
    assert pi.use_china_mirror() is True
