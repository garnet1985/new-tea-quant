"""Tag 用例：scaffold / apply_settings_patch / validate_artifact。"""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
_TEMPLATE_REL = Path("_template") / "empty_scenario"
_CONTRACTS = (
    "from core.modules.tag.contracts import TagCalendarAsOfResult, TagContext, TagHooks"
)


class TagArtifactOps:
    """userspace 标签制品编排；信道只传参。"""

    @classmethod
    def scaffold_from_template(cls, raw_path: str) -> Dict[str, Any]:
        try:
            dest, key = cls._resolve_dest(raw_path)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        root = ProjectContext.path.get_tags_root().resolve()
        template = (root / _TEMPLATE_REL).resolve()
        if not template.is_dir():
            return {
                "ok": False,
                "error": "标签模板不存在: extensions/tags/_template/empty_scenario",
            }
        if dest.exists():
            return {"ok": False, "error": f"目标已存在: {dest}"}

        meta_key = Path(key).name
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template, dest, ignore=_IGNORE)
            settings = dest / "settings.py"
            cls._enable_in_settings(settings)
            cls._set_meta_key(settings, meta_key)
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建标签目录: {exc}"}
        except ValueError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

        relative = f"extensions/tags/{key}"
        return {
            "ok": True,
            "key": key,
            "path": relative,
            "dest": str(dest),
            "meta_key": meta_key,
            "files": ["tag.py", "settings.py"],
            "note": f"仍是空模板，meta.key 已写成 {meta_key}",
        }

    @classmethod
    def apply_settings_patch(
        cls,
        *,
        key: str,
        tag_py: str = "",
        settings_py: str = "",
    ) -> Dict[str, Any]:
        try:
            folder, relative = cls._folder_for_key(key)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        if not folder.is_dir():
            return {
                "ok": False,
                "error": f"标签不存在: {relative}。请先 scaffold_from_template",
            }
        if not any(str(x or "").strip() for x in (tag_py, settings_py)):
            return {"ok": False, "error": "至少提供 tag_py、settings_py 之一"}

        written: List[str] = []
        try:
            if str(tag_py or "").strip():
                body = cls.normalize_tag_source(tag_py)
                sig = cls.lint_tag_hooks_source(body)
                if sig:
                    return {"ok": False, "key": key, "error": sig}
                (folder / "tag.py").write_text(body, encoding="utf-8")
                written.append("tag.py")
            if str(settings_py or "").strip():
                shape = cls._settings_shape_error(settings_py)
                if shape:
                    return {"ok": False, "key": key, "error": shape}
                merged = cls.merge_settings_text(folder / "settings.py", settings_py)
                (folder / "settings.py").write_text(merged, encoding="utf-8")
                written.append("settings.py")
        except OSError:
            return {"ok": False, "error": f"无法写入 {relative} 下的标签文件"}

        return {
            "ok": True,
            "key": key,
            "path": relative,
            "files": written,
            "note": "文件已覆盖。接着 validate_artifact，通过之前不要跑打标。",
        }

    @classmethod
    def validate_artifact(cls, *, key: str) -> Dict[str, Any]:
        from core.modules.tag import Tag
        from core.modules.tag.contracts import TagHooks

        try:
            folder, relative = cls._folder_for_key(key)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        tag_file = folder / "tag.py"
        settings_file = folder / "settings.py"
        if not tag_file.is_file() or not settings_file.is_file():
            return {
                "ok": False,
                "key": key,
                "errors": [f"标签文件不齐: {relative}。需要 tag.py 和 settings.py"],
            }

        errors: List[str] = []
        for label, path in (("tag.py", tag_file), ("settings.py", settings_file)):
            syntax = cls._syntax_error_file(path, label)
            if syntax:
                errors.append(syntax)
        if errors:
            return {"ok": False, "key": key, "errors": errors}

        settings = cls._load_settings(settings_file)
        if isinstance(settings, dict):
            meta = settings.get("meta")
            meta_key = ""
            if isinstance(meta, dict):
                meta_key = str(meta.get("key") or "").strip()
            if not meta_key:
                errors.append("settings 缺少 meta.key")
            elif not cls._meta_key_aligned(meta_key, key, folder):
                leaf = Path(str(key).replace("\\", "/")).name
                errors.append(
                    f"meta.key={meta_key!r} 无法标识本标签"
                    f"（请求 {key}，目录叶名 {leaf}）。"
                    f"meta.key 应等于目录名/叶名，或经发现解析到同一文件夹"
                )
            if settings.get("is_enabled") is not True:
                errors.append("is_enabled 必须为 True，否则不能打标")
            defs = settings.get("tag_definitions")
            if not isinstance(defs, list) or not defs:
                errors.append("settings 须含非空 tag_definitions 列表")
        else:
            errors.append(
                cls._scrub(f"无法加载settings.py: {settings}", folder, relative)
            )

        hooks_error, hooks_name = cls._hooks_status(folder, key)
        if hooks_error:
            errors.append(hooks_error)

        if errors:
            return {"ok": False, "key": key, "errors": cls._unique(errors)}
        return {
            "ok": True,
            "key": key,
            "path": relative,
            "hooks_class": hooks_name,
            "is_enabled": True,
        }

    @classmethod
    def normalize_tag_source(cls, body: str) -> str:
        lines = [
            line
            for line in body.splitlines()
            if "import TagHooks" not in line or "core.modules.tag" in line
        ]
        cleaned: List[str] = []
        for line in lines:
            if line.strip() in {
                "from core.modules.tag import TagHooks",
                "from core.modules.tag.core.engines.shared.hooks import TagHooks",
            }:
                continue
            cleaned.append(line)
        lines = cleaned
        if not any("from core.modules.tag.contracts import" in line for line in lines):
            insert_at = 0
            for index, line in enumerate(lines):
                if line.startswith("from __future__"):
                    insert_at = index + 1
            lines.insert(insert_at, _CONTRACTS)
        return "\n".join(lines).strip() + "\n"

    @classmethod
    def lint_tag_hooks_source(cls, body: str) -> str:
        text = str(body or "")
        if "def calculate_tag(self, ctx" in text:
            return ""
        return (
            "calculate_tag 必须写成 def calculate_tag(self, ctx: TagContext) -> dict | None。"
            "返回 {\"value\": ...} 或 None。文件没有被改。"
        )

    @classmethod
    def merge_settings_text(cls, path: Path, body: str) -> str:
        incoming = cls._python_literals(body)
        new_settings = cls._dict_from_settings(incoming)
        old_settings = cls._dict_from_settings(
            path.read_text(encoding="utf-8") if path.is_file() else ""
        )
        if not isinstance(new_settings, dict):
            return incoming
        if not isinstance(old_settings, dict):
            rendered = new_settings
        else:
            rendered = dict(old_settings)
            rendered.update(new_settings)
        if rendered.get("is_enabled") is not True:
            rendered["is_enabled"] = True
        data = rendered.get("data")
        if isinstance(data, dict) and "min_required_records" not in data:
            data["min_required_records"] = 0
        calculation = rendered.setdefault("calculation", {})
        if isinstance(calculation, dict):
            calculation.setdefault("update_mode", "incremental")
            calculation.setdefault("recompute", False)
            execution = calculation.setdefault("execution", {})
            if isinstance(execution, dict):
                base = data.get("base") if isinstance(data, dict) else None
                data_key = ""
                if isinstance(base, dict):
                    data_key = str(base.get("data_key") or "")
                if data_key == "stock.kline.daily":
                    execution.setdefault("mode", "entity_based")
                execution.setdefault("start_date", "")
                execution.setdefault("end_date", "")
        if not isinstance(rendered.get("tag_definitions"), list):
            rendered["tag_definitions"] = []
        return "settings = " + cls._literal(rendered) + "\n"

    @classmethod
    def interpret_execute_result(cls, result: Any) -> None:
        """成功则返回；否则抛 RuntimeError（供 BFF/agent 共用）。"""
        if not isinstance(result, dict) or not result.get("success"):
            message = ""
            if isinstance(result, dict):
                message = str(result.get("message") or "").strip()
                failed = int(result.get("fail") or 0)
                if not message and failed:
                    message = f"标签计算失败（{failed} 个任务）"
            raise RuntimeError(message or "标签计算未完成")
        if result.get("dry_run"):
            return
        produced = int(result.get("tag_values_count") or 0)
        saved = int(result.get("saved_tag_values") or 0)
        if produced > 0 and saved < produced:
            raise RuntimeError(
                f"标签值未全部落库（计算 {produced} 行，写入 {saved} 行）"
            )

    @classmethod
    def _resolve_dest(cls, raw_path: str) -> tuple[Path, str]:
        from core.modules.tag import Tag

        text = str(raw_path or "").strip()
        if not text:
            raise ValueError("目标路径不能为空")
        root = ProjectContext.path.get_tags_root().resolve()
        candidate = Path(text).expanduser()
        if candidate.is_absolute():
            dest = candidate.resolve()
            try:
                key = dest.relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError(f"目标路径须在 {root} 下") from exc
        else:
            key = text.strip("/")
            dest = (root / key).resolve()
        if not key or key.startswith("..") or not dest.is_relative_to(root):
            raise ValueError("目标路径无效")
        if not Tag.is_valid_path(key):
            raise ValueError(
                "路径须为 machine-readable：每段以字母开头，仅含字母、数字、下划线"
                f"（当前: {key!r}）"
            )
        return dest, key

    @classmethod
    def _folder_for_key(cls, key: str) -> tuple[Path, str]:
        text = str(key or "").strip().strip("/")
        if not text:
            raise ValueError("key 不能为空")
        from core.modules.tag import Tag

        if not Tag.is_valid_path(text):
            # meta.key 可能合法但 path 规则不同——尝试 resolve
            try:
                folder = Tag.resolve_folder(text)
                path_id = Tag.resolve_path(text)
                return folder, f"extensions/tags/{path_id}"
            except (FileNotFoundError, ValueError, OSError) as exc:
                raise ValueError(f"目录名不合法：{text}") from exc
        try:
            folder = Tag.resolve_folder(text)
            path_id = Tag.resolve_path(text)
            return folder, f"extensions/tags/{path_id}"
        except (FileNotFoundError, ValueError, OSError):
            root = ProjectContext.path.get_tags_root().resolve()
            dest = (root / text).resolve()
            if not dest.is_relative_to(root):
                raise ValueError(f"目录名不合法：{text}")
            return dest, f"extensions/tags/{text}"

    @classmethod
    def _enable_in_settings(cls, settings_file: Path) -> None:
        if not settings_file.is_file():
            raise ValueError(f"复制后缺少 settings.py: {settings_file}")
        text = settings_file.read_text(encoding="utf-8")
        new_text, count = re.subn(
            r'("is_enabled"\s*:\s*)False', r"\1True", text, count=1
        )
        if count != 1:
            raise ValueError(f"无法在 {settings_file} 中将 is_enabled 设为 True")
        settings_file.write_text(new_text, encoding="utf-8")

    @classmethod
    def _set_meta_key(cls, settings_file: Path, key: str) -> None:
        if not settings_file.is_file():
            raise ValueError(f"缺少 settings.py: {settings_file}")
        text = settings_file.read_text(encoding="utf-8")
        escaped = str(key or "").strip().replace("\\", "\\\\").replace('"', '\\"')
        if not escaped:
            raise ValueError("meta.key 不能为空")
        if re.search(r'["\']key["\']\s*:', text):
            new_text, count = re.subn(
                r'("key"\s*:\s*")[^"]*(")',
                rf"\g<1>{escaped}\g<2>",
                text,
                count=1,
            )
            if count != 1:
                raise ValueError(f"无法写入 meta.key：{key}")
            settings_file.write_text(new_text, encoding="utf-8")
            return
        patterns = (
            (r'("meta"\s*:\s*\{)(\s*\n)', rf'\1\n        "key": "{escaped}",\2'),
            (r'("meta"\s*:\s*\{)(\s*\})', rf'\1\n        "key": "{escaped}",\n    \2'),
        )
        for pattern, repl in patterns:
            new_text, count = re.subn(pattern, repl, text, count=1)
            if count == 1:
                settings_file.write_text(new_text, encoding="utf-8")
                return
        raise ValueError(f"无法在 {settings_file} 中注入 meta.key")

    @classmethod
    def _meta_key_aligned(cls, meta_key: str, parsed: str, folder: Path) -> bool:
        from core.modules.tag import Tag

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

    @classmethod
    def _hooks_status(cls, folder: Path, key: str) -> tuple[str, str]:
        from core.modules.tag import Tag
        from core.modules.tag.contracts import TagHooks

        loaded = Tag.load_hooks_class(folder, key)
        if loaded is None:
            return cls._hooks_exception(folder, key), ""
        hooks_name, hooks_class = loaded[1], loaded[3]
        if not issubclass(hooks_class, TagHooks) or hooks_class is TagHooks:
            return "tag.py 的公开类必须继承 TagHooks", ""
        pending = sorted(getattr(hooks_class, "__abstractmethods__", ()))
        if pending:
            return "未实现钩子: " + "、".join(pending), ""
        return "", hooks_name

    @classmethod
    def _hooks_exception(cls, folder: Path, key: str) -> str:
        path = folder / "tag.py"
        try:
            source = path.read_text(encoding="utf-8")
            compiled = compile(source, "tag.py", "exec")
            namespace: Dict[str, Any] = {
                "__name__": f"_ntq_validate_tag_{key.replace('/', '_')}"
            }
            exec(compiled, namespace, namespace)  # noqa: S102
        except Exception as exc:
            return f"无法加载 tag.py: {exc}"
        return "tag.py 缺少继承 TagHooks 的公开类"

    @classmethod
    def _settings_shape_error(cls, body: str) -> str:
        if cls._dict_from_settings(cls._python_literals(body)) is None:
            return (
                "settings.py 必须是 Python，以 settings = { 开头。"
                "布尔写 True / False。不要写 YAML。"
                "至少包含 is_enabled、meta.key、data.base、tag_definitions。"
                "文件没有被改。"
            )
        return ""

    @staticmethod
    def _load_settings(path: Path) -> Dict[str, Any] | str:
        try:
            loaded = Discovery.file.load_python_config(path, var_name="settings")
        except Exception as exc:
            return str(exc)
        if not isinstance(loaded, dict):
            return "settings 不是 dict"
        return loaded

    @staticmethod
    def _dict_from_settings(body: str) -> Optional[Dict[str, Any]]:
        text = str(body or "")
        marker = text.find("settings")
        if marker < 0:
            return None
        start = text.find("{", marker)
        if start < 0:
            return None
        try:
            value = ast.literal_eval(text[start:])
        except (SyntaxError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _python_literals(body: str) -> str:
        return (
            body.replace(": true", ": True")
            .replace(": false", ": False")
            .replace(": null", ": None")
        )

    @staticmethod
    def _literal(value: Any) -> str:
        if isinstance(value, bool):
            return "True" if value else "False"
        if value is None:
            return "None"
        if isinstance(value, str):
            return repr(value)
        if isinstance(value, (int, float)):
            return repr(value)
        if isinstance(value, list):
            if not value:
                return "[]"
            return "[" + ", ".join(TagArtifactOps._literal(i) for i in value) + "]"
        if isinstance(value, dict):
            if not value:
                return "{}"
            parts = [
                repr(str(k)) + ": " + TagArtifactOps._literal(v)
                for k, v in value.items()
            ]
            return "{" + ", ".join(parts) + "}"
        return repr(value)

    @staticmethod
    def _syntax_error_file(path: Path, label: str) -> str:
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=label)
        except SyntaxError as exc:
            return f"{label} 语法错误: 第 {exc.lineno or '?'} 行: {exc.msg}"
        except UnicodeError:
            return f"{label} 不是 UTF-8"
        except OSError:
            return f"无法读取 {label}"
        return ""

    @staticmethod
    def _scrub(text: str, folder: Path, relative: str) -> str:
        return (
            str(text)
            .replace(str(folder.resolve()), relative)
            .replace(str(folder), relative)
        )

    @staticmethod
    def _unique(items: List[str]) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                out.append(item)
        return out
