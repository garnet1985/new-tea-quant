"""Class Discovery - 类自动发现工具"""
from __future__ import annotations

from typing import Dict, Type, Any, Optional, Callable, Set
from dataclasses import dataclass, field
import logging
import importlib
import pkgutil

logger = logging.getLogger(__name__)

DEFAULT_SKIP_MODULES: frozenset[str] = frozenset({"__pycache__", "__init__"})


@dataclass
class DiscoveryResult:
    """发现结果"""

    classes: Dict[str, Type] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryConfig:
    """发现配置"""

    DEFAULT_SKIP_MODULES = DEFAULT_SKIP_MODULES

    base_class: Type
    module_name_pattern: str  # 例如: "{base_module}.{name}.provider"
    class_filter: Optional[Callable[[Type], bool]] = None
    key_extractor: Optional[Callable[[Type], str]] = None
    attribute_extractors: Dict[str, Callable[[Type], Any]] = field(default_factory=dict)
    skip_modules: Set[str] = field(
        default_factory=lambda: set(DEFAULT_SKIP_MODULES)
    )
    skip_classes: Set[str] = field(default_factory=set)


class ClassDiscovery:
    """类自动发现工具"""

    def __init__(self, config: DiscoveryConfig):
        self.config = config
        self._cache: Dict[str, DiscoveryResult] = {}

    def discover(
        self,
        base_module_path: str,
        use_cache: bool = True,
    ) -> DiscoveryResult:
        """发现指定包下的所有类"""
        cache_key = base_module_path

        if use_cache and cache_key in self._cache:
            logger.debug("使用缓存发现结果: %s", base_module_path)
            return self._cache[cache_key]

        result = DiscoveryResult()

        try:
            base_package = importlib.import_module(base_module_path)
            package_paths = base_package.__path__

            for _importer, modname, ispkg in pkgutil.iter_modules(package_paths):
                if (
                    not ispkg
                    or modname in self.config.skip_modules
                    or modname.startswith("_")
                ):
                    continue

                module_path = self.config.module_name_pattern.format(
                    base_module=base_module_path,
                    name=modname,
                )

                module_classes = self._discover_classes_in_module(module_path)

                for key, cls in module_classes.items():
                    if key in result.classes:
                        existing_class = result.classes[key]
                        logger.warning(
                            "发现重复的类标识 '%s': %s 和 %s",
                            key,
                            existing_class.__name__,
                            cls.__name__,
                        )
                    else:
                        result.classes[key] = cls
                        for attr_name, extractor in self.config.attribute_extractors.items():
                            if attr_name not in result.metadata:
                                result.metadata[attr_name] = {}
                            result.metadata[attr_name][key] = extractor(cls)

            if use_cache:
                self._cache[cache_key] = result

        except ImportError:
            logger.debug("包不存在，跳过: %s", base_module_path)
        except Exception as e:
            logger.error("发现类失败 %s: %s", base_module_path, e)

        return result

    def _discover_classes_in_module(self, module_path: str) -> Dict[str, Type]:
        """发现指定模块中的所有类"""
        classes: Dict[str, Type] = {}

        try:
            module = importlib.import_module(module_path)
        except ImportError:
            return classes
        except Exception as e:
            logger.warning("导入模块失败 %s: %s", module_path, e)
            return classes

        for attr_name in dir(module):
            if attr_name in self.config.skip_classes:
                continue

            attr = getattr(module, attr_name)

            if not isinstance(attr, type):
                continue

            if not issubclass(attr, self.config.base_class):
                continue

            if attr == self.config.base_class:
                continue

            if self.config.class_filter and not self.config.class_filter(attr):
                continue

            if self.config.key_extractor:
                key = self.config.key_extractor(attr)
                if not key:
                    continue
            else:
                key = attr.__name__

            classes[key] = attr

        return classes

    @staticmethod
    def discover_class_by_path(
        class_path: str,
        base_class: Optional[Type] = None,
    ) -> Optional[Type]:
        """通过完整路径加载单个类；可选 ``issubclass`` 校验。"""
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name, None)

            if not cls or not isinstance(cls, type):
                return None

            if base_class is not None:
                if not issubclass(cls, base_class):
                    return None

            return cls

        except ImportError as e:
            logger.debug("模块不存在，跳过: %s (%s)", class_path, e)
            return None
        except Exception as e:
            logger.warning("通过路径发现类失败 %s: %s", class_path, e)
            return None

    def clear_cache(self, base_module_path: Optional[str] = None) -> None:
        """清除缓存"""
        if base_module_path:
            self._cache.pop(base_module_path, None)
        else:
            self._cache.clear()
