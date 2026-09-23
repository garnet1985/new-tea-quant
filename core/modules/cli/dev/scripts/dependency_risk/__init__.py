"""依赖安装风险检测（``devcli.py cd``；pack 默认步骤）。"""

from .dependency_risk import run_dependency_check

__all__ = ["run_dependency_check"]
