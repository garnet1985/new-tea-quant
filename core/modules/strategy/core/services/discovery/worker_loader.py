"""从磁盘加载策略 hooks 类。"""
from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Optional, Tuple, Type

from .path_rules import StrategyPathRules

logger = logging.getLogger(__name__)


class StrategyWorkerLoader:
    """策略 strategy.py 中 hooks 类的动态加载。"""

    @classmethod
    def load_hooks_class(
        cls,
        strategy_folder: Path,
        strategy_key: str,
    ) -> Optional[Tuple[str, str, Path, Type]]:
        """加载 hooks 类；失败返回 None。"""
        folder = Path(strategy_folder)
        worker_file = folder / "strategy.py"
        if not worker_file.is_file():
            return None

        module_id = StrategyPathRules.strategy_module_id(strategy_key, suffix="strategy")

        try:
            spec = importlib.util.spec_from_file_location(module_id, worker_file)
            if spec is None or spec.loader is None:
                logger.warning("Cannot create module spec for worker: %s", worker_file)
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            hooks_class: Optional[Type] = None
            hooks_class_name: Optional[str] = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and not attr_name.startswith("_"):
                    if attr.__module__ == module_id or attr.__module__.startswith("_ntq_strategy_"):
                        hooks_class = attr
                        hooks_class_name = attr_name
                        break

            if hooks_class is None:
                logger.warning("Strategy %s missing hooks class", strategy_key)
                return None

            return (
                module_id,
                hooks_class_name,
                worker_file.resolve(),
                hooks_class,
            )
        except Exception as exc:
            logger.error("Failed to load hooks: %s, error=%s", strategy_key, exc)
            return None

    @classmethod
    def import_hooks_class(
        cls,
        *,
        worker_module_path: str,
        worker_class_name: str,
        worker_file_path: str = "",
    ) -> Type:
        """主进程 / 子进程共用：优先 import 已注册模块，否则按文件路径加载。"""
        from core.modules.strategy.core.hooks.base import StrategyHooks

        mod_path = str(worker_module_path or "").strip()
        cls_name = str(worker_class_name or "").strip()
        if not mod_path or not cls_name:
            raise ValueError("worker_module_path and worker_class_name are required")

        try:
            module = importlib.import_module(mod_path)
            hooks_class = getattr(module, cls_name, None)
            if (
                isinstance(hooks_class, type)
                and issubclass(hooks_class, StrategyHooks)
                and hooks_class is not StrategyHooks
            ):
                return hooks_class
        except Exception:
            pass

        file_path = Path(str(worker_file_path or "").strip())
        if not file_path.is_file():
            raise ValueError(f"cannot import strategy hooks: {mod_path}")

        spec = importlib.util.spec_from_file_location(mod_path, file_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot load hooks module from file: {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        hooks_class = getattr(module, cls_name, None)
        if (
            not isinstance(hooks_class, type)
            or not issubclass(hooks_class, StrategyHooks)
            or hooks_class is StrategyHooks
        ):
            raise ValueError(f"invalid hooks class {cls_name!r} in {file_path}")
        return hooks_class


__all__ = ["StrategyWorkerLoader"]
