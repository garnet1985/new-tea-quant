"""安全取值工具（缺/坏字段不中断 pipeline）。

消费者: scanner, enumerator, price_factor
"""

from .safe_bar_value import SafeBarValue

__all__ = ["SafeBarValue"]
