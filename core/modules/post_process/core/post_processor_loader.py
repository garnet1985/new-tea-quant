"""加载 / 枚举 userspace PostProcessor 声明。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.modules.post_process.core.post_processor_types import (
    AdapterBinding,
    PostProcessorDefinition,
)

_DEF_FILENAMES = (
    "post_processor.json",
)


class PostProcessorLoader:
    @staticmethod
    def list_keys() -> List[str]:
        root = ProjectContext.path.get_post_processors_directory()
        if not root.is_dir():
            return []
        keys: List[str] = []
        for child in sorted(root.iterdir()):
            if child.name.startswith(("_", ".")):
                continue
            if child.is_file() and child.suffix.lower() == ".json":
                keys.append(child.stem)
                continue
            if child.is_dir():
                for fname in _DEF_FILENAMES:
                    if (child / fname).is_file():
                        keys.append(child.name)
                        break
        return keys

    @staticmethod
    def resolve_path(key: str) -> Optional[Path]:
        name = str(key or "").strip()
        if not name:
            return None
        root = ProjectContext.path.get_post_processors_directory()
        flat = root / f"{name}.json"
        if flat.is_file():
            return flat
        for fname in _DEF_FILENAMES:
            path = root / name / fname
            if path.is_file():
                return path
        return None

    @staticmethod
    def load(key: str) -> Optional[PostProcessorDefinition]:
        path = PostProcessorLoader.resolve_path(key)
        if path is None:
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return None
        if not isinstance(raw, dict):
            return None
        return PostProcessorLoader._from_dict(str(key).strip(), raw)

    @staticmethod
    def _from_dict(key: str, raw: Dict[str, Any]) -> PostProcessorDefinition:
        declared_key = str(raw.get("key") or key).strip() or key
        name = str(raw.get("name") or "").strip()
        raw_enabled = raw.get("is_enabled", True)
        if isinstance(raw_enabled, bool):
            is_enabled = raw_enabled
        elif isinstance(raw_enabled, (int, float)):
            is_enabled = bool(raw_enabled)
        else:
            text = str(raw_enabled or "").strip().lower()
            is_enabled = text not in ("0", "false", "no", "off", "")
        on_error = str(raw.get("on_error") or "continue").strip().lower()
        if on_error not in ("continue", "stop"):
            on_error = "continue"
        on_empty = str(raw.get("on_empty") or "run").strip().lower()
        if on_empty not in ("run", "skip"):
            on_empty = "run"

        adapters_raw = raw.get("adapters")
        if adapters_raw is None:
            adapters_raw = raw.get("components")
        adapters: Dict[str, AdapterBinding] = {}
        if isinstance(adapters_raw, dict):
            for adapter_name, body in adapters_raw.items():
                aname = str(adapter_name or "").strip()
                if not aname:
                    continue
                cfg: Dict[str, Any] = {}
                depends: List[str] = []
                if isinstance(body, dict):
                    raw_cfg = body.get("config")
                    if isinstance(raw_cfg, dict):
                        cfg = dict(raw_cfg)
                    raw_deps = body.get("depends_on")
                    if isinstance(raw_deps, str) and raw_deps.strip():
                        depends = [raw_deps.strip()]
                    elif isinstance(raw_deps, list):
                        depends = [str(x).strip() for x in raw_deps if str(x).strip()]
                adapters[aname] = AdapterBinding(
                    name=aname,
                    config=cfg,
                    depends_on=depends,
                )

        return PostProcessorDefinition(
            key=declared_key,
            name=name,
            is_enabled=is_enabled,
            on_error=on_error,
            on_empty=on_empty,
            adapters=adapters,
        )

    @staticmethod
    def list_enabled_keys() -> List[str]:
        """``is_enabled: true`` 的 post_processor key（稳定排序）。"""
        out: List[str] = []
        for key in PostProcessorLoader.list_keys():
            definition = PostProcessorLoader.load(key)
            if definition is not None and definition.is_enabled:
                out.append(key)
        return out


__all__ = ["PostProcessorLoader"]
