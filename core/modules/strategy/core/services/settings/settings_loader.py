# """Strategy settings loader (simplified version)."""

# from __future__ import annotations

# import importlib.util
# import logging
# from pathlib import Path
# from typing import Any, Dict, Optional

# logger = logging.getLogger(__name__)


# class SettingsLoader:
#     """Strategy settings loader (simplified version).

#     TODO: 后续完善完整的settings加载逻辑（包括default values应用、验证等）。
#     """

#     @staticmethod
#     def load_settings_dict_from_folder(
#         strategy_folder: Path,
#         *,
#         strategy_key: Optional[str] = None,
#     ) -> Dict[str, Any]:
#         """Load settings dict from strategy_folder/settings.py.

#         Args:
#             strategy_folder: strategy folder path
#             strategy_key: strategy key (optional, default to folder.name)

#         Returns:
#             settings dict

#         Raises:
#             FileNotFoundError: settings.py not found
#             ValueError: settings.py must define a dict named settings
#         """
#         folder = Path(strategy_folder)
#         settings_file = folder / "settings.py"
#         if not settings_file.is_file():
#             raise FileNotFoundError(f"settings.py not found: {settings_file}")

#         key = str(strategy_key or folder.name).strip() or folder.name
#         module_name = f"strategy_{key}_settings"

#         spec = importlib.util.spec_from_file_location(module_name, settings_file)
#         if spec is None or spec.loader is None:
#             raise ValueError(f"cannot load settings module: {settings_file}")

#         module = importlib.util.module_from_spec(spec)
#         spec.loader.exec_module(module)

#         settings = getattr(module, "settings", None)
#         if not isinstance(settings, dict):
#             raise ValueError(f"settings.py must define a dict named settings: {settings_file}")

#         logger.info("Loaded settings from %s", settings_file)
#         return dict(settings)

#     @staticmethod
#     def load_and_merge_settings(
#         strategy_folder: Path,
#         *,
#         strategy_key: Optional[str] = None,
#         defaults: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         """Load settings dict and merge with defaults.

#         Args:
#             strategy_folder: strategy folder path
#             strategy_key: strategy key (optional)
#             defaults: default values (optional)

#         Returns:
#             merged settings dict
#         """
#         settings = SettingsLoader.load_settings_dict_from_folder(
#             strategy_folder,
#             strategy_key=strategy_key,
#         )

#         # Merge with defaults (简化版本)
#         # TODO: 后续完善完整的merge逻辑（包括deep merge等）
#         if defaults:
#             merged = dict(defaults)
#             merged.update(settings)
#             return merged

#         return settings


# __all__ = ['SettingsLoader']