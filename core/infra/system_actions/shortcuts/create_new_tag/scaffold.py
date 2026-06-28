#!/usr/bin/env python3
"""从模板新建 Tag 场景目录。"""

from __future__ import annotations

from pathlib import Path

from core.infra.project_context import ProjectContext

from core.infra.system_actions.shortcuts._shared import (
    ScaffoldResult,
    copy_template,
    enable_in_settings,
    resolve_dest,
)
from core.modules.tag.services.discovery.path_rules import is_machine_readable_tag_path

TAG_TEMPLATE_REL = Path("_template") / "empty_scenario"


def scaffold_tag(raw_path: str) -> ScaffoldResult:
    """复制 ``extensions/tags/_template/empty_scenario/`` 到 ``tags/<raw_path>/``。"""
    root = ProjectContext.path.get_tags_root()
    dest, key = resolve_dest(
        root=root,
        raw_path=raw_path,
        path_validator=is_machine_readable_tag_path,
    )
    template = (root / TAG_TEMPLATE_REL).resolve()
    copy_template(template=template, dest=dest)
    enable_in_settings(dest / "settings.py")
    return ScaffoldResult(kind="tag", key=key, dest=dest)


__all__ = ["scaffold_tag"]
