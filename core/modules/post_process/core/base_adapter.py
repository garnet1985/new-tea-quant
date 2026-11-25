"""BaseAdapter — userspace 后续处理适配器基类。"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple

from core.modules.post_process.core.protocol import ScanSessionReport

logger = logging.getLogger(__name__)


def _config_value_present(config: Dict[str, Any], key: str) -> bool:
    val = config.get(key)
    if val is None:
        return False
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, (list, tuple, set)):
        return any(str(x).strip() for x in val)
    if isinstance(val, dict):
        return bool(val)
    return True


class BaseAdapter(ABC):
    """后续处理适配器基类。

    准则:
    - 标准协议 input 为 ``ScanSessionReport``
    - ``deps`` 为所依赖 adapter 的 output（key→value）；无依赖则为 ``{}``
    - 默认遵守各 ``StrategyScanReport.goal``；改目标须用户显式写代码
    - 真发必备项用类属性声明；复杂规则覆盖 ``check_readiness``
    """

    # 真发时 config 中必须非空的键
    required_for_live: ClassVar[Tuple[str, ...]] = ()
    # 适配器目录下必须存在的文件（如 token.txt）
    required_files: ClassVar[Tuple[str, ...]] = ()
    # 真发时至少有一个存在的环境变量（与 files / config 的组合规则见 check_readiness）
    required_env: ClassVar[Tuple[str, ...]] = ()

    def __init__(self, adapter_name: Optional[str] = None):
        self.adapter_name = adapter_name or self._infer_adapter_name()

    def _infer_adapter_name(self) -> str:
        class_name = self.__class__.__name__
        for suffix in ("Adapter", "Component"):
            if class_name.endswith(suffix):
                class_name = class_name[: -len(suffix)]
                break
        return class_name.lower()

    def check_readiness(
        self,
        config: Dict[str, Any],
        *,
        adapter_directory: Optional[Path] = None,
    ) -> Tuple[bool, str]:
        """静态自检真发必备配置；缺则返回 ``(False, 原因)``。

        若 ``dry_run is True``：本方法直接通过（便于演练路径）。
        目录着色请用 ``check_adapter_readiness``（会按真发条件检查，优先级
        不可用 > 测试模式 > 可用）。

        默认将 ``required_for_live`` / ``required_files`` / ``required_env`` 视为**同时**需要满足
        （env 组内任一即可）。三选一等复杂规则请子类覆盖。
        """
        cfg = dict(config or {})
        if cfg.get("dry_run", None) is True:
            return True, ""

        missing: List[str] = []
        for key in self.required_for_live:
            if not _config_value_present(cfg, key):
                missing.append(f"config.{key}")

        if self.required_files:
            root = Path(adapter_directory) if adapter_directory else None
            if root is None:
                missing.append("adapter_directory")
            else:
                for fname in self.required_files:
                    if not (root / fname).is_file():
                        missing.append(fname)

        if self.required_env:
            if not any(str(os.environ.get(env) or "").strip() for env in self.required_env):
                missing.append(
                    "env:" + "|".join(self.required_env)
                    if len(self.required_env) > 1
                    else f"env:{self.required_env[0]}"
                )

        if missing:
            return False, "缺少：" + "、".join(missing)
        return True, ""

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
