"""AsOfSlice — 时钟点数据切片。

消费者: scanner, enumerator

流程位置: 推进时间 → **切数据（本包）** → 执行业务
"""

from .as_of_slice import AsOfSlice

__all__ = ["AsOfSlice"]
