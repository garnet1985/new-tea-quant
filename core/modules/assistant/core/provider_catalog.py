"""扫描并解析 userspace Assistant 供应商目录（实施层）。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.modules.assistant.contracts import ProviderInfo

_CONFIG_FILE = "config.py"
_CONFIG_VAR = "PROVIDER"
_API_KEY_FILE = "api_key.txt"


class ProviderCatalog:
    """把供应商目录变成 ``ProviderInfo``；不做调用编排。"""

    @staticmethod
    def is_safe_provider_id(provider_id: str) -> bool:
        name = str(provider_id or "").strip()
        if not name or name in {".", ".."}:
            return False
        if "/" in name or "\\" in name:
            return False
        return not name.startswith(".")

    @staticmethod
    def list_providers() -> List[ProviderInfo]:
        """发现 `userspace/extensions/assistant/providers/*` 下的合法供应商。"""
        providers_root = ProjectContext.path.get_assistant_providers_directory()
        config_files = Discovery.discover.files(
            providers_root,
            "*/config.py",
            exclude_patterns=["*/__pycache__/*"],
            max_depth=2,
        )
        found: List[ProviderInfo] = []
        seen: set[str] = set()
        for config_path in sorted(config_files):
            info = ProviderCatalog.parse_provider(config_path.parent)
            if info is None or info.provider_id in seen:
                continue
            seen.add(info.provider_id)
            found.append(info)
        return found

    @staticmethod
    def get_provider(provider_id: str) -> Optional[ProviderInfo]:
        """按文件夹名取一个供应商；不存在或配置不合法时返回 ``None``。"""
        name = str(provider_id or "").strip()
        if not ProviderCatalog.is_safe_provider_id(name):
            return None
        for item in ProviderCatalog.list_providers():
            if item.provider_id == name:
                return item
        return None

    @staticmethod
    def parse_provider(directory: Path) -> Optional[ProviderInfo]:
        """解析单个供应商目录；缺字段或非法目录名时返回 ``None``。"""
        provider_id = directory.name
        if not ProviderCatalog.is_safe_provider_id(provider_id):
            return None

        config_path = directory / _CONFIG_FILE
        raw = Discovery.file.load_python_config(config_path, var_name=_CONFIG_VAR)
        if not isinstance(raw, dict):
            return None

        base_url = str(raw.get("base_url") or "").strip()
        model = str(raw.get("model") or "").strip()
        if not base_url or not model:
            return None

        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            enabled = bool(enabled)

        return ProviderInfo(
            provider_id=provider_id,
            directory=directory,
            base_url=base_url.rstrip("/"),
            model=model,
            enabled=enabled,
            has_api_key=ProviderCatalog._has_api_key(directory),
        )

    @staticmethod
    def load_api_key(directory: Path) -> Optional[str]:
        """读取 ``api_key.txt``；缺失或空白返回 ``None``。"""
        key_path = directory / _API_KEY_FILE
        if not key_path.is_file():
            return None
        text = Discovery.file.load_text(key_path)
        key = str(text or "").strip()
        return key or None

    @staticmethod
    def _has_api_key(directory: Path) -> bool:
        return ProviderCatalog.load_api_key(directory) is not None
