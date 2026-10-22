"""动态加载 userspace PostProcess component（内部）。"""

from __future__ import annotations

import importlib
import inspect
from typing import List, Optional, Type, TYPE_CHECKING

from core.infra.project_context import ProjectContext

if TYPE_CHECKING:
    from core.modules.post_process.core.base_adapter import BaseAdapter


class AdapterLoader:
    """按约定路径加载 ``BaseAdapter`` 子类。"""

    @staticmethod
    def module_path(adapter_name: str) -> str:
        return f"userspace.extensions.post_process.adapters.{adapter_name}.adapter"

    @staticmethod
    def settings_module_path(adapter_name: str) -> str:
        return f"userspace.extensions.post_process.adapters.{adapter_name}.settings"

    @staticmethod
    def find_adapter_class(module: object) -> Optional[Type["BaseAdapter"]]:
        from core.modules.post_process.core.base_adapter import BaseAdapter

        for _, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseAdapter)
                and obj is not BaseAdapter
            ):
                return obj
        return None

    @staticmethod
    def load_class(adapter_name: str) -> Optional[Type["BaseAdapter"]]:
        name = str(adapter_name or "").strip()
        if not name:
            return None
        try:
            module = importlib.import_module(AdapterLoader.module_path(name))
        except Exception:
            return None
        return AdapterLoader.find_adapter_class(module)

    @staticmethod
    def list_names() -> List[str]:
        root = ProjectContext.path.get_adapters_directory()
        if not root.is_dir():
            return []
        names: List[str] = []
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(("_", ".")):
                continue
            if (child / "adapter.py").is_file():
                names.append(child.name)
        return names

    @staticmethod
    def load_default_config(adapter_name: str) -> dict:
        name = str(adapter_name or "").strip()
        if not name:
            return {}
        try:
            module = importlib.import_module(AdapterLoader.settings_module_path(name))
        except ModuleNotFoundError:
            return {}
        except Exception:
            return {}
        if hasattr(module, "settings") and isinstance(getattr(module, "settings"), dict):
            return dict(getattr(module, "settings"))
        if hasattr(module, "config") and isinstance(getattr(module, "config"), dict):
            return dict(getattr(module, "config"))
        return {}


__all__ = ["AdapterLoader"]
