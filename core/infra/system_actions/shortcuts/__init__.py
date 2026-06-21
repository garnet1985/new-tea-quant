"""从 userspace 模板快捷新建策略 / Tag。"""

from core.infra.system_actions.shortcuts._shared import ScaffoldError, ScaffoldResult
from core.infra.system_actions.shortcuts.create_new_strategy.scaffold import scaffold_strategy
from core.infra.system_actions.shortcuts.create_new_tag.scaffold import scaffold_tag

__all__ = [
    "ScaffoldError",
    "ScaffoldResult",
    "scaffold_strategy",
    "scaffold_tag",
]
