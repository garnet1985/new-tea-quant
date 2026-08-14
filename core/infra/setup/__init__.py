"""安装域（非 setuptools 的 setup）。

公开约定：包根仅导出 ``Setup``。类型见 ``contracts``，或经 ``Setup.types``。
CLI / launcher / install.py / BFF 只应调用门面，不深挖 ``core/steps`` / ``core/scripts``。
"""

from .setup import Setup

__all__ = ["Setup"]
