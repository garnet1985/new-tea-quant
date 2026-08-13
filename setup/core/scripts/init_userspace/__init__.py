"""将仓库根 ``userspace/`` 同步到 ``setup/init_userspace/`` 并生成 zip。"""

from .package import package_init_userspace

__all__ = ["package_init_userspace"]
