"""validate_strategy：用 NTQ 的发现规则加载钩子和 settings。"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List

from core.infra.discovery import Discovery
from core.modules.strategy.contracts import StrategyHooks
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    StrategyDraft,
)
from core.modules.strategy.core.services.discovery.hooks_loader import (
    StrategyHooksLoader,
)
from core.modules.agent.core.tools.strategy._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)


def validate_strategy(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """加载已写好的策略。失败时返回错误列表，不启动回测。"""
    parsed = parse_strategy_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, relative = located
    strategy_file = folder / "strategy.py"
    settings_file = folder / "settings.py"
    if not strategy_file.is_file() or not settings_file.is_file():
        return {
            "ok": False,
            "key": parsed,
            "errors": [f"策略文件不齐: {relative}。需要 strategy.py 和 settings.py"],
        }

    errors: List[str] = []
    for label, path in (("strategy.py", strategy_file), ("settings.py", settings_file)):
        syntax = _syntax_error(path, label)
        if syntax:
            errors.append(syntax)
    if errors:
        return {"ok": False, "key": parsed, "errors": errors}

    draft = StrategyDraft(
        unique_relative_path=parsed,
        strategy_file=strategy_file,
        settings_file=settings_file,
    )
    draft_errors: List[str] = []
    if not draft.is_valid():
        draft_errors = [
            _scrub(item, folder, relative) for item in draft.validation_errors()
        ]

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
                f"meta.key={meta_key!r} 无法标识本策略"
                f"（请求 {parsed}，目录叶名 {leaf}）。"
                f"meta.key 应等于目录名/叶名，或经发现解析到同一文件夹"
            )
        if settings.get("is_enabled") is not True:
            errors.append("is_enabled 必须为 True，否则不能回测")
    elif not any(item.startswith("无法加载settings.py") for item in draft_errors):
        errors.append(_scrub(f"无法加载settings.py: {settings}", folder, relative))

    hooks_error, hooks_name = _hooks_status(folder, parsed)
    for item in draft_errors:
        if hooks_error and "strategy.py" in item:
            continue
        errors.append(item)
    if hooks_error:
        errors.append(hooks_error)
    bar_access = _bar_attribute_access(strategy_file)
    if bar_access:
        errors.append(bar_access)

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
    """Accept short aliases (rsi_v1) under descriptive folders (rsi_v1_baseline)."""
    needle = str(parsed or "").replace("\\", "/").strip().strip("/")
    leaf = Path(needle).name if needle else ""
    if meta_key in {needle, leaf}:
        return True
    try:
        from core.modules.strategy import Strategy

        resolved = Strategy.resolve_folder(meta_key).resolve()
        return resolved == folder.resolve()
    except (FileNotFoundError, ValueError, OSError):
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
    loaded = StrategyHooksLoader.load_hooks_class(folder, key)
    if loaded is None:
        return _hooks_exception(folder, key), ""
    hooks_name, hooks_class = loaded[1], loaded[3]
    if not issubclass(hooks_class, StrategyHooks) or hooks_class is StrategyHooks:
        return "strategy.py 的公开类必须继承 StrategyHooks", ""
    pending = sorted(getattr(hooks_class, "__abstractmethods__", ()))
    if pending:
        return "未实现钩子: " + "、".join(pending), ""
    return "", hooks_name


def _hooks_exception(folder: Path, key: str) -> str:
    """加载器失败时只记日志。这里再执行一次，把异常原文交给模型。"""
    path = folder / "strategy.py"
    try:
        source = path.read_text(encoding="utf-8")
        compiled = compile(source, "strategy.py", "exec")
        namespace: Dict[str, Any] = {
            "__name__": f"_ntq_agent_validate_{key.replace('/', '_')}"
        }
        exec(compiled, namespace, namespace)  # noqa: S102
    except Exception as exc:
        return f"无法加载 strategy.py: {exc}"
    return "strategy.py 缺少继承 StrategyHooks 的公开类"


def _bar_attribute_access(path: Path) -> str:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if ".macd_" in source or ".get(" not in source and "records.last" in source:
        return 'K 线是 dict。用 bar.get("字段")，不要写成 bar.字段'
    return ""


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
