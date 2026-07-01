"""Strategy discovery 服务（ProjectContext + Discovery）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext

from .path_rules import StrategyPathRules
from .worker_loader import StrategyWorkerLoader

logger = logging.getLogger(__name__)


class DiscoveryService:
    """策略发现：扫描 strategies 目录并加载 settings / hooks。"""

    @staticmethod
    def discover_strategies(
        strategies_root: Optional[Path] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """发现全部策略，返回 strategy_name → info dict。"""
        if strategies_root is None:
            strategies_root = ProjectContext.path.get_strategies_root()

        if not strategies_root.exists():
            logger.warning("Strategy directory does not exist: %s", strategies_root)
            return {}

        discovered: Dict[str, Dict[str, Any]] = {}
        for strategy_folder in DiscoveryService._iter_strategy_directories(strategies_root):
            strategy_info = DiscoveryService.load_strategy_info(
                strategy_folder,
                strategies_root=strategies_root,
            )
            if strategy_info:
                discovered[strategy_info["name"]] = strategy_info
                logger.info("Discovered strategy: %s", strategy_info["name"])
        return discovered

    @staticmethod
    def _iter_strategy_directories(strategies_root: Path) -> List[Path]:
        """遍历含 settings.py 与 strategy.py 的策略目录。"""
        candidates: List[Path] = []
        for dirpath, dirnames, _filenames in os.walk(strategies_root):
            dirnames[:] = [d for d in dirnames if not str(d).startswith("_")]
            folder = Path(dirpath)
            if (folder / "settings.py").is_file() and (folder / "strategy.py").is_file():
                candidates.append(folder)
        candidates.sort(
            key=lambda p: StrategyPathRules.relative_strategy_key(p, strategies_root)
        )
        return candidates

    @staticmethod
    def load_strategy_info(
        strategy_folder: Path,
        *,
        strategies_root: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """加载单个策略 info dict；失败返回 None。"""
        if strategies_root is None:
            strategies_root = ProjectContext.path.get_strategies_root()

        try:
            strategy_key = StrategyPathRules.relative_strategy_key(
                strategy_folder,
                strategies_root,
            )
        except ValueError:
            logger.warning("Strategy directory not under strategies_root: %s", strategy_folder)
            return None

        if not StrategyPathRules.is_machine_readable_path(strategy_key):
            logger.warning(
                "Strategy path contains non machine-readable segment, skipped: %s",
                strategy_key,
            )
            return None

        settings_file = strategy_folder / "settings.py"
        if not settings_file.is_file():
            logger.warning("Strategy %s missing settings.py", strategy_key)
            return None

        try:
            settings_dict = Discovery.file.load_python_config(settings_file, var_name="settings")
            if not isinstance(settings_dict, dict):
                logger.error("Strategy %s settings is not a dict", strategy_key)
                return None
        except Exception as exc:
            logger.error("Failed to load settings: %s, error=%s", strategy_key, exc)
            return None

        validation_result = DiscoveryService._validate_settings_simple(settings_dict)
        if not validation_result["is_valid"]:
            logger.error(
                "Strategy %s settings validation failed: %s",
                strategy_key,
                validation_result["errors"],
            )
            return None

        hooks_result = StrategyWorkerLoader.load_hooks_class(strategy_folder, strategy_key)
        if not hooks_result:
            logger.warning("Strategy %s cannot load hooks class", strategy_key)
            return None

        worker_module_path, worker_class_name, worker_file_path, worker_class = hooks_result

        return {
            "name": strategy_key,
            "folder": str(strategy_folder.resolve()),
            "is_enabled": bool(settings_dict.get("is_enabled", False)),
            "display_name": str(settings_dict.get("meta", {}).get("display_name", "")).strip(),
            "settings": settings_dict,
            "worker_module_path": worker_module_path,
            "worker_class_name": worker_class_name,
            "worker_file_path": str(worker_file_path),
            "worker_class": worker_class,
        }

    @staticmethod
    def _validate_settings_simple(settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        """简化版 settings 校验。"""
        errors: List[str] = []

        if "is_enabled" not in settings_dict:
            errors.append("Missing is_enabled field")

        core = settings_dict.get("core")
        if core is not None and not isinstance(core, dict):
            errors.append("core must be a dict if present")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
        }


__all__ = ["DiscoveryService"]
