"""create_tag：检查名字与目录，再复制空模板。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

from core.infra.project_context import ProjectContext
from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder


def create_tag(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """新建标签场景。存在、名字、模板检查都在这里完成。"""
    parsed = parse_tag_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located
    dest, relative = located
    if dest.exists():
        return {"ok": False, "error": f"目标已存在: {relative}"}

    template = (
        ProjectContext.path.get_tags_root() / "_template" / "empty_scenario"
    )
    if not template.is_dir():
        return {
            "ok": False,
            "error": "标签模板不存在: extensions/tags/_template/empty_scenario",
        }

    from core.modules.cli.user.scripts.create_from_template.create_from_template import (
        CreateFromTemplate,
    )

    try:
        CreateFromTemplate.create_tag(parsed)
    except CreateFromTemplate.Error as exc:
        return {"ok": False, "error": _short_create_error(str(exc), relative)}

    settings = dest / "settings.py"
    tag_py = dest / "tag.py"
    if not settings.is_file() or not tag_py.is_file():
        return {"ok": False, "error": f"模板复制后文件不齐: {relative}"}
    meta_key = Path(parsed).name
    try:
        _align_meta_key(settings, meta_key)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "key": parsed,
        "path": relative,
        "files": ["tag.py", "settings.py"],
        "note": f"仍是空模板，meta.key 已写成 {meta_key}",
    }


def _align_meta_key(settings_file: Path, key: str) -> None:
    """模板里的 meta.key 是 empty_tag，这里改成叶名（与 demo 约定一致）。"""
    text = settings_file.read_text(encoding="utf-8")
    escaped = key.replace("\\", "\\\\").replace('"', '\\"')
    new_text, count = re.subn(
        r'("key"\s*:\s*")[^"]*(")',
        rf"\g<1>{escaped}\g<2>",
        text,
        count=1,
    )
    if count != 1:
        raise ValueError(f"无法写入 meta.key：{key}")
    settings_file.write_text(new_text, encoding="utf-8")


def _short_create_error(message: str, relative: str) -> str:
    text = message.strip()
    if text.startswith("目标已存在"):
        return f"目标已存在: {relative}"
    if "模板目录不存在" in text:
        return "标签模板不存在: extensions/tags/_template/empty_scenario"
    return text
