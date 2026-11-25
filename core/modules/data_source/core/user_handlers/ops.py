"""Userspace 数据源 handler 脚手架 / 写文件 / mapping / 校验（域逻辑；信道只传参）。"""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.infra.project_context import ProjectContext
from core.modules.data_source.core.data_class.config import DataSourceConfig
from core.modules.data_source.core.data_class.error import DataSourceConfigError
from core.modules.data_source.core.data_class.handler_mapping import HandlerMapping
from core.modules.data_source.core.reserved_dependencies import RESERVED_DEPENDENCY_KEYS
from core.modules.data_source.core.service.manager_helper import DataSourceManagerHelper

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "README.md")
_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
KEY_RULE = "每段以字母开头，仅含字母、数字、下划线；勿用 _ 开头；勿用保留依赖关键字"


class DataSourceHandlerOps:
    """handlers/_template/example → userspace handler；拒写 _template。"""

    @classmethod
    def scaffold(
        cls,
        *,
        key: str,
        hooks_class_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        if parsed in RESERVED_DEPENDENCY_KEYS or parsed.split("/")[-1] in RESERVED_DEPENDENCY_KEYS:
            return {
                "ok": False,
                "error": (
                    f"key 不能使用保留依赖关键字: {parsed}。"
                    f"保留字: {sorted(RESERVED_DEPENDENCY_KEYS)}"
                ),
            }

        dest, relative = cls._folder(parsed)
        if dest.exists():
            return {"ok": False, "error": f"目标已存在: {relative}"}

        template = (
            ProjectContext.path.get_data_source_handlers_directory()
            / "_template"
            / "example"
        )
        if not template.is_dir():
            return {
                "ok": False,
                "error": "数据源模板不存在: extensions/data_source/handlers/_template/example",
            }

        class_name = str(hooks_class_name or "").strip() or cls._hooks_class_name(parsed)
        if not re.match(r"^[A-Z][A-Za-z0-9_]*$", class_name):
            return {
                "ok": False,
                "error": f"hooks 类名不合法: {class_name}（须大写开头，仅字母数字下划线）",
            }

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template, dest, ignore=_IGNORE)
            cls._rewrite_placeholders(dest, class_name=class_name)
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建 handler 目录: {exc}"}
        except ValueError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

        mapping_key = cls.mapping_key_for(parsed)
        handler_ref = cls.default_handler_ref(parsed, class_name)
        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "mapping_key": mapping_key,
            "handler": handler_ref,
            "hooks_class": class_name,
            "files": ["handler.py", "settings.py"],
            "note": (
                f"已生成空 handler 骨架（类名 {class_name}）。"
                "接着 write_user_handler_files 写 settings/钩子，"
                f"再 apply_mapping_entry(key={mapping_key!r}, handler={handler_ref!r})，"
                "最后 validate_user_handler。"
            ),
        }

    @classmethod
    def write_files(
        cls,
        *,
        key: str,
        handler_py: str = "",
        settings_py: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        dest, relative = cls._folder(parsed)
        if not dest.is_dir():
            return {
                "ok": False,
                "error": f"handler 不存在: {relative}。请先 scaffold_user_handler",
            }
        if any(seg.startswith("_") for seg in Path(parsed).parts):
            return {"ok": False, "error": f"拒绝写入模板/私有目录: {relative}"}

        handler_body = str(handler_py or "")
        settings_body = str(settings_py or "")
        if not handler_body.strip() and not settings_body.strip():
            return {"ok": False, "error": "至少提供 handler_py、settings_py 之一"}

        written: List[str] = []
        try:
            if handler_body.strip():
                syntax = cls._syntax_error(handler_body, "handler.py")
                if syntax:
                    return {"ok": False, "key": parsed, "error": syntax}
                if "DataSourceHooks" not in handler_body:
                    return {
                        "ok": False,
                        "key": parsed,
                        "error": "handler.py 须继承 DataSourceHooks。文件没有被改。",
                    }
                if "class " not in handler_body:
                    return {
                        "ok": False,
                        "key": parsed,
                        "error": "handler.py 缺少类定义。文件没有被改。",
                    }
                (dest / "handler.py").write_text(
                    handler_body if handler_body.endswith("\n") else handler_body + "\n",
                    encoding="utf-8",
                )
                written.append("handler.py")
            if settings_body.strip():
                syntax = cls._syntax_error(settings_body, "settings.py")
                if syntax:
                    return {"ok": False, "key": parsed, "error": syntax}
                (dest / "settings.py").write_text(
                    settings_body if settings_body.endswith("\n") else settings_body + "\n",
                    encoding="utf-8",
                )
                written.append("settings.py")
        except OSError:
            return {"ok": False, "error": f"无法写入 {relative} 下的 handler 文件"}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "files": written,
            "note": "文件已覆盖。接着 apply_mapping_entry（若尚未登记），再 validate_user_handler。",
        }

    @classmethod
    def apply_mapping_entry(
        cls,
        *,
        key: str,
        handler: str,
        is_enabled: bool = True,
        depends_on: Optional[Sequence[str]] = None,
        weight: Optional[int] = None,
    ) -> Dict[str, Any]:
        mapping_key = str(key or "").strip()
        if not mapping_key:
            return {"ok": False, "error": "key 不能为空"}
        if "/" in mapping_key or "\\" in mapping_key:
            return {
                "ok": False,
                "error": "mapping key 须为扁平名（无斜杠）；嵌套目录用 handler 路径表达",
            }
        if mapping_key in RESERVED_DEPENDENCY_KEYS:
            return {
                "ok": False,
                "error": (
                    f"key 不能使用保留依赖关键字: {mapping_key}。"
                    f"保留字: {sorted(RESERVED_DEPENDENCY_KEYS)}"
                ),
            }
        if not _PATH_SEGMENT_RE.match(mapping_key):
            return {"ok": False, "error": f"mapping key 不合法: {mapping_key}。{KEY_RULE}"}

        handler_ref = str(handler or "").strip()
        if not handler_ref or "." not in handler_ref:
            return {
                "ok": False,
                "error": "handler 须为「模块.类名」格式，例如 my_src.MySrcHooks",
            }

        entry: Dict[str, Any] = {
            "handler": handler_ref,
            "is_enabled": bool(is_enabled),
        }
        if depends_on is not None:
            deps = [str(x).strip() for x in depends_on if str(x).strip()]
            entry["depends_on"] = deps
        if weight is not None:
            try:
                entry["weight"] = int(weight)
            except (TypeError, ValueError):
                return {"ok": False, "error": "weight 须为整数"}

        mapping_path = ProjectContext.path.get_data_source_mapping_path()
        if not mapping_path.is_file():
            return {"ok": False, "error": f"mapping.py 不存在: {mapping_path}"}

        current = DataSourceManagerHelper.load_mapping_from_py(mapping_path)
        if not isinstance(current, dict):
            return {"ok": False, "error": "无法加载 mapping.py 中的 DATA_SOURCES"}

        merged = dict(current)
        merged[mapping_key] = entry
        try:
            HandlerMapping(merged)
        except Exception as exc:
            return {"ok": False, "error": f"mapping 校验失败: {exc}"}

        try:
            text = mapping_path.read_text(encoding="utf-8")
            new_text = cls._replace_data_sources_block(text, merged)
            mapping_path.write_text(new_text, encoding="utf-8")
        except Exception as exc:
            return {"ok": False, "error": f"无法写入 mapping.py: {exc}"}

        return {
            "ok": True,
            "key": mapping_key,
            "handler": handler_ref,
            "is_enabled": bool(is_enabled),
            "depends_on": list(entry.get("depends_on") or []),
            "weight": entry.get("weight"),
            "note": "已写入 DATA_SOURCES。接着 validate_user_handler。",
        }

    @classmethod
    def validate(cls, *, key: str) -> Dict[str, Any]:
        """按 mapping key 校验 settings + handler 类；不跑 renew。"""
        mapping_key = str(key or "").strip()
        if not mapping_key:
            return {"ok": False, "error": "key 不能为空"}
        if "/" in mapping_key or "\\" in mapping_key:
            return {
                "ok": False,
                "error": "validate 使用 mapping key（扁平名），不是目录斜杠路径",
            }

        errors: List[str] = []
        mapping_path = ProjectContext.path.get_data_source_mapping_path()
        data_sources = DataSourceManagerHelper.load_mapping_from_py(mapping_path)
        if not isinstance(data_sources, dict):
            return {"ok": False, "key": mapping_key, "errors": ["无法加载 mapping.py"]}

        info = data_sources.get(mapping_key)
        if not isinstance(info, dict):
            return {
                "ok": False,
                "key": mapping_key,
                "errors": [
                    f"mapping 中无此 key: {mapping_key}。请先 apply_mapping_entry"
                ],
            }

        handler_ref = str(info.get("handler") or "").strip()
        if not handler_ref:
            errors.append("mapping 缺少 handler")

        settings_path = cls._resolve_settings_path(mapping_key, handler_ref)
        if settings_path is None or not settings_path.is_file():
            return {
                "ok": False,
                "key": mapping_key,
                "errors": cls._unique(
                    errors + [f"找不到 settings.py（key={mapping_key}）"]
                ),
            }

        handler_dir = settings_path.parent
        handler_file = handler_dir / "handler.py"
        relative = cls._relative_handlers_path(handler_dir)

        for label, path in (("handler.py", handler_file), ("settings.py", settings_path)):
            if not path.is_file():
                errors.append(f"缺少 {label}")
                continue
            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source, filename=label)
            except SyntaxError as exc:
                errors.append(f"{label} 语法错误: 第 {exc.lineno or '?'} 行: {exc.msg}")
            except UnicodeError:
                errors.append(f"{label} 不是 UTF-8")
            except OSError:
                errors.append(f"无法读取 {label}")

        if errors:
            return {"ok": False, "key": mapping_key, "errors": cls._unique(errors)}

        config_dict = DataSourceManagerHelper.load_config_from_py(settings_path)
        if not isinstance(config_dict, dict):
            return {
                "ok": False,
                "key": mapping_key,
                "errors": [
                    "settings.py 须定义 settings = {...}（模板注释态不算）"
                ],
            }

        table_name = ""
        try:
            config = DataSourceConfig.from_dict(config_dict, mapping_key)
            table_name = str(config.get_table_name())
        except DataSourceConfigError as exc:
            return {"ok": False, "key": mapping_key, "errors": [str(exc)]}
        except Exception as exc:
            return {"ok": False, "key": mapping_key, "errors": [f"配置解析失败: {exc}"]}

        handler_cls = None
        if handler_ref:
            try:
                handler_cls = DataSourceManagerHelper.find_handler_class_from_mappings(
                    {"handler": handler_ref}, mapping_key
                )
            except Exception as exc:
                errors.append(f"无法解析 handler: {exc}")
            if handler_cls is None:
                errors.append(f"无法加载 handler 类: {handler_ref}")
            elif not DataSourceManagerHelper.is_valid_handler(handler_cls):
                errors.append(
                    f"handler 无效: {handler_ref}（须为 DataSourceHooks 子类且非基类本身）"
                )

        table_registered = False
        if table_name:
            try:
                from core.modules.data_manager import DataManager

                model = DataManager.get_instance().get_table(table_name)
                table_registered = model is not None
            except Exception:
                table_registered = False
            if not table_registered:
                errors.append(
                    f"绑定表未注册: {table_name}。"
                    "请先确保表存在（用户表走 create_table / validate_table / ensure_physical_table）"
                )

        depends = info.get("depends_on") or []
        if isinstance(depends, list):
            for dep in depends:
                dep_s = str(dep).strip()
                if not dep_s:
                    continue
                if dep_s in RESERVED_DEPENDENCY_KEYS:
                    continue
                if dep_s not in data_sources:
                    errors.append(f"depends_on 引用不存在的数据源: {dep_s}")

        if errors:
            return {"ok": False, "key": mapping_key, "errors": cls._unique(errors)}

        return {
            "ok": True,
            "key": mapping_key,
            "path": relative,
            "handler": handler_ref,
            "hooks_class": getattr(handler_cls, "__name__", "") or "",
            "table": table_name,
            "table_registered": table_registered,
            "is_enabled": bool(info.get("is_enabled", True)),
            "note": "校验通过（未执行 renew）。可用 cli renew / DataSourceManager.renew 拉取。",
        }

    @classmethod
    def mapping_key_for(cls, folder_key: str) -> str:
        return Path(str(folder_key).replace("\\", "/")).name

    @classmethod
    def default_handler_ref(cls, folder_key: str, class_name: str) -> str:
        module = str(folder_key).replace("\\", "/").strip("/").replace("/", ".")
        return f"{module}.{class_name}"

    @classmethod
    def is_valid_folder_key(cls, relative_path: str) -> bool:
        text = str(relative_path or "").strip().strip("/")
        if not text or text.startswith("_"):
            return False
        segments = [seg for seg in text.split("/") if seg]
        if not segments or any(seg.startswith("_") for seg in segments):
            return False
        return all(bool(_PATH_SEGMENT_RE.match(seg)) for seg in segments)

    @classmethod
    def _normalize_key(cls, key: str) -> str | Dict[str, Any]:
        text = str(key or "").strip().strip("/")
        if not text:
            return {"ok": False, "error": "key 不能为空"}
        if ".." in text.split("/") or text.startswith("/"):
            return {"ok": False, "error": f"目录名不合法：{text}"}
        if not cls.is_valid_folder_key(text):
            return {"ok": False, "error": f"目录名不合法：{text}。{KEY_RULE}"}
        return text

    @classmethod
    def _folder(cls, key: str) -> tuple[Path, str]:
        root = ProjectContext.path.get_data_source_handlers_directory().resolve()
        dest = (root / key).resolve()
        if not dest.is_relative_to(root) or dest == root:
            raise ValueError(
                f"路径必须在 userspace/extensions/data_source/handlers 下: {key}"
            )
        relative = f"extensions/data_source/handlers/{key}"
        return dest, relative

    @classmethod
    def _rewrite_placeholders(cls, dest: Path, *, class_name: str) -> None:
        handler_file = dest / "handler.py"
        if not handler_file.is_file() or not (dest / "settings.py").is_file():
            raise ValueError(f"模板复制后文件不齐: {dest}")
        text = handler_file.read_text(encoding="utf-8")
        if "ExampleHooks" not in text:
            raise ValueError("模板 handler.py 缺少 ExampleHooks 占位")
        handler_file.write_text(
            text.replace("ExampleHooks", class_name),
            encoding="utf-8",
        )

    @staticmethod
    def _hooks_class_name(key: str) -> str:
        leaf = Path(str(key).replace("\\", "/")).name
        parts = [p for p in re.split(r"[^a-zA-Z0-9]+", leaf) if p]
        if not parts:
            return "CustomHooks"
        return "".join(p[:1].upper() + p[1:] for p in parts) + "Hooks"

    @classmethod
    def _resolve_settings_path(
        cls, mapping_key: str, handler_ref: str
    ) -> Optional[Path]:
        handlers_root = ProjectContext.path.get_data_source_handlers_directory()
        direct = handlers_root / mapping_key / "settings.py"
        if direct.is_file():
            return direct
        # handler 简写：a.b.Class → handlers/a/b/settings.py
        if handler_ref and "." in handler_ref:
            parts = handler_ref.split(".")
            module_parts = parts[:-1]
            if module_parts:
                nested = handlers_root.joinpath(*module_parts) / "settings.py"
                if nested.is_file():
                    return nested
        from core.infra.discovery import Discovery

        return Discovery.file.find_in_tree(handlers_root, mapping_key, "settings.py")

    @classmethod
    def _relative_handlers_path(cls, handler_dir: Path) -> str:
        root = ProjectContext.path.get_data_source_handlers_directory().resolve()
        try:
            rel = handler_dir.resolve().relative_to(root)
            return f"extensions/data_source/handlers/{rel.as_posix()}"
        except ValueError:
            return str(handler_dir)

    @classmethod
    def _replace_data_sources_block(
        cls, text: str, data_sources: Dict[str, Any]
    ) -> str:
        idx = text.find("DATA_SOURCES")
        if idx < 0:
            raise ValueError("mapping.py 缺少 DATA_SOURCES")
        eq = text.find("=", idx)
        if eq < 0:
            raise ValueError("mapping.py DATA_SOURCES 赋值语法错误")
        brace_start = text.find("{", eq)
        if brace_start < 0:
            raise ValueError("mapping.py DATA_SOURCES 缺少字典字面量")
        depth = 0
        brace_end = -1
        for i in range(brace_start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break
        if brace_end < 0:
            raise ValueError("mapping.py DATA_SOURCES 字典未闭合")
        rendered = "DATA_SOURCES = " + cls._format_mapping(data_sources) + "\n"
        suffix = text[brace_end + 1 :]
        if suffix and not suffix.startswith("\n"):
            suffix = "\n" + suffix.lstrip("\n")
        return text[:idx] + rendered + suffix

    @classmethod
    def _format_mapping(cls, data_sources: Dict[str, Any]) -> str:
        lines = ["{"]
        for name, cfg in data_sources.items():
            if not isinstance(cfg, dict):
                continue
            lines.append(f"    {cls._py_str(name)}: {{")
            # 稳定字段顺序
            ordered_keys = ["handler", "is_enabled", "weight", "depends_on"]
            seen = set()
            for field in ordered_keys:
                if field not in cfg:
                    continue
                seen.add(field)
                lines.append(
                    f"        {cls._py_str(field)}: {cls._py_literal(cfg[field])},"
                )
            for field, value in cfg.items():
                if field in seen:
                    continue
                lines.append(
                    f"        {cls._py_str(field)}: {cls._py_literal(value)},"
                )
            lines.append("    },")
        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def _py_str(value: str) -> str:
        return repr(str(value))

    @classmethod
    def _py_literal(cls, value: Any) -> str:
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, int) and not isinstance(value, bool):
            return str(int(value))
        if isinstance(value, str):
            return repr(value)
        if isinstance(value, list):
            inner = ", ".join(cls._py_literal(x) for x in value)
            return f"[{inner}]"
        return repr(value)

    @staticmethod
    def _syntax_error(body: str, label: str) -> str:
        try:
            ast.parse(body, filename=label)
        except SyntaxError as exc:
            return f"{label} 语法错误: 第 {exc.lineno or '?'} 行: {exc.msg}"
        return ""

    @staticmethod
    def _unique(items: List[str]) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                out.append(item)
        return out
