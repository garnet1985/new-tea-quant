"""File Discovery - 批量文件发现工具"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import logging
import fnmatch

logger = logging.getLogger(__name__)

DEFAULT_MAX_DEPTH = 10


@dataclass
class FileDiscoveryConfig:
    """文件发现配置"""

    DEFAULT_MAX_DEPTH = DEFAULT_MAX_DEPTH

    base_dir: Path
    pattern: str = "**/*"
    exclude_patterns: List[str] = field(default_factory=list)
    file_type: Optional[str] = None  # "file" | "dir" | None
    max_depth: int = DEFAULT_MAX_DEPTH
    follow_symlinks: bool = False


class FileDiscovery:
    """批量文件发现工具"""

    DEFAULT_MAX_DEPTH = DEFAULT_MAX_DEPTH

    def __init__(self, config: FileDiscoveryConfig):
        self.config = config
        self._cache: Dict[str, List[Path]] = {}

    def _cache_key(self) -> str:
        excludes = ",".join(sorted(self.config.exclude_patterns))
        return (
            f"{self.config.base_dir.resolve()}|"
            f"{self.config.pattern}|"
            f"{self.config.file_type}|"
            f"{self.config.max_depth}|"
            f"{self.config.follow_symlinks}|"
            f"{excludes}"
        )

    def discover(self, *, use_cache: bool = True) -> List[Path]:
        """批量发现文件/目录"""
        cache_key = self._cache_key()

        if use_cache and cache_key in self._cache:
            logger.debug("使用缓存发现结果: %s", cache_key)
            return self._cache[cache_key]

        if not self.config.base_dir.exists():
            logger.debug("基础目录不存在: %s", self.config.base_dir)
            return []

        results: List[Path] = []

        try:
            matched_paths = self.config.base_dir.glob(self.config.pattern)

            for path in matched_paths:
                depth = len(path.relative_to(self.config.base_dir).parts)
                if depth > self.config.max_depth:
                    continue

                if self.config.file_type == "file" and not path.is_file():
                    continue
                if self.config.file_type == "dir" and not path.is_dir():
                    continue

                if self._should_exclude(path):
                    continue

                if path.is_symlink() and not self.config.follow_symlinks:
                    continue

                results.append(path)

            logger.debug("发现 %s 个文件/目录", len(results))

            if use_cache:
                self._cache[cache_key] = results

        except Exception as e:
            logger.error("发现文件失败: %s", e)
            return []

        return results

    def discover_with_metadata(
        self, *, use_cache: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """批量发现文件并提取元数据"""
        paths = self.discover(use_cache=use_cache)
        metadata: Dict[str, Dict[str, Any]] = {}

        for path in paths:
            try:
                stat = path.stat()
                metadata[str(path)] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "type": "file" if path.is_file() else "dir",
                    "extension": path.suffix if path.is_file() else None,
                }
            except Exception as e:
                logger.warning("获取文件元数据失败: %s, %s", path, e)

        return metadata

    def _should_exclude(self, path: Path) -> bool:
        path_str = str(path)
        relative_path = str(path.relative_to(self.config.base_dir))

        for exclude_pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(path_str, exclude_pattern):
                return True
            if fnmatch.fnmatch(relative_path, exclude_pattern):
                return True

        return False

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        logger.debug("清除所有缓存")
