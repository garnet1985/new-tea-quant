"""
Core `data_id` / `DataKey` 白名单（框架内置枚举）。

Userspace 扩展使用稳定字符串 id + 注册表，勿改本包内枚举文件。
"""

from .data_keys import DataKey

__all__ = ["DataKey"]
