"""validate_tag：经 Tag Facade 加载 hooks 与 settings，不启动计算。"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List

from core.infra.discovery import Discovery
from core.modules.tag import Tag
from core.modules.tag.contracts import TagHooks
from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder


def validate_tag(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """加载已写好的标签。失败时返回错误列表，不启动打标。"""
    parsed = parse_tag_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, relative = located
    tag_file = folder / "tag.py"
    settings_file = folder / "settings.py"
    if not tag_file.is_file() or not settings_file.is_file():
        return {
            "ok": False,
            "key": parsed,
            "errors": [f"标签文件不齐: {relative}。需要 tag.py 和 settings.py"],
        }

    errors: List[str] = []
    for label, path in (("tag.py", tag_file), ("settings.py", settings_file)):
        syntax = _syntax_error(path, label)
        if syntax:
            errors.append(syntax)
    if errors:
        return {"ok": False, "key": parsed, "errors": errors}

    settings = _load_settings(settings_file)
    if isinstance(settings, dict):
        meta = settings.get("meta")
        meta_key = ""
        if isinstance(meta, dict):
            meta_key = str(meta.get("key") or "").strip()
        if not meta_key:
            errors.append("settings 缺少 meta.key")
        elif not _meta_key_aligned(meta_key, parsed, folder):
            leaf = Path(str(parsed).replace("\\", "/")).name
            errors.append(
                f"meta.key={meta_key!r} 无法标识本标签"
                f"（请求 {parsed}，目录叶名 {leaf}）。"
                f"meta.key 应等于目录名/叶名，或经发现解析到同一文件夹"
            )
        if settings.get("is_enabled") is not True:
            errors.append("is_enabled 必须为 True，否则不能打标")
        defs = settings.get("tag_definitions")
        if not isinstance(defs, list) or not defs:
            errors.append("settings 须含非空 tag_definitions 列表")
    else:
        errors.append(_scrub(f"无法加载settings.py: {settings}", folder, relative))

    hooks_error, hooks_name = _hooks_status(folder, parsed)
    if hooks_error:
        errors.append(hooks_error)

    if errors:
        return {"ok": False, "key": parsed, "errors": _unique(errors)}
    return {
        "ok": True,
        "key": parsed,
        "path": relative,
        "hooks_class": hooks_name,
        "is_enabled": True,
    }


def _meta_key_aligned(meta_key: str, parsed: str, folder: Path) -> bool:
    needle = str(parsed or "").replace("\\", "/").strip().strip("/")
    leaf = Path(needle).name if needle else ""
    if meta_key in {needle, leaf}:
        return True
    info = Tag.get_tag_info(meta_key, enabled_only=False)
    if info is None:
        return False
    try:
        return Path(str(info.get("folder") or "")).resolve() == folder.resolve()
    except OSError:
        return False


def _syntax_error(path: Path, label: str) -> str:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=label)
    except SyntaxError as exc:
        line = exc.lineno or "?"
        return f"{label} 语法错误: 第 {line} 行: {exc.msg}"
    except UnicodeError:
        return f"{label} 不是 UTF-8"
    except OSError:
        return f"无法读取 {label}"
    return ""


def _load_settings(path: Path) -> Dict[str, Any] | str:
    try:
        loaded = Discovery.file.load_python_config(path, var_name="settings")
    except Exception as exc:
        return str(exc)
    if not isinstance(loaded, dict):
        return "settings 不是 dict"
    return loaded


def _hooks_status(folder: Path, key: str) -> tuple[str, str]:
    loaded = Tag.load_hooks_class(folder, key)
    if loaded is None:
        return _hooks_exception(folder, key), ""
    hooks_name, hooks_class = loaded[1], loaded[3]
    if not issubclass(hooks_class, TagHooks) or hooks_class is TagHooks:
        return "tag.py 的公开类必须继承 TagHooks", ""
    pending = sorted(getattr(hooks_class, "__abstractmethods__", ()))
    if pending:
        return "未实现钩子: " + "、".join(pending), ""
    return "", hooks_name


def _hooks_exception(folder: Path, key: str) -> str:
    path = folder / "tag.py"
    try:
        source = path.read_text(encoding="utf-8")
        compiled = compile(source, "tag.py", "exec")
        namespace: Dict[str, Any] = {
            "__name__": f"_ntq_agent_validate_tag_{key.replace('/', '_')}"
        }
        exec(compiled, namespace, namespace)  # noqa: S102
    except Exception as exc:
        return f"无法加载 tag.py: {exc}"
    return "tag.py 缺少继承 TagHooks 的公开类"


def _scrub(text: str, folder: Path, relative: str) -> str:
    return (
        str(text)
        .replace(str(folder.resolve()), relative)
        .replace(str(folder), relative)
    )


def _unique(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
