from __future__ import annotations

import pytest

from core.infra.utils.core.locale.locale_utils import LocaleUtils


def _isolate_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setattr(LocaleUtils, "_zoneinfo_path_name", staticmethod(lambda: ""))
    monkeypatch.setattr(LocaleUtils, "_windows_timezone_name", staticmethod(lambda: ""))
    monkeypatch.setattr(LocaleUtils, "_locale_is_zh_cn", staticmethod(lambda: False))


def test_is_china_from_shanghai_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_timezone(monkeypatch)
    monkeypatch.setenv("TZ", "Asia/Shanghai")
    assert LocaleUtils.is_china() is True


def test_is_china_from_urumqi(monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_timezone(monkeypatch)
    monkeypatch.setenv("TZ", "Asia/Urumqi")
    assert LocaleUtils.is_china() is True


def test_is_china_false_for_perth_singapore_hong_kong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_timezone(monkeypatch)
    for zone in ("Asia/Singapore", "Australia/Perth", "Asia/Hong_Kong"):
        monkeypatch.setenv("TZ", zone)
        monkeypatch.setattr(LocaleUtils, "_zoneinfo_path_name", staticmethod(lambda z=zone: z))
        assert LocaleUtils.is_china() is False, zone


def test_posix_utc8_is_not_china(monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_timezone(monkeypatch)
    monkeypatch.setenv("TZ", "CST-8")
    assert LocaleUtils.is_china() is False


def test_is_china_from_windows_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_timezone(monkeypatch)
    monkeypatch.setattr(
        LocaleUtils, "_windows_timezone_name", staticmethod(lambda: "China Standard Time")
    )
    assert LocaleUtils.is_china() is True


def test_is_china_from_zh_cn_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_CTYPE", raising=False)
    monkeypatch.setattr(LocaleUtils, "_zoneinfo_path_name", staticmethod(lambda: ""))
    monkeypatch.setattr(LocaleUtils, "_windows_timezone_name", staticmethod(lambda: ""))
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    assert LocaleUtils.is_china() is True
