"""从磁盘动态加载用户 ``tag.py`` 中的 hooks 类。

消费者: TagDraft / DiscoveredTagInfo, 后续 engines

本文件:
- TagHooksLoader: importlib 加载 + 查找公开 TagHooks 子类
  边界: 负责模块 spec 与类解析；不负责 settings 校验或 hook 调用
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple, Type

from .constants import TAG_FILE_NAME
from .path_rules import TagPathRules

logger = logging.getLogger(__name__)


class TagHooksLoader:
    """从 ``tag.py`` 动态加载用户 hooks 类。"""

    @classmethod
    def load_hooks_class(
        cls,
        tag_folder: Path,
        tag_key: str,
    ) -> Optional[Tuple[str, str, Path, Type]]:
        """加载 hooks 类；失败返回 None。

        Returns:
            ``(hooks_module_path, hooks_class_name, hooks_file_path, hooks_class)``
        """
        folder = Path(tag_folder)
        hooks_file = folder / TAG_FILE_NAME
        if not hooks_file.is_file():
            return None

        module_id = TagPathRules.tag_module_id(tag_key, suffix="tag")

        try:
            spec = importlib.util.spec_from_file_location(module_id, hooks_file)
            if spec is None or spec.loader is None:
                logger.warning("Cannot create module spec for tag hooks: %s", hooks_file)
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_id] = module
            spec.loader.exec_module(module)

            from core.modules.tag.core.engines.shared.hooks.tag_hooks import TagHooks

            hooks_class: Optional[Type] = None
            hooks_class_name: Optional[str] = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if not isinstance(attr, type) or attr_name.startswith("_"):
                    continue
                if attr is TagHooks or not issubclass(attr, TagHooks):
                    continue
                if attr.__module__ == module_id or attr.__module__.startswith(
                    "_ntq_tag_"
                ):
                    hooks_class = attr
                    hooks_class_name = attr_name
                    break

            if hooks_class is None:
                logger.warning("Tag %s missing hooks class", tag_key)
                return None

            return (
                module_id,
                hooks_class_name,
                hooks_file.resolve(),
                hooks_class,
            )
        except Exception as exc:
            logger.error("Failed to load tag hooks: %s, error=%s", tag_key, exc)
            return None

    @classmethod
    def import_hooks_class(
        cls,
        *,
        hooks_module_path: str,
        hooks_class_name: str,
        hooks_file_path: str = "",
    ) -> Type:
        """主进程 / 子进程共用：优先 import 已注册模块，否则按文件路径加载。"""
        from core.modules.tag.core.engines.shared.hooks.tag_hooks import TagHooks

        mod_path = str(hooks_module_path or "").strip()
        cls_name = str(hooks_class_name or "").strip()
        if not mod_path or not cls_name:
            raise ValueError("hooks_module_path and hooks_class_name are required")

        try:
            module = importlib.import_module(mod_path)
            hooks_class = getattr(module, cls_name, None)
            if (
                isinstance(hooks_class, type)
                and issubclass(hooks_class, TagHooks)
                and hooks_class is not TagHooks
            ):
                return hooks_class
        except Exception:
            pass

        file_path = Path(str(hooks_file_path or "").strip())
        if not file_path.is_file():
            raise ValueError(f"cannot import tag hooks: {mod_path}")

        spec = importlib.util.spec_from_file_location(mod_path, file_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot load hooks module from file: {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_path] = module
        spec.loader.exec_module(module)
        hooks_class = getattr(module, cls_name, None)
        if (
            not isinstance(hooks_class, type)
            or not issubclass(hooks_class, TagHooks)
            or hooks_class is TagHooks
        ):
            raise ValueError(f"invalid hooks class {cls_name!r} in {file_path}")
        return hooks_class


__all__ = ["TagHooksLoader"]
