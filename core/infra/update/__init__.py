"""升级扩展：数据迁移脚本注册表与 post-upgrade 收尾。

编排 / 版本探测见 ``setup/core/updater/``。包根仅导出 ``Update``；类型见 ``contracts``。
CLI：``python -m core.infra.update.core.post_upgrade run``。
"""

from .update import Update

__all__ = ["Update"]
