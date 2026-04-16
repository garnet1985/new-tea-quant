from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional


class BaseLoader(ABC):
    """所有业务 loader 的抽象基类。"""

    @abstractmethod
    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        """根据参数与上下文加载数据。"""
        raise NotImplementedError

