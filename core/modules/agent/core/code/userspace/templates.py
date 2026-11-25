"""Userspace present templates：可覆盖内置正文；新 scenario 用 frontmatter match。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.modules.agent.core.code.conf.conf import PRESENTATION_SCENARIOS
from core.modules.agent.core.code.executor.shared.prompt_loader import load_prompt
from core.modules.agent.core.code.userspace.frontmatter import split_frontmatter

logger = logging.getLogger(__name__)


def userspace_template_path(scenario: str) -> Optional[Path]:
    key = str(scenario or "").strip()
    if not ProjectContext.path.is_safe_extension_id(key):
        return None
    path = ProjectContext.path.get_agent_templates_directory() / f"{key}.md"
    return path if path.is_file() else None


def merged_scenario_keys() -> List[str]:
    keys = set(PRESENTATION_SCENARIOS)
    root = ProjectContext.path.get_agent_templates_directory()
    if not root.is_dir():
        return sorted(keys)
    for path in Discovery.discover.files(
        root,
        "*.md",
        exclude_patterns=["*/__pycache__/*"],
        max_depth=1,
    ):
        if ProjectContext.path.is_safe_extension_id(path.stem):
            keys.add(path.stem)
    return sorted(keys)


def load_merged_template(scenario: str) -> str:
    """用户同名文件优先；否则读内置 content/templates。"""
    key = str(scenario or "").strip()
    user_path = userspace_template_path(key)
    if user_path is not None:
        raw = Discovery.file.load_text(user_path)
        if raw and str(raw).strip():
            _meta, body = split_frontmatter(str(raw))
            return body.rstrip()
    builtin = PRESENTATION_SCENARIOS.get(key)
    if not builtin:
        raise KeyError(f"unknown presentation scenario: {key}")
    return load_prompt(builtin).rstrip()


def list_userspace_template_matches() -> List[Tuple[str, Dict[str, Any]]]:
    """仅「非内置 scenario」且带 match 的模版，供 present 解析。"""
    root = ProjectContext.path.get_agent_templates_directory()
    if not root.is_dir():
        return []
    out: List[Tuple[str, Dict[str, Any]]] = []
    for path in sorted(
        Discovery.discover.files(
            root,
            "*.md",
            exclude_patterns=["*/__pycache__/*"],
            max_depth=1,
        )
    ):
        key = path.stem
        if not ProjectContext.path.is_safe_extension_id(key):
            continue
        if key in PRESENTATION_SCENARIOS:
            continue
        raw = Discovery.file.load_text(path)
        if raw is None:
            continue
        meta, _body = split_frontmatter(str(raw))
        match = meta.get("match") if isinstance(meta, dict) else None
        if not isinstance(match, dict):
            continue
        cleaned = _normalize_match(match)
        if cleaned:
            out.append((key, cleaned))
    return out


def match_userspace_scenario(
    user_text: str,
    tools_seen: Sequence[Mapping[str, Any]] | None,
) -> Optional[str]:
    text = str(user_text or "")
    for scenario, match in list_userspace_template_matches():
        if _match_rule(match, text, tools_seen):
            return scenario
    return None


def _normalize_match(raw: Mapping[str, Any]) -> Dict[str, Any]:
    tool = str(raw.get("tool") or "").strip()
    if not tool:
        return {}
    out: Dict[str, Any] = {"tool": tool}
    layer = str(raw.get("layer") or "").strip()
    if layer:
        out["layer"] = layer
    user_re = str(raw.get("user_re") or "").strip()
    if user_re:
        try:
            out["user_re"] = re.compile(user_re)
        except re.error as exc:
            logger.warning("invalid userspace template user_re %r: %s", user_re, exc)
            return {}
    return out


def _match_rule(
    match: Mapping[str, Any],
    user_text: str,
    tools_seen: Sequence[Mapping[str, Any]] | None,
) -> bool:
    tool = str(match.get("tool") or "").strip()
    layer = str(match.get("layer") or "").strip()
    if not _saw_ok_tool(tools_seen, tool, layer=layer):
        return False
    pattern = match.get("user_re")
    if pattern is None:
        return True
    return bool(pattern.search(user_text))


def _saw_ok_tool(
    tools_seen: Sequence[Mapping[str, Any]] | None,
    tool: str,
    *,
    layer: str = "",
) -> bool:
    want = str(tool or "").strip()
    want_layer = str(layer or "").strip()
    for row in tools_seen or ():
        if not isinstance(row, Mapping):
            continue
        if str(row.get("tool") or "").strip() != want:
            continue
        if not row.get("ok"):
            continue
        if want_layer and str(row.get("layer") or "").strip() != want_layer:
            continue
        return True
    return False
