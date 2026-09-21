"""本机是否在中国大陆：按时区地名判断，不用 UTC+8。

公开入口：``Utils.locale.is_china()``。
"""
from __future__ import annotations

import os
from pathlib import Path

_CN_ZONE_TAILS = (
    "asia/shanghai",
    "asia/urumqi",
    "asia/chongqing",
    "asia/harbin",
    "asia/kashgar",
)


class LocaleUtils:
    """区域判断。不含网络探测。"""

    @staticmethod
    def is_china() -> bool:
        """系统时区为中国大陆 IANA 名，或语言为 zh_CN。"""
        return LocaleUtils._timezone_is_china() or LocaleUtils._locale_is_zh_cn()

    @staticmethod
    def _timezone_is_china() -> bool:
        names = [
            os.environ.get("TZ", ""),
            LocaleUtils._zoneinfo_path_name(),
            LocaleUtils._windows_timezone_name(),
        ]
        for raw in names:
            key = str(raw or "").strip().replace("\\", "/").lower()
            if not key:
                continue
            if key in {"prc", "china standard time"}:
                return True
            if any(key.endswith(tail) or f"/{tail}" in f"/{key}" for tail in _CN_ZONE_TAILS):
                return True
        return False

    @staticmethod
    def _zoneinfo_path_name() -> str:
        localtime = Path("/etc/localtime")
        try:
            if not localtime.exists():
                return ""
            resolved = str(localtime.resolve()).replace("\\", "/")
        except OSError:
            return ""
        for marker in ("/zoneinfo/", "/Time Zone Database/"):
            if marker in resolved:
                return resolved.split(marker, 1)[-1]
        return ""

    @staticmethod
    def _windows_timezone_name() -> str:
        if os.name != "nt":
            return ""
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
            ) as key:
                name, _ = winreg.QueryValueEx(key, "TimeZoneKeyName")
            return str(name or "")
        except Exception:
            return ""

    @staticmethod
    def _locale_is_zh_cn() -> bool:
        keys = (
            os.environ.get("LC_ALL")
            or os.environ.get("LC_CTYPE")
            or os.environ.get("LANG")
            or ""
        ).lower().replace("-", "_")
        return "zh_cn" in keys
