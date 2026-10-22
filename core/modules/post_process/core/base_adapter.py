"""BaseAdapter — userspace 后续处理适配器基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

from core.modules.post_process.core.protocol import ScanSessionReport

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """后续处理适配器基类。

    准则:
    - 标准协议 input 为 ``ScanSessionReport``
    - ``deps`` 为所依赖 adapter 的 output（key→value）；无依赖则为 ``{}``
    - 默认遵守各 ``StrategyScanReport.goal``；改目标须用户显式写代码
    """

    def __init__(self, adapter_name: Optional[str] = None):
        self.adapter_name = adapter_name or self._infer_adapter_name()

    def _infer_adapter_name(self) -> str:
        class_name = self.__class__.__name__
        for suffix in ("Adapter", "Component"):
            if class_name.endswith(suffix):
                class_name = class_name[: -len(suffix)]
                break
        return class_name.lower()

    @abstractmethod
    def run(
        self,
        session: ScanSessionReport,
        config: Dict[str, Any],
        deps: Dict[str, Any],
    ) -> Any:
        """执行适配器；返回值可供依赖本适配器的其它适配器经 ``deps`` 读取。"""

    def log_info(self, message: str) -> None:
        logger.info("[%s] %s", self.adapter_name, message)

    def log_warning(self, message: str) -> None:
        logger.warning("[%s] %s", self.adapter_name, message)

    def log_error(self, message: str, *, exc_info: bool = False) -> None:
        logger.error("[%s] %s", self.adapter_name, message, exc_info=exc_info)


__all__ = ["BaseAdapter"]
