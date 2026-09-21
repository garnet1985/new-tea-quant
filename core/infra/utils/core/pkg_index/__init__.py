"""pip / npm 源：国内走镜像，国外走官方。

优先级：``USE_CHINA_MIRROR=1/0`` → ``LocaleUtils.is_china()`` → pypi.org 短探不通则镜像。
公开入口：``Utils.pkg``。
"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from typing import Mapping, Optional

from core.infra.utils.core.locale.locale_utils import LocaleUtils

PYPI_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
PYPI_MIRROR_HOST = "pypi.tuna.tsinghua.edu.cn"
PYPI_PROBE_URL = "https://pypi.org/simple/pip/"
NPM_MIRROR = "https://registry.npmmirror.com"
NPM_OFFICIAL = "https://registry.npmjs.org"
PIP_TIMEOUT_SEC = 15
PIP_RETRIES = 1
PYPI_PROBE_SEC = 2.0
NPM_FETCH_TIMEOUT_MS = 15000
NPM_FETCH_RETRIES = 1


class PkgIndex:
    """安装外部依赖时的 pip / npm 网络参数。"""

    PYPI_MIRROR = PYPI_MIRROR
    PYPI_MIRROR_HOST = PYPI_MIRROR_HOST
    NPM_MIRROR = NPM_MIRROR
    NPM_OFFICIAL = NPM_OFFICIAL

    _auto_cache: Optional[bool] = None
    _announced = False

    @staticmethod
    def reset_for_tests() -> None:
        PkgIndex._auto_cache = None
        PkgIndex._announced = False

    @staticmethod
    def _env_flag(name: str) -> Optional[bool]:
        raw = os.environ.get(name, "").strip().lower()
        if raw in ("1", "true", "yes"):
            return True
        if raw in ("0", "false", "no"):
            return False
        return None

    @staticmethod
    def pypi_reachable(timeout: float = PYPI_PROBE_SEC) -> bool:
        try:
            urllib.request.urlopen(PYPI_PROBE_URL, timeout=timeout)
            return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    @staticmethod
    def use_china_mirror() -> bool:
        """国内（或 PyPI 不通）走镜像；国外且 PyPI 可达走官方源。"""
        forced = PkgIndex._env_flag("USE_CHINA_MIRROR")
        if forced is not None:
            return forced
        if PkgIndex._auto_cache is None:
            if LocaleUtils.is_china():
                PkgIndex._auto_cache = True
            else:
                PkgIndex._auto_cache = not PkgIndex.pypi_reachable()
        return bool(PkgIndex._auto_cache)

    @staticmethod
    def pip_args() -> list:
        flags = [
            "--disable-pip-version-check",
            "--timeout",
            str(PIP_TIMEOUT_SEC),
            "--retries",
            str(PIP_RETRIES),
        ]
        if PkgIndex._env_flag("NTQ_PIP_NO_CACHE") is True:
            flags.append("--no-cache-dir")
        if PkgIndex.use_china_mirror():
            flags.extend(["-i", PYPI_MIRROR, "--trusted-host", PYPI_MIRROR_HOST])
        return flags

    @staticmethod
    def npm_env(base: Optional[Mapping[str, str]] = None) -> dict:
        """给 ``npm install`` 用的环境。国内写 npmmirror，并限制 fetch 超时。"""
        env = dict(os.environ if base is None else base)
        env["npm_config_fetch_timeout"] = str(NPM_FETCH_TIMEOUT_MS)
        env["npm_config_fetch_retries"] = str(NPM_FETCH_RETRIES)
        if PkgIndex.use_china_mirror():
            env["npm_config_registry"] = NPM_MIRROR
            env["npm_config_replace_registry_host"] = "always"
        else:
            env.setdefault("npm_config_registry", NPM_OFFICIAL)
        return env

    @staticmethod
    def pip_hint() -> str:
        return (
            "无法连接依赖源（或超时）。可强制镜像或官方源：\n"
            "  USE_CHINA_MIRROR=1 python install.py\n"
            "  USE_CHINA_MIRROR=0 python install.py"
        )

    @staticmethod
    def announce() -> None:
        if PkgIndex._announced:
            return
        PkgIndex._announced = True
        forced = PkgIndex._env_flag("USE_CHINA_MIRROR")
        if forced is True:
            print(
                "使用国内镜像（pip: 清华，npm: npmmirror）（USE_CHINA_MIRROR=1）",
                file=sys.stderr,
                flush=True,
            )
            return
        if forced is False:
            print("使用官方源（PyPI / npmjs）（USE_CHINA_MIRROR=0）", file=sys.stderr, flush=True)
            return
        if PkgIndex.use_china_mirror():
            if LocaleUtils.is_china():
                print(
                    "检测到国内环境，pip 使用清华镜像，npm 使用 npmmirror",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                print(
                    "无法快速连接 PyPI，pip / npm 改用国内镜像",
                    file=sys.stderr,
                    flush=True,
                )

    @staticmethod
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

    @staticmethod
    def version_meets(installed: str, minimum: tuple) -> bool:
        if not installed:
            return False
        got = PkgIndex.parse_pkg_version(installed)
        n = max(len(got), len(minimum))
        got = got + (0,) * (n - len(got))
        need = minimum + (0,) * (n - len(minimum))
        return got >= need

    @staticmethod
    def installed_version(name: str) -> str:
        try:
            from importlib.metadata import version

            return version(name)
        except Exception:
            return ""

    @staticmethod
    def pip_meets_minimum(minimum: tuple = (24, 0)) -> bool:
        return PkgIndex.version_meets(PkgIndex.installed_version("pip"), minimum)
