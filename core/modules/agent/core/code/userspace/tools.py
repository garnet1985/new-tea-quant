"""Userspace agent tools：仅新增；与内置同名则忽略。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.modules.agent.contracts import ToolSpec

logger = logging.getLogger(__name__)

Handler = Callable[[Dict[str, Any]], Dict[str, Any]]


def list_userspace_tool_specs(
    *,
    builtin_names: frozenset[str],
) -> List[ToolSpec]:
    specs: List[ToolSpec] = []
    for spec, _handler in _discover(builtin_names):
        specs.append(spec)
    return specs


def get_userspace_tool_handler(
    name: str,
    *,
    builtin_names: frozenset[str],
) -> Optional[Handler]:
    key = str(name or "").strip()
    if not key or key in builtin_names:
        return None
    for spec, handler in _discover(builtin_names):
        if spec.name == key:
            return handler
    return None


def _discover(
    builtin_names: frozenset[str],
) -> List[Tuple[ToolSpec, Handler]]:
    root = ProjectContext.path.get_agent_tools_directory()
    if not root.is_dir():
        return []
    tool_files = Discovery.discover.files(
        root,
        "*/tool.py",
        exclude_patterns=["*/__pycache__/*"],
        max_depth=2,
    )
    found: List[Tuple[ToolSpec, Handler]] = []
    seen: set[str] = set()
    for tool_py in sorted(tool_files):
        folder = tool_py.parent
        if not ProjectContext.path.is_safe_extension_id(folder.name):
            continue
        loaded = _load_tool_file(tool_py, folder_name=folder.name)
        if loaded is None:
            continue
        spec, handler = loaded
        if spec.name in builtin_names:
            logger.warning(
                "userspace tool %s ignored: name conflicts with builtin",
                spec.name,
            )
            continue
        if spec.name in seen:
            logger.warning("userspace tool %s ignored: duplicate", spec.name)
            continue
        seen.add(spec.name)
        found.append((spec, handler))
    return found


def _load_tool_file(
    path: Path,
    *,
    folder_name: str,
) -> Optional[Tuple[ToolSpec, Handler]]:
    namespace = Discovery.file.load_python_namespace(
        path,
        module_name=f"userspace_agent_tool_{folder_name}",
    )
    if not namespace:
        return None
    raw = namespace.get("TOOL")
    run = namespace.get("run")
    if not isinstance(raw, dict):
        logger.warning("userspace tool %s missing TOOL dict", path)
        return None
    if not callable(run):
        logger.warning("userspace tool %s missing run()", path)
        return None
    name = str(raw.get("name") or folder_name).strip()
    if not ProjectContext.path.is_safe_extension_id(name):
        logger.warning("userspace tool unsafe name %r in %s", name, path)
        return None
    description = str(raw.get("description") or "").strip() or name
    parameters = raw.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    spec = ToolSpec(
        name=name,
        description=description,
        parameters=parameters,
        implemented=True,
    )

    def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = run(arguments if isinstance(arguments, dict) else {})
        if isinstance(result, dict):
            return result
        return {"ok": False, "error": "userspace tool 必须返回对象"}

    return spec, handler
