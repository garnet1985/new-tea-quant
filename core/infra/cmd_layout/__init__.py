"""命令行布局助手（CmdLayout）。

公开 API：
- ``from core.infra.cmd_layout import CmdLayout``
- ``from core.infra.cmd_layout import i`` — 图标短入口（Windows 安全）

契约见根目录 ``API.md``。
"""

from .cmd_layout import CmdLayout

# 短入口：等价于 CmdLayout.icon.i / IconService.get
i = CmdLayout.icon.i

__all__ = ["CmdLayout", "i"]
