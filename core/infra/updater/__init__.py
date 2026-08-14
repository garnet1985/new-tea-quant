"""升级：编排源码、数据迁移脚本注册表与 post-upgrade 收尾。

运行时从 ``userspace/system/updater`` 启动。包根仅导出 ``Updater``；类型见 ``contracts``。
CLI：``python -m core.infra.updater.core.post_upgrade run``。
"""

from .updater import Updater

__all__ = ["Updater"]
