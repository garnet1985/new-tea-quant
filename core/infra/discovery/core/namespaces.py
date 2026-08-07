"""命名空间 API - 提供清晰的命名空间访问方式"""
from typing import Dict, Type, Any, Optional, Callable, List, Union
from pathlib import Path

from .file_utils import FileUtils
from .file_discovery import FileDiscovery, FileDiscoveryConfig
from .class_discovery import ClassDiscovery, DiscoveryConfig
from .module_discovery import ModuleDiscovery


class FileNamespace:
    """文件操作命名空间"""

    @staticmethod
    def find_file(
        start_dir: Path,
        filename: str,
        *,
        search_parents: bool = False,
        max_depth: int = 10
    ) -> Optional[Path]:
        """查找单个文件"""
        return FileUtils.find_file(start_dir, filename, search_parents=search_parents, max_depth=max_depth)

    @staticmethod
    def find_in_tree(
        base_dir: Path,
        key: str,
        filename: str,
    ) -> Optional[Path]:
        """按目录名 ``key`` 在树中定位 ``{key}/{filename}``（直达或嵌套）。"""
        return FileUtils.find_in_tree(base_dir, key, filename)

    @staticmethod
    def load_file_content(
        file_path: Path,
        *,
        encoding: str = 'utf-8',
        auto_detect_format: bool = True
    ) -> Union[str, Dict[str, Any], bytes, None]:
        """加载文件内容"""
        return FileUtils.load_file_content(file_path, encoding=encoding, auto_detect_format=auto_detect_format)

    @staticmethod
    def load_json(file_path: Path) -> Optional[Dict[str, Any]]:
        """加载JSON文件"""
        return FileUtils.load_json(file_path)

    @staticmethod
    def load_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
        """加载YAML文件"""
        return FileUtils.load_yaml(file_path)

    @staticmethod
    def load_text(file_path: Path, *, encoding: str = 'utf-8') -> Optional[str]:
        """加载文本文件"""
        return FileUtils.load_text(file_path, encoding=encoding)

    @staticmethod
    def load_python_config(file_path: Path, var_name: str = "settings") -> Optional[Dict[str, Any]]:
        """加载Python配置文件并提取指定变量"""
        return FileUtils.load_python_config(file_path, var_name)

    @staticmethod
    def save_file_content(
        file_path: Path,
        content: Union[str, Dict[str, Any], bytes],
        *,
        encoding: str = 'utf-8',
        ensure_parent_exists: bool = True
    ) -> bool:
        """保存文件内容（自动识别JSON/YAML/文本）"""
        return FileUtils.save_file_content(file_path, content, encoding=encoding, ensure_parent_exists=ensure_parent_exists)

    @staticmethod
    def save_json(file_path: Path, data: Dict[str, Any], *, encoding: str = 'utf-8') -> bool:
        """保存JSON文件"""
        return FileUtils.save_json(file_path, data, encoding=encoding)

    @staticmethod
    def save_yaml(file_path: Path, data: Dict[str, Any], *, encoding: str = 'utf-8') -> bool:
        """保存YAML文件"""
        return FileUtils.save_yaml(file_path, data, encoding=encoding)


class DiscoverNamespace:
    """批量发现命名空间"""

    @staticmethod
    def files(
        base_dir: Path,
        pattern: str = "**/*",
        *,
        exclude_patterns: Optional[List[str]] = None,
        max_depth: int = FileDiscovery.DEFAULT_MAX_DEPTH,
    ) -> List[Path]:
        """批量发现文件"""
        config = FileDiscoveryConfig(
            base_dir=base_dir,
            pattern=pattern,
            exclude_patterns=exclude_patterns or [],
            file_type="file",
            max_depth=max_depth,
        )
        discovery = FileDiscovery(config)
        return discovery.discover()

    @staticmethod
    def directories(
        base_dir: Path,
        pattern: str = "**/*",
        *,
        exclude_patterns: Optional[List[str]] = None,
        max_depth: int = FileDiscovery.DEFAULT_MAX_DEPTH,
    ) -> List[Path]:
        """批量发现目录"""
        config = FileDiscoveryConfig(
            base_dir=base_dir,
            pattern=pattern,
            exclude_patterns=exclude_patterns or [],
            file_type="dir",
            max_depth=max_depth,
        )
        discovery = FileDiscovery(config)
        return discovery.discover()

    @staticmethod
    def files_by_suffix(
        base_dir: Path,
        suffix: str,
        *,
        exclude_patterns: Optional[List[str]] = None,
        max_depth: int = FileDiscovery.DEFAULT_MAX_DEPTH,
    ) -> List[Path]:
        """根据扩展名批量发现文件；``suffix`` 须含点，如 ``.json``。"""
        if not suffix.startswith("."):
            raise ValueError(
                f"files_by_suffix 要求 suffix 以 '.' 开头（如 '.json'），收到 {suffix!r}"
            )
        pattern = f"**/*{suffix}"
        config = FileDiscoveryConfig(
            base_dir=base_dir,
            pattern=pattern,
            exclude_patterns=exclude_patterns or [],
            file_type="file",
            max_depth=max_depth,
        )
        discovery = FileDiscovery(config)
        return discovery.discover()

    @staticmethod
    def subclasses(
        base_class: Type,
        base_module_path: str,
        module_name_pattern: str = "{base_module}.{name}",
        key_extractor: Optional[Callable[[Type], str]] = None,
        class_filter: Optional[Callable[[Type], bool]] = None
    ) -> Dict[str, Type]:
        """发现所有继承 base_class 的子类"""
        config = DiscoveryConfig(
            base_class=base_class,
            module_name_pattern=module_name_pattern,
            key_extractor=key_extractor,
            class_filter=class_filter
        )
        discovery = ClassDiscovery(config)
        result = discovery.discover(base_module_path)
        return result.classes

    @staticmethod
    def objects(
        base_module_path: str,
        object_name: str,
        module_pattern: str = "{base_module}.{name}",
        skip_modules: Optional[set] = None,
    ) -> Dict[str, Any]:
        """发现所有模块中的特定对象"""
        return ModuleDiscovery.discover_objects(
            base_module_path,
            object_name,
            module_pattern,
            skip_modules,
        )


class ClassDiscoveryNamespace:
    """类发现命名空间（高级用法）"""

    @staticmethod
    def create_config(
        base_class: Type,
        module_name_pattern: str,
        key_extractor: Optional[Callable[[Type], str]] = None,
        class_filter: Optional[Callable[[Type], bool]] = None,
        attribute_extractors: Optional[Dict[str, Callable[[Type], Any]]] = None,
        skip_modules: Optional[set] = None,
        skip_classes: Optional[set] = None,
    ) -> DiscoveryConfig:
        """创建发现配置"""
        return DiscoveryConfig(
            base_class=base_class,
            module_name_pattern=module_name_pattern,
            key_extractor=key_extractor,
            class_filter=class_filter,
            attribute_extractors=attribute_extractors or {},
            skip_modules=(
                set(skip_modules)
                if skip_modules is not None
                else set(DiscoveryConfig.DEFAULT_SKIP_MODULES)
            ),
            skip_classes=set(skip_classes) if skip_classes is not None else set(),
        )

    @staticmethod
    def create(config: DiscoveryConfig) -> ClassDiscovery:
        """创建类发现器实例"""
        return ClassDiscovery(config)

    @staticmethod
    def discover_class_by_path(
        class_path: str,
        base_class: Optional[Type] = None,
    ) -> Optional[Type]:
        """通过完整路径发现单个类"""
        return ClassDiscovery.discover_class_by_path(class_path, base_class)