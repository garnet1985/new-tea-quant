"""Python 3.9 语法兼容扫描（pack 默认步骤）。"""

from .py39_compat_check import collect_py39_compat_issues, run_py39_compat_check

__all__ = ["collect_py39_compat_issues", "run_py39_compat_check"]
