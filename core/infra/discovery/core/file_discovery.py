"""File Discovery - 批量文件发现工具"""
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
import logging
import fnmatch


logger = logging.getLogger(__name__)


@dataclass
class FileDiscoveryConfig:
    """文件发现配置"""
    base_dir: Path
    pattern: str = "**/*"
    exclude_patterns: List[str] = field(default_factory=list)
    file_type: Optional[str] = None  # "file" | "dir" | None
    max_depth: int = 10
    follow_symlinks: bool = False


class FileDiscovery:
    """批量文件发现工具"""

    def __init__(self, config: FileDiscoveryConfig):
        self.config = config
        self._cache: Dict[str, List[Path]] = {}

    def discover(self, *, use_cache: bool = True) -> List[Path]:
        """批量发现文件/目录"""
        cache_key = f"{self.config.base_dir}:{self.config.pattern}"

        # 检查缓存
        if use_cache and cache_key in self._cache:
            logger.debug(f"使用缓存发现结果: {cache_key}")
            return self._cache[cache_key]

        if not self.config.base_dir.exists():
            logger.debug(f"基础目录不存在: {self.config.base_dir}")
            return []

        results = []

        try:
            # 使用 glob 模式搜索
            matched_paths = self.config.base_dir.glob(self.config.pattern)

            for path in matched_paths:
                # 检查深度限制
                depth = len(path.relative_to(self.config.base_dir).parts)
                if depth > self.config.max_depth:
                    continue

                # 检查文件类型
                if self.config.file_type == "file" and not path.is_file():
                    continue
                elif self.config.file_type == "dir" and not path.is_dir():
                    continue

                # 检查排除模式
                if self._should_exclude(path):
                    continue

                # 检查符号链接
                if path.is_symlink() and not self.config.follow_symlinks:
                    continue

                results.append(path)

            logger.debug(f"发现 {len(results)} 个文件/目录")

            # 缓存结果
            if use_cache:
                self._cache[cache_key] = results

        except Exception as e:
            logger.error(f"发现文件失败: {e}")
            return []

        return results

    def discover_with_metadata(self, *, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """批量发现文件并提取元数据"""
        paths = self.discover(use_cache=use_cache)
        metadata = {}

        for path in paths:
            try:
                stat = path.stat()
                metadata[str(path)] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "type": "file" if path.is_file() else "dir",
                    "extension": path.suffix if path.is_file() else None
                }
            except Exception as e:
                logger.warning(f"获取文件元数据失败: {path}, {e}")

        return metadata

    def _should_exclude(self, path: Path) -> bool:
        """检查路径是否应该被排除"""
        path_str = str(path)
        relative_path = str(path.relative_to(self.config.base_dir))

        for exclude_pattern in self.config.exclude_patterns:
            # 使用 fnmatch 匹配
            if fnmatch.fnmatch(path_str, exclude_pattern):
                return True
            if fnmatch.fnmatch(relative_path, exclude_pattern):
                return True

        return False

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        logger.debug("清除所有缓存")


# ========== 便捷函数 ==========

def discover_files(
    base_dir: Path,
    pattern: str = "**/*",
    *,
    exclude_patterns: Optional[List[str]] = None,
    max_depth: int = 10
) -> List[Path]:
    """便捷函数：批量发现文件"""
    config = FileDiscoveryConfig(
        base_dir=base_dir,
        pattern=pattern,
        exclude_patterns=exclude_patterns or [],
        file_type="file",
        max_depth=max_depth
    )
    discovery = FileDiscovery(config)
    return discovery.discover()


def discover_directories(
    base_dir: Path,
    pattern: str = "**/*",
    *,
    exclude_patterns: Optional[List[str]] = None,
    max_depth: int = 10
) -> List[Path]:
    """便捷函数：批量发现目录"""
    config = FileDiscoveryConfig(
        base_dir=base_dir,
        pattern=pattern,
        exclude_patterns=exclude_patterns or [],
        file_type="dir",
        max_depth=max_depth
    )
    discovery = FileDiscovery(config)
    return discovery.discover()


def discover_files_by_suffix(
    base_dir: Path,
    suffix: str,
    *,
    exclude_patterns: Optional[List[str]] = None,
    max_depth: int = 10
) -> List[Path]:
    """便捷函数：根据扩展名批量发现文件"""
    pattern = f"**/*{suffix}"
    return discover_files(
        base_dir,
        pattern,
        exclude_patterns=exclude_patterns,
        max_depth=max_depth
    )