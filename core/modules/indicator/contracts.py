"""跨模块契约：指标计算结果类型。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union

# compute_batch 单项: (指标名, 参数, 结果)
BatchIndicatorResult = Tuple[
    str, Dict[str, Any], Union[List[float], Dict[str, List[float]]]
]

__all__ = ["BatchIndicatorResult"]
