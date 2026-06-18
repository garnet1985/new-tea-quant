#!/usr/bin/env python3
"""从磁盘加载 tag_worker（嵌套目录，不依赖 userspace 包路径）。"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple, Type

from core.modules.tag.engines.shared.base_worker import BaseTagWorker

from .path_rules import tag_module_id

logger = logging.getLogger(__name__)


def load_tag_worker_class(
    tag_folder: Path,
    tag_key: str,
) -> Optional[Tuple[str, str, Path, Type[BaseTagWorker]]]:
    """
    加载 tag worker 类。

    Returns:
        ``(worker_module_path, worker_class_name, worker_file_path, worker_class)``
    """
    folder = Path(tag_folder)
    worker_file = folder / "tag_worker.py"
    if not worker_file.is_file():
        return None

    module_id = tag_module_id(tag_key, suffix="worker")
    try:
        spec = importlib.util.spec_from_file_location(module_id, worker_file)
        if spec is None or spec.loader is None:
            logger.warning("无法为 tag_worker 创建 module spec: %s", worker_file)
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_id] = module
        spec.loader.exec_module(module)

        worker_class: Optional[Type[BaseTagWorker]] = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseTagWorker)
                and attr is not BaseTagWorker
            ):
                worker_class = attr
                break
        if worker_class is None:
            logger.warning("Tag 场景 %s 未找到 BaseTagWorker 子类", tag_key)
            return None
        return (
            module_id,
            worker_class.__name__,
            worker_file.resolve(),
            worker_class,
        )
    except Exception as exc:
        logger.error("加载 tag worker 失败: %s, error=%s", tag_key, exc)
        return None


def import_tag_worker_class(
    *,
    worker_module_path: str,
    worker_class_name: str,
    worker_file_path: str = "",
) -> Type[BaseTagWorker]:
    """主进程 / 子进程共用：优先 import 已注册模块，否则按文件路径加载。"""
    mod_path = str(worker_module_path or "").strip()
    cls_name = str(worker_class_name or "").strip()
    if not mod_path or not cls_name:
        raise ValueError("worker_module_path and worker_class_name are required")

    try:
        module = importlib.import_module(mod_path)
        worker_class = getattr(module, cls_name, None)
        if (
            isinstance(worker_class, type)
            and issubclass(worker_class, BaseTagWorker)
            and worker_class is not BaseTagWorker
        ):
            return worker_class
    except Exception:
        pass

    file_path = Path(str(worker_file_path or "").strip())
    if not file_path.is_file():
        raise ValueError(f"cannot import tag worker: {mod_path}")

    spec = importlib.util.spec_from_file_location(mod_path, file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load tag worker module from file: {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_path] = module
    spec.loader.exec_module(module)
    worker_class = getattr(module, cls_name, None)
    if (
        not isinstance(worker_class, type)
        or not issubclass(worker_class, BaseTagWorker)
        or worker_class is BaseTagWorker
    ):
        raise ValueError(f"tag worker class not found: {cls_name}")
    return worker_class


__all__ = ["import_tag_worker_class", "load_tag_worker_class"]
