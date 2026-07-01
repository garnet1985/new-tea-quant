"""执行管理宿主适配：BFF（异步 job）与 CLI（阻塞）。"""

from .bff import submit_workbench_step_via_bff_contract
from .cli import run_workbench_step_via_cli_contract

__all__ = [
    "run_workbench_step_via_cli_contract",
    "submit_workbench_step_via_bff_contract",
]
