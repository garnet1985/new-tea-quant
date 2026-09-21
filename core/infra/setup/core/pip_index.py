"""pip 源选择：国内走清华镜像，国外走 PyPI。

优先级：``USE_CHINA_MIRROR=1/0`` 显式覆盖 → ``Utils.is_china()`` → pypi.org 短探不通则镜像。
"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from typing import Optional

from core.infra.utils import Utils

TSINGHUA_SIMPLE = "https://pypi.tuna.tsinghua.edu.cn/simple"
TSINGHUA_HOST = "pypi.tuna.tsinghua.edu.cn"
PYPI_PROBE_URL = "https://pypi.org/simple/pip/"
PIP_TIMEOUT_SEC = 15
PIP_RETRIES = 1
PYPI_PROBE_SEC = 2.0

_auto_cache: Optional[bool] = None
_announced = False


def reset_for_tests() -> None:
    global _auto_cache, _announced
    _auto_cache = None
    _announced = False


def _env_flag(name: str) -> Optional[bool]:
    raw = os.environ.get(name, "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return None


def pypi_reachable(timeout: float = PYPI_PROBE_SEC) -> bool:
    try:
        urllib.request.urlopen(PYPI_PROBE_URL, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def use_china_mirror() -> bool:
    """国内（或 PyPI 不通）走清华镜像；国外且 PyPI 可达走官方源。"""
    global _auto_cache
    forced = _env_flag("USE_CHINA_MIRROR")
    if forced is not None:
        return forced
    if _auto_cache is None:
        if Utils.is_china():
            _auto_cache = True
        else:
            _auto_cache = not pypi_reachable()
    return bool(_auto_cache)


def pip_net_flags() -> list:
    flags = [
        "--disable-pip-version-check",
        "--timeout",
        str(PIP_TIMEOUT_SEC),
        "--retries",
        str(PIP_RETRIES),
    ]
    if _env_flag("NTQ_PIP_NO_CACHE") is True:
        flags.append("--no-cache-dir")
    if use_china_mirror():
        flags.extend(["-i", TSINGHUA_SIMPLE, "--trusted-host", TSINGHUA_HOST])
    return flags


def pip_network_hint() -> str:
    return (
        "无法连接 PyPI（或超时）。可强制镜像或官方源：\n"
        "  USE_CHINA_MIRROR=1 python install.py\n"
        "  USE_CHINA_MIRROR=0 python install.py"
    )


def announce_pip_index() -> None:
    global _announced
    if _announced:
        return
    _announced = True
    forced = _env_flag("USE_CHINA_MIRROR")
    if forced is True:
        print("使用清华 PyPI 镜像（USE_CHINA_MIRROR=1）", file=sys.stderr, flush=True)
        return
    if forced is False:
        print("使用官方 PyPI（USE_CHINA_MIRROR=0）", file=sys.stderr, flush=True)
        return
    if use_china_mirror():
        if Utils.is_china():
            print("检测到国内环境，使用清华 PyPI 镜像", file=sys.stderr, flush=True)
        else:
            print("无法快速连接 PyPI，改用清华镜像", file=sys.stderr, flush=True)


def parse_pkg_version(raw: str) -> tuple:
    nums = []
    for part in str(raw).split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        nums.append(int(digits))
    return tuple(nums) if nums else (0,)


def version_meets(installed: str, minimum: tuple) -> bool:
    if not installed:
        return False
    got = parse_pkg_version(installed)
    n = max(len(got), len(minimum))
    got = got + (0,) * (n - len(got))
    need = minimum + (0,) * (n - len(minimum))
    return got >= need


def installed_version(name: str) -> str:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return ""


def pip_meets_minimum(minimum: tuple = (24, 0)) -> bool:
    return version_meets(installed_version("pip"), minimum)
