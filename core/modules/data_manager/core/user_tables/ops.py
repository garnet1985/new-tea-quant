"""Userspace 自定义表用例（域逻辑；信道只传参/改 return）。"""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.db.contracts import (
    TABLE_KINDS,
    SchemaManager,
    validate_table_identity,
)
from core.infra.project_context import ProjectContext

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "README.md")
_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
_SUBJECT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
KEY_RULE = "每段以字母开头，仅含字母、数字、下划线；勿用 _ 开头"


class UserTableOps:
    """cust_* 表的脚手架与校验；拒绝污染 core/tables。"""

    @classmethod
    def scaffold(
        cls,
        *,
        key: str,
        kind: str = "data",
        table_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        kind_norm = str(kind or "data").strip().lower() or "data"
        if kind_norm not in TABLE_KINDS:
            return {
                "ok": False,
                "error": f"kind 无效：{kind_norm}，允许 {', '.join(sorted(TABLE_KINDS))}",
            }

        dest, relative = cls._folder(parsed)
        if dest.exists():
            return {"ok": False, "error": f"目标已存在: {relative}"}

        template = (
            ProjectContext.path.get_extensions_tables_directory()
            / "_template"
            / "empty_table"
        )
        if not template.is_dir():
            return {
                "ok": False,
                "error": "表模板不存在: extensions/tables/_template/empty_table",
            }

        name = str(table_name or "").strip() or cls.default_table_name(
            key=parsed, kind=kind_norm
        )
        blocked = cls.refuse_core_structural(name)
        if blocked:
            return blocked
        if not name.startswith("cust_"):
            return {
                "ok": False,
                "requires_confirm": True,
                "scope": "core_system_table",
                "error": (
                    f"拒绝创建 {name!r}：用户表须以 cust_ 开头，"
                    "不要污染 core/tables 或使用 sys_ 前缀"
                ),
            }

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template, dest, ignore=_IGNORE)
            cls._rewrite_placeholders(
                dest, table_name=name, kind=kind_norm, key=parsed
            )
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建表目录: {exc}"}
        except ValueError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "table_name": name,
            "kind": kind_norm,
            "files": ["schema.py", "model.py"],
            "note": (
                f"已在 userspace 生成空表骨架，schema.name={name}。"
                "接着写入字段定义，再 validate_user_table。"
            ),
        }

    @classmethod
    def write_files(
        cls,
        *,
        key: str,
        schema_py: str = "",
        model_py: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        dest, relative = cls._folder(parsed)
        if not dest.is_dir():
            return {
                "ok": False,
                "error": f"表不存在: {relative}。请先 scaffold_user_table",
            }
        schema_body = str(schema_py or "")
        model_body = str(model_py or "")
        if not schema_body.strip() and not model_body.strip():
            return {"ok": False, "error": "至少提供 schema_py、model_py 之一"}

        written: List[str] = []
        try:
            if schema_body.strip():
                shape = cls._schema_shape_error(schema_body)
                if shape:
                    return {"ok": False, "key": parsed, "error": shape}
                (dest / "schema.py").write_text(
                    schema_body if schema_body.endswith("\n") else schema_body + "\n",
                    encoding="utf-8",
                )
                written.append("schema.py")
            if model_body.strip():
                syntax = cls._syntax_error(model_body, "model.py")
                if syntax:
                    return {"ok": False, "key": parsed, "error": syntax}
                if "DbBaseModel" not in model_body:
                    return {
                        "ok": False,
                        "key": parsed,
                        "error": "model.py 须继承 DbBaseModel。文件没有被改。",
                    }
                (dest / "model.py").write_text(
                    model_body if model_body.endswith("\n") else model_body + "\n",
                    encoding="utf-8",
                )
                written.append("model.py")
        except OSError:
            return {"ok": False, "error": f"无法写入 {relative} 下的表文件"}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "files": written,
            "note": "文件已覆盖。接着 validate_user_table，通过之前不要建物理表。",
        }

    @classmethod
    def validate(cls, data_manager: Any, *, key: str) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        dest, relative = cls._folder(parsed)
        schema_file = dest / "schema.py"
        model_file = dest / "model.py"
        if not schema_file.is_file() or not model_file.is_file():
            return {
                "ok": False,
                "key": parsed,
                "errors": [f"表文件不齐: {relative}。需要 schema.py 和 model.py"],
            }

        errors: List[str] = []
        for label, path in (("schema.py", schema_file), ("model.py", model_file)):
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
            return {"ok": False, "key": parsed, "errors": errors}

        model_text = model_file.read_text(encoding="utf-8")
        if "DbBaseModel" not in model_text:
            errors.append("model.py 须继承 DbBaseModel")
        if "class " not in model_text:
            errors.append("model.py 缺少类定义")

        try:
            schema = SchemaManager(database_type="duckdb").load_schema_from_python(
                str(schema_file)
            )
        except Exception as exc:
            return {
                "ok": False,
                "key": parsed,
                "errors": cls._unique(errors + [f"无法加载 schema.py: {exc}"]),
            }
        if not isinstance(schema, dict):
            return {
                "ok": False,
                "key": parsed,
                "errors": cls._unique(errors + ["schema 不是 dict"]),
            }

        blocked = cls.refuse_core_structural(str(schema.get("name") or ""))
        if blocked:
            return {
                "ok": False,
                "key": parsed,
                "requires_confirm": True,
                "scope": "core_system_table",
                "errors": [str(blocked["error"])],
            }
        identity = cls.assert_cust_schema(schema)
        if identity:
            errors.append(identity)

        registered = False
        model_class = ""
        table_name = str(schema.get("name") or "")
        if not errors:
            try:
                cls_obj = data_manager.register_table(str(dest), from_core=False)
                if cls_obj is None:
                    errors.append(
                        "register_table 失败"
                        "（检查 model.py 是否可导入、是否继承 DbBaseModel）"
                    )
                else:
                    registered = True
                    model_class = getattr(cls_obj, "__name__", "") or ""
            except Exception as exc:
                errors.append(f"注册失败: {exc}")

        if errors:
            return {"ok": False, "key": parsed, "errors": cls._unique(errors)}
        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "table_name": table_name,
            "model_class": model_class,
            "registered": registered,
            "note": "校验通过。需要物理表时再 ensure_user_table。",
        }

    @classmethod
    def ensure_physical(cls, data_manager: Any, *, key: str) -> Dict[str, Any]:
        checked = cls.validate(data_manager, key=key)
        if not checked.get("ok"):
            return checked
        table_name = str(checked.get("table_name") or "").strip()
        blocked = cls.refuse_core_structural(table_name)
        if blocked:
            return blocked
        parsed = str(checked.get("key") or key)
        dest, relative = cls._folder(parsed)
        try:
            data_manager.register_table(str(dest), from_core=False)
            model = data_manager.get_table(table_name)
            if model is None:
                return {
                    "ok": False,
                    "key": parsed,
                    "error": f"注册后仍拿不到表实例: {table_name}",
                }
            model.create_table()
        except Exception as exc:
            return {"ok": False, "key": parsed, "error": f"建物理表失败: {exc}"}
        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "table_name": table_name,
            "note": "物理表已确保存在（userspace cust_*）。",
        }

    @classmethod
    def describe(cls, data_manager: Any, *, table_name: str) -> Dict[str, Any]:
        name = str(table_name or "").strip()
        if not name:
            return {"ok": False, "error": "table_name 不能为空"}
        try:
            model = data_manager.get_table(name)
        except Exception as exc:
            return {"ok": False, "error": f"无法读取表: {exc}"}
        if model is None:
            return {"ok": False, "error": f"未注册的表: {name}"}
        schema = getattr(model, "schema", None) or {}
        if not isinstance(schema, dict):
            schema = {}
        fields = schema.get("fields") if isinstance(schema.get("fields"), list) else []
        field_rows: List[Dict[str, Any]] = []
        for item in fields:
            if not isinstance(item, dict):
                continue
            field_rows.append(
                {
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "nullable": item.get("nullable"),
                    "description": item.get("description"),
                }
            )
        owner = (
            "sys"
            if name.startswith("sys_")
            else ("cust" if name.startswith("cust_") else "other")
        )
        return {
            "ok": True,
            "table_name": name,
            "owner": owner,
            "kind": schema.get("kind"),
            "storage_domain": schema.get("storage_domain"),
            "primary_key": schema.get("primaryKey"),
            "fields": field_rows,
            "field_count": len(field_rows),
            "note": (
                "只读摘要。系统表结构性变更须警告+确认，且不要改 core/tables。"
                if owner == "sys"
                else "用户表定义应在 userspace/extensions/tables。"
            ),
        }

    @classmethod
    def list_names(cls, data_manager: Any, *, owner: str = "all") -> Dict[str, Any]:
        own = str(owner or "all").strip().lower() or "all"
        if own not in {"all", "sys", "cust"}:
            return {"ok": False, "error": "owner 仅支持 all / sys / cust"}
        try:
            names = list(data_manager.list_tables())
        except Exception as exc:
            return {"ok": False, "error": f"无法列出表: {exc}"}
        if own == "sys":
            names = [n for n in names if n.startswith("sys_")]
        elif own == "cust":
            names = [n for n in names if n.startswith("cust_")]
        return {"ok": True, "owner": own, "tables": names, "count": len(names)}

    @staticmethod
    def refuse_core_structural(table_name: str) -> Optional[Dict[str, Any]]:
        name = str(table_name or "").strip()
        if name.startswith("sys_"):
            return {
                "ok": False,
                "requires_confirm": True,
                "scope": "core_system_table",
                "error": (
                    f"拒绝结构性操作：{name} 属于系统表（core/tables）。"
                    "请先向用户警告并取得明确确认；确认后也不要改 core/tables，"
                    "应走正式迁移/开发流程。用户自定义表请用 cust_* 写在 userspace。"
                ),
            }
        return None

    @classmethod
    def assert_cust_schema(cls, schema: Dict[str, Any]) -> Optional[str]:
        if not isinstance(schema, dict):
            return "schema 必须是 dict"
        name = str(schema.get("name") or "").strip()
        blocked = cls.refuse_core_structural(name)
        if blocked:
            return str(blocked["error"])
        try:
            validate_table_identity(schema, owner="cust")
        except ValueError as exc:
            return str(exc)
        kind = str(schema.get("kind") or "").strip().lower()
        if kind not in TABLE_KINDS:
            return f"kind 无效：{kind}"
        return None

    @classmethod
    def default_table_name(cls, *, key: str, kind: str = "data") -> str:
        leaf = Path(str(key).replace("\\", "/")).name
        subject = re.sub(r"[^a-z0-9_]", "_", leaf.lower()).strip("_")
        if not subject or not _SUBJECT_RE.match(subject):
            subject = "custom_table"
        kind_norm = str(kind or "data").strip().lower() or "data"
        return f"cust_{kind_norm}_{subject}"

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
        root = ProjectContext.path.get_extensions_tables_directory().resolve()
        dest = (root / key).resolve()
        if not dest.is_relative_to(root) or dest == root:
            raise ValueError(f"路径必须在 userspace/extensions/tables 下: {key}")
        relative = f"extensions/tables/{key}"
        return dest, relative

    @classmethod
    def _rewrite_placeholders(
        cls, dest: Path, *, table_name: str, kind: str, key: str
    ) -> None:
        schema_file = dest / "schema.py"
        model_file = dest / "model.py"
        if not schema_file.is_file() or not model_file.is_file():
            raise ValueError(f"模板复制后文件不齐: {dest}")

        class_name = cls._class_name(key)
        schema_text = schema_file.read_text(encoding="utf-8")
        schema_text, n_name = re.subn(
            r'("name"\s*:\s*")[^"]*(")',
            rf"\g<1>{table_name}\g<2>",
            schema_text,
            count=1,
        )
        schema_text, n_kind = re.subn(
            r'("kind"\s*:\s*")[^"]*(")',
            rf"\g<1>{kind}\g<2>",
            schema_text,
            count=1,
        )
        if n_name != 1 or n_kind != 1:
            raise ValueError("无法写入 schema.name / kind")
        schema_file.write_text(schema_text, encoding="utf-8")
        model_file.write_text(
            model_file.read_text(encoding="utf-8").replace(
                "EmptyTableModel", class_name
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _class_name(key: str) -> str:
        leaf = Path(str(key).replace("\\", "/")).name
        parts = [p for p in re.split(r"[^a-zA-Z0-9]+", leaf) if p]
        if not parts:
            return "CustomTableModel"
        return "".join(p[:1].upper() + p[1:] for p in parts) + "Model"

    @classmethod
    def _schema_shape_error(cls, body: str) -> str:
        syntax = cls._syntax_error(body, "schema.py")
        if syntax:
            return syntax
        schema = cls._load_schema_dict(body)
        if schema is None:
            return (
                "schema.py 必须是 Python，含全局变量 schema = { ... }。"
                "须含 name / kind / primaryKey / fields；name 为 cust_{kind}_主题。"
                "文件没有被改。"
            )
        blocked = cls.refuse_core_structural(str(schema.get("name") or ""))
        if blocked:
            return str(blocked["error"])
        return cls.assert_cust_schema(schema) or ""

    @staticmethod
    def _load_schema_dict(body: str) -> Optional[Dict[str, Any]]:
        try:
            tree = ast.parse(body)
        except SyntaxError:
            return None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "schema":
                        try:
                            value = ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            return None
                        return value if isinstance(value, dict) else None
        return None

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
