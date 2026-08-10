#!/usr/bin/env python3
"""从模板新建 Tag 场景目录。"""

from __future__ import annotations

from pathlib import Path

from core.infra.project_context import ProjectContext
from core.infra.system_actions.contracts import ScaffoldResult
from core.infra.system_actions.core.shortcuts.shared import ScaffoldHelpers
from core.modules.tag import Tag

TAG_TEMPLATE_REL = Path("_template") / "empty_scenario"


class TagScaffold:
    """Tag 脚手架（内部实现；公开入口 ``SystemActions.scaffold.create_tag``）。"""

    @staticmethod
    def create(raw_path: str) -> ScaffoldResult:
        """复制 ``extensions/tags/_template/empty_scenario/`` 到 ``tags/<raw_path>/``。"""
        root = ProjectContext.path.get_tags_root()
        dest, key = ScaffoldHelpers.resolve_dest(
            root=root,
            raw_path=raw_path,
            path_validator=Tag.is_valid_path,
        )
        template = (root / TAG_TEMPLATE_REL).resolve()
        ScaffoldHelpers.copy_template(template=template, dest=dest)
        ScaffoldHelpers.enable_in_settings(dest / "settings.py")
        ScaffoldHelpers.inject_meta_key_in_settings_file(dest / "settings.py", key)
        return ScaffoldResult(kind="tag", key=key, dest=dest)


__all__ = ["TagScaffold"]
