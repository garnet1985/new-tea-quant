"""Module Discovery - 模块自动发现工具"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set
import logging
import importlib
import pkgutil

logger = logging.getLogger(__name__)

DEFAULT_SKIP_MODULES: frozenset[str] = frozenset({"__pycache__", "__init__"})


class ModuleDiscovery:
    """模块自动发现工具（无状态；公开入口见 Discovery.discover.objects）。"""

    DEFAULT_SKIP_MODULES = DEFAULT_SKIP_MODULES

    @staticmethod
    def discover_objects(
        base_module_path: str,
        object_name: str,
        module_pattern: str = "{base_module}.{name}",
        skip_modules: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """发现一级子模块中的同名对象（fail-soft）。"""
        if skip_modules is None:
            skip_modules = set(ModuleDiscovery.DEFAULT_SKIP_MODULES)

        objects: Dict[str, Any] = {}

        try:
            base_package = importlib.import_module(base_module_path)
            package_paths = base_package.__path__

            for _importer, modname, _ispkg in pkgutil.iter_modules(package_paths):
                if modname in skip_modules or modname.startswith("_"):
                    continue

                module_path = module_pattern.format(
                    base_module=base_module_path,
                    name=modname,
                )

                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, object_name):
                        objects[modname] = getattr(module, object_name)
                    else:
                        logger.debug("模块 %s 没有定义 %s", module_path, object_name)
                except ImportError:
                    continue
                except Exception as e:
                    logger.warning("加载模块失败 %s: %s", module_path, e)
                    continue

            logger.debug("发现 %s 个 %s 对象", len(objects), object_name)

        except ImportError:
            logger.debug("包不存在，跳过: %s", base_module_path)
        except Exception as e:
            logger.error("发现对象失败 %s: %s", base_module_path, e)

        return objects
