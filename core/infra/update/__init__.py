"""升级扩展：数据迁移脚本注册表与 post-upgrade 收尾。

编排 / 版本探测见 ``setup/updater/``。包根仅导出 ``Update``；类型见 ``contracts``。
CLI 兼容：``python -m core.infra.update.post_upgrade run``。
"""

from .update import Update

__all__ = ["Update"]
