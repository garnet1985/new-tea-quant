"""系统级操作：缓存清理、pipeline 租约、模板脚手架。

包根仅导出 ``SystemActions``；类型见 ``contracts``。
Facade 方法内懒导入，避免 BFF 冷启动拉起 strategy/tag 重链。
"""

from .system_actions import SystemActions

__all__ = ["SystemActions"]
