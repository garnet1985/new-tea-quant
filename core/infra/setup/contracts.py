"""setup 公开类型（经 ``Setup.types`` 或本模块导入）。"""
from __future__ import annotations

from typing import Literal

InstallProfileName = Literal["ui", "cli"]
CliInstallScope = Literal["full", "deps_only", "none"]
InstallEntry = Literal["ui", "cli"]
AppEntry = Literal["ui", "cli", "devcli"]

__all__ = [
    "AppEntry",
    "CliInstallScope",
    "InstallEntry",
    "InstallProfileName",
]
