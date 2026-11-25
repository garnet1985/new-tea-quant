"""Python 3.11 语法兼容扫描（pack 默认步骤）。"""

from .py311_compat_check import collect_py311_compat_issues, run_py311_compat_check

__all__ = ["collect_py311_compat_issues", "run_py311_compat_check"]
