"""Strategy 模块公开 API。"""

from .contracts import ExecutionMode, SellReason, SimulateKind
from .strategy import Strategy

# TODO: [legacy-bridge] 迁移完成后删除整块兼容逻辑：
#   - 用户策略文件的 import 路径（engines.simulator.* → core.engines.*）
#   - tag 模块 calendar_slice runtime import
#   - strategy_legacy 交叉 import

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_THIS_DIR = Path(__file__).parent
_CORE_DIR = _THIS_DIR / "core"


def _register_virtual_module(full_name: str, real_path: Path) -> None:
    """临时注册虚拟模块路径（兼容旧 import）。"""
    if full_name in sys.modules:
        return
    spec = spec_from_file_location(full_name, real_path)
    if spec and spec.loader:
        module = module_from_spec(spec)
        sys.modules[full_name] = module
        spec.loader.exec_module(module)


_ENGINES_CORE_DIR = _CORE_DIR / "engines"
_register_virtual_module("core.modules.strategy.core.engines", _ENGINES_CORE_DIR / "__init__.py")
_register_virtual_module("core.modules.strategy.core.engines.shared", _ENGINES_CORE_DIR / "shared" / "__init__.py")
_register_virtual_module(
    "core.modules.strategy.core.engines.shared.data_classes",
    _ENGINES_CORE_DIR / "shared" / "data_classes" / "__init__.py",
)
_register_virtual_module(
    "core.modules.strategy.core.engines.shared.data_classes.calendar_as_of",
    _ENGINES_CORE_DIR / "shared" / "data_classes" / "calendar_as_of" / "__init__.py",
)
_register_virtual_module(
    "core.modules.strategy.core.engines.enumerator",
    _ENGINES_CORE_DIR / "enumerator" / "__init__.py",
)

sys.modules["core.modules.strategy.engines"] = sys.modules["core.modules.strategy.core.engines"]
sys.modules["core.modules.strategy.engines.shared"] = sys.modules["core.modules.strategy.core.engines.shared"]
sys.modules["core.modules.strategy.engines.shared.data_classes"] = sys.modules[
    "core.modules.strategy.core.engines.shared.data_classes"
]
sys.modules["core.modules.strategy.engines.shared.data_classes.opportunity"] = sys.modules[
    "core.modules.strategy.core.engines.shared.data_classes.opportunity"
]

# TODO: [legacy-bridge] calendar_sliced runtime 仍在 strategy_legacy；此映射不完整
sys.modules["core.modules.strategy.engines.simulator"] = sys.modules["core.modules.strategy.core.engines.enumerator"]
sys.modules["core.modules.strategy.engines.simulator.enumerator"] = sys.modules[
    "core.modules.strategy.core.engines.enumerator"
]
sys.modules["core.modules.strategy.engines.simulator.enumerator.calendar_sliced"] = sys.modules[
    "core.modules.strategy.core.engines.shared.data_classes"
]
sys.modules["core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types"] = sys.modules[
    "core.modules.strategy.core.engines.shared.data_classes.calendar_as_of"
]

_HOOKS_CORE_DIR = _CORE_DIR / "hooks"
_register_virtual_module("core.modules.strategy.core.hooks", _HOOKS_CORE_DIR / "__init__.py")
_register_virtual_module("core.modules.strategy.core.hooks.base", _HOOKS_CORE_DIR / "base.py")
sys.modules["core.modules.strategy.hooks"] = sys.modules["core.modules.strategy.core.hooks"]

_register_virtual_module(
    "core.modules.strategy.core.engines.shared.data_classes.opportunity",
    _ENGINES_CORE_DIR / "shared" / "data_classes" / "opportunity.py",
)


__all__ = ["Strategy", "ExecutionMode", "SellReason", "SimulateKind"]
