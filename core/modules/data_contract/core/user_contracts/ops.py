"""Userspace 数据契约脚手架 / 写文件 / data_keys / 校验（域逻辑；信道只传参）。"""

from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "README.md")
_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
_DATA_KEY_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_]*)+$")
_CONST_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_TEMPLATE_DIRS = frozenset({"contract_example"})
KEY_RULE = "每段以字母开头，仅含字母、数字、下划线；勿用 _ 开头；勿用模板名 contract_example"
VALID_TYPES = frozenset({"time_series", "non_time_series"})
VALID_SCOPES = frozenset({"global", "per_entity"})


class UserContractOps:
    """contract_example → userspace contract；登记 USER_DATA_KEY；拒写模板目录。"""

    @classmethod
    def scaffold(
        cls,
        *,
        key: str,
        data_key: Optional[str] = None,
        const_name: Optional[str] = None,
        contract_type: str = "non_time_series",
        scope: str = "global",
        list_data_key: str = "",
        display_name: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_folder_key(key)
        if isinstance(parsed, dict):
            return parsed
        if parsed in _TEMPLATE_DIRS or parsed.split("/")[-1] in _TEMPLATE_DIRS:
            return {"ok": False, "error": f"不能使用模板目录名: {parsed}"}

        ctype = str(contract_type or "non_time_series").strip().lower()
        if ctype not in VALID_TYPES:
            return {
                "ok": False,
                "error": f"contract_type 无效: {ctype}，允许 {sorted(VALID_TYPES)}",
            }
        sc = str(scope or "global").strip().lower()
        if sc not in VALID_SCOPES:
            return {
                "ok": False,
                "error": f"scope 无效: {sc}，允许 {sorted(VALID_SCOPES)}",
            }
        list_key = str(list_data_key or "").strip()
        if sc == "per_entity" and not list_key:
            return {
                "ok": False,
                "error": "scope=per_entity 时必须提供 list_data_key（如 stock.list）",
            }

        dk = str(data_key or "").strip() or cls.default_data_key(parsed)
        if not _DATA_KEY_RE.match(dk):
            return {
                "ok": False,
                "error": (
                    f"data_key 不合法: {dk}。"
                    "须为点分小写段，如 my.custom.data"
                ),
            }
        const = str(const_name or "").strip() or cls.const_name_for(dk)
        if not _CONST_RE.match(const):
            return {
                "ok": False,
                "error": f"const_name 不合法: {const}（须 SCREAMING_SNAKE）",
            }

        dest, relative = cls._folder(parsed)
        if dest.exists():
            return {"ok": False, "error": f"目标已存在: {relative}"}

        template = (
            ProjectContext.path.get_data_contract_root() / "contract_example"
        )
        if not template.is_dir():
            return {
                "ok": False,
                "error": "契约模板不存在: extensions/data_contract/contract_example",
            }

        display = str(display_name or "").strip() or parsed.replace("/", ".")
        loader_class = cls._loader_class_name(parsed)

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template, dest, ignore=_IGNORE)
            cls._rewrite_placeholders(
                dest,
                const_name=const,
                data_key=dk,
                contract_type=ctype,
                scope=sc,
                list_data_key=list_key,
                display_name=display,
                loader_class=loader_class,
            )
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建契约目录: {exc}"}
        except ValueError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "data_key": dk,
            "const_name": const,
            "contract_type": ctype,
            "scope": sc,
            "list_data_key": list_key or None,
            "files": ["declaration.py", "loader.py"],
            "note": (
                f"已生成空契约骨架（{const} = {dk!r}）。"
                "接着 write_user_contract_files，"
                f"再 apply_user_data_key(const_name={const!r}, data_key={dk!r})，"
                "最后 validate_user_contract。"
            ),
        }

    @classmethod
    def write_files(
        cls,
        *,
        key: str,
        declaration_py: str = "",
        loader_py: str = "",
        contract_py: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_folder_key(key)
        if isinstance(parsed, dict):
            return parsed
        dest, relative = cls._folder(parsed)
        if not dest.is_dir():
            return {
                "ok": False,
                "error": f"契约不存在: {relative}。请先 scaffold_user_contract",
            }
        if parsed in _TEMPLATE_DIRS or any(
            seg.startswith("_") for seg in Path(parsed).parts
        ):
            return {"ok": False, "error": f"拒绝写入模板/私有目录: {relative}"}

        decl_body = str(declaration_py or "")
        loader_body = str(loader_py or "")
        contract_body = str(contract_py or "")
        if (
            not decl_body.strip()
            and not loader_body.strip()
            and not contract_body.strip()
        ):
            return {
                "ok": False,
                "error": "至少提供 declaration_py、loader_py、contract_py 之一",
            }

        written: List[str] = []
        try:
            if decl_body.strip():
                syntax = cls._syntax_error(decl_body, "declaration.py")
                if syntax:
                    return {"ok": False, "key": parsed, "error": syntax}
                if "_DECLARATION" not in decl_body:
                    return {
                        "ok": False,
                        "key": parsed,
                        "error": "declaration.py 须导出 *_DECLARATION。文件没有被改。",
                    }
                (dest / "declaration.py").write_text(
                    decl_body if decl_body.endswith("\n") else decl_body + "\n",
                    encoding="utf-8",
                )
                written.append("declaration.py")
            if loader_body.strip():
                syntax = cls._syntax_error(loader_body, "loader.py")
                if syntax:
                    return {"ok": False, "key": parsed, "error": syntax}
                if "BaseDataContractLoader" not in loader_body:
                    return {
                        "ok": False,
                        "key": parsed,
                        "error": "loader.py 须继承 BaseDataContractLoader。文件没有被改。",
                    }
                if "class " not in loader_body:
                    return {
                        "ok": False,
                        "key": parsed,
                        "error": "loader.py 缺少类定义。文件没有被改。",
                    }
                (dest / "loader.py").write_text(
                    loader_body if loader_body.endswith("\n") else loader_body + "\n",
                    encoding="utf-8",
                )
                written.append("loader.py")
            if contract_body.strip():
                syntax = cls._syntax_error(contract_body, "contract.py")
                if syntax:
                    return {"ok": False, "key": parsed, "error": syntax}
                (dest / "contract.py").write_text(
                    contract_body
                    if contract_body.endswith("\n")
                    else contract_body + "\n",
                    encoding="utf-8",
                )
                written.append("contract.py")
        except OSError:
            return {"ok": False, "error": f"无法写入 {relative} 下的契约文件"}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "files": written,
            "note": "文件已覆盖。接着 apply_user_data_key（若尚未登记），再 validate_user_contract。",
        }

    @classmethod
    def apply_user_data_key(
        cls,
        *,
        const_name: str,
        data_key: str,
    ) -> Dict[str, Any]:
        const = str(const_name or "").strip()
        dk = str(data_key or "").strip()
        if not const:
            return {"ok": False, "error": "const_name 不能为空"}
        if not _CONST_RE.match(const):
            return {"ok": False, "error": f"const_name 不合法: {const}（须 SCREAMING_SNAKE）"}
        if not dk:
            return {"ok": False, "error": "data_key 不能为空"}
        if not _DATA_KEY_RE.match(dk):
            return {
                "ok": False,
                "error": f"data_key 不合法: {dk}。须为点分小写段，如 my.custom.data",
            }

        path = ProjectContext.path.get_data_contract_root() / "data_keys.py"
        if not path.is_file():
            return {"ok": False, "error": f"data_keys.py 不存在: {path}"}

        current = cls._load_user_data_key_map(path)
        if current is None:
            return {"ok": False, "error": "无法加载 USER_DATA_KEY"}

        for existing_const, existing_val in current.items():
            if existing_const == const:
                if existing_val == dk:
                    return {
                        "ok": True,
                        "const_name": const,
                        "data_key": dk,
                        "unchanged": True,
                        "note": "USER_DATA_KEY 已含相同条目。",
                    }
                return {
                    "ok": False,
                    "error": (
                        f"常量 {const} 已存在且值为 {existing_val!r}，"
                        f"与请求 {dk!r} 冲突"
                    ),
                }
            if existing_val == dk and existing_const != const:
                return {
                    "ok": False,
                    "error": (
                        f"data_key {dk!r} 已被 {existing_const} 占用"
                    ),
                }

        merged = dict(current)
        merged[const] = dk
        try:
            text = path.read_text(encoding="utf-8")
            new_text = cls._replace_user_data_key_class(text, merged)
            path.write_text(new_text, encoding="utf-8")
        except Exception as exc:
            return {"ok": False, "error": f"无法写入 data_keys.py: {exc}"}

        return {
            "ok": True,
            "const_name": const,
            "data_key": dk,
            "note": "已写入 USER_DATA_KEY。接着 validate_user_contract。",
        }

    @classmethod
    def validate(cls, *, key: str, reload: bool = True) -> Dict[str, Any]:
        parsed = cls._normalize_folder_key(key)
        if isinstance(parsed, dict):
            return parsed
        dest, relative = cls._folder(parsed)
        decl_file = dest / "declaration.py"
        loader_file = dest / "loader.py"
        if not decl_file.is_file() or not loader_file.is_file():
            return {
                "ok": False,
                "key": parsed,
                "errors": [f"契约文件不齐: {relative}。需要 declaration.py 和 loader.py"],
            }

        errors: List[str] = []
        for label, path in (("declaration.py", decl_file), ("loader.py", loader_file)):
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
            return {"ok": False, "key": parsed, "errors": cls._unique(errors)}

        keys_path = ProjectContext.path.get_data_contract_root() / "data_keys.py"
        user_keys = cls._load_user_data_key_map(keys_path) or {}
        registered_values = set(user_keys.values())

        try:
            decl_mod = cls._load_py_module(decl_file, f"user_contract_decl_{parsed.replace('/', '_')}")
        except Exception as exc:
            return {
                "ok": False,
                "key": parsed,
                "errors": [f"导入 declaration.py 失败: {exc}"],
            }

        declarations: List[tuple[str, Dict[str, Any], str]] = []
        for attr_name in dir(decl_mod):
            if not attr_name.endswith("_DECLARATION") or attr_name.startswith("_"):
                continue
            decl = getattr(decl_mod, attr_name)
            if not isinstance(decl, dict):
                errors.append(f"{attr_name} 不是 dict")
                continue
            meta_errors = cls._validate_meta(decl)
            if meta_errors:
                errors.extend(meta_errors)
                continue
            meta = decl.get("meta") or {}
            data_key = str(meta.get("key") or "").strip()
            if not data_key:
                errors.append(f"{attr_name}: 缺少 meta.key")
                continue
            if data_key not in registered_values:
                errors.append(
                    f"data_key {data_key!r} 未在 USER_DATA_KEY 中登记。"
                    "请先 apply_user_data_key"
                )
                continue
            declarations.append((data_key, decl, attr_name))

        if not declarations and not errors:
            errors.append("declaration.py 未找到有效的 *_DECLARATION")

        try:
            loader_mod = cls._load_py_module(
                loader_file, f"user_contract_loader_{parsed.replace('/', '_')}"
            )
        except Exception as exc:
            return {
                "ok": False,
                "key": parsed,
                "errors": cls._unique(errors + [f"导入 loader.py 失败: {exc}"]),
            }

        from core.modules.data_contract.contracts import BaseDataContractLoader

        loader_classes = [
            attr
            for attr_name in dir(loader_mod)
            for attr in [getattr(loader_mod, attr_name)]
            if isinstance(attr, type)
            and issubclass(attr, BaseDataContractLoader)
            and attr is not BaseDataContractLoader
        ]
        if not loader_classes:
            errors.append("loader.py 中没有找到继承 BaseDataContractLoader 的类")

        if errors:
            return {"ok": False, "key": parsed, "errors": cls._unique(errors)}

        primary_key = declarations[0][0]
        discovered = False
        if reload:
            try:
                from core.modules.data_contract import ContractIssuer

                ContractIssuer.reload(
                    user_space_path=ProjectContext.path.get_data_contract_root()
                )
                issuer = ContractIssuer()
                issuer.discover(
                    user_space_path=ProjectContext.path.get_data_contract_root()
                )
                discovered = primary_key in set(issuer.list_available_keys())
                if not discovered:
                    verr = issuer.get_validation_errors()
                    folder_errs = verr.get(Path(parsed).name) or verr.get(parsed) or []
                    if folder_errs:
                        errors.extend(str(x) for x in folder_errs)
                    else:
                        errors.append(
                            f"reload 后仍未发现 data_key: {primary_key}"
                        )
            except Exception as exc:
                errors.append(f"reload/discover 失败: {exc}")

        if errors:
            return {"ok": False, "key": parsed, "errors": cls._unique(errors)}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "data_key": primary_key,
            "declarations": [name for _, _, name in declarations],
            "loader_class": getattr(loader_classes[0], "__name__", "") or "",
            "reloaded": bool(reload),
            "discovered": discovered if reload else None,
            "note": (
                "校验通过并已 reload。"
                if reload
                else "结构校验通过。需要生效时再 ContractIssuer.reload()。"
            ),
        }

    @classmethod
    def describe(cls, *, data_key: str) -> Dict[str, Any]:
        name = str(data_key or "").strip()
        if not name:
            return {"ok": False, "error": "data_key 不能为空"}
        try:
            from core.modules.data_contract import ContractIssuer

            issuer = ContractIssuer()
            issuer.discover()
            if not issuer.is_available(name):
                return {"ok": False, "error": f"未发现契约: {name}"}
            decl = issuer.get_declaration(name)
        except Exception as exc:
            return {"ok": False, "error": f"无法读取契约: {exc}"}
        meta = decl.get("meta") if isinstance(decl.get("meta"), dict) else {}
        return {
            "ok": True,
            "data_key": name,
            "type": meta.get("type"),
            "scope": meta.get("scope"),
            "display_name": meta.get("display_name"),
            "list_data_key": meta.get("list_data_key"),
            "is_customized": bool(decl.get("_is_customized", False)),
            "note": "只读摘要。userspace 契约改文件后须 validate/reload。",
        }

    @classmethod
    def default_data_key(cls, folder_key: str) -> str:
        leaf = Path(str(folder_key).replace("\\", "/")).name
        parts = [p for p in re.split(r"[^a-zA-Z0-9]+", leaf.lower()) if p]
        if len(parts) >= 2:
            return ".".join(parts)
        if len(parts) == 1:
            return f"user.{parts[0]}"
        return "user.custom.data"

    @classmethod
    def const_name_for(cls, data_key: str) -> str:
        parts = [p for p in str(data_key).split(".") if p]
        return "_".join(p.upper() for p in parts) if parts else "USER_CUSTOM_DATA"

    @classmethod
    def is_valid_folder_key(cls, relative_path: str) -> bool:
        text = str(relative_path or "").strip().strip("/")
        if not text or text.startswith("_"):
            return False
        segments = [seg for seg in text.split("/") if seg]
        if not segments or any(seg.startswith("_") for seg in segments):
            return False
        if any(seg in _TEMPLATE_DIRS for seg in segments):
            return False
        return all(bool(_PATH_SEGMENT_RE.match(seg)) for seg in segments)

    @classmethod
    def _normalize_folder_key(cls, key: str) -> str | Dict[str, Any]:
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
        root = ProjectContext.path.get_data_contract_root().resolve()
        dest = (root / key).resolve()
        if not dest.is_relative_to(root) or dest == root:
            raise ValueError(
                f"路径必须在 userspace/extensions/data_contract 下: {key}"
            )
        relative = f"extensions/data_contract/{key}"
        return dest, relative

    @classmethod
    def _rewrite_placeholders(
        cls,
        dest: Path,
        *,
        const_name: str,
        data_key: str,
        contract_type: str,
        scope: str,
        list_data_key: str,
        display_name: str,
        loader_class: str,
    ) -> None:
        decl = dest / "declaration.py"
        loader = dest / "loader.py"
        if not decl.is_file() or not loader.is_file():
            raise ValueError(f"模板复制后文件不齐: {dest}")

        # 骨架用字符串 meta.key，避免尚未 apply_user_data_key 时导入失败；
        # 登记后可再 write 成 USER_DATA_KEY.CONST。
        list_line = (
            f'\n        "list_data_key": {list_data_key!r},'
            if scope == "per_entity" and list_data_key
            else ""
        )
        decl.write_text(
            (
                f'"""Userspace data contract: {display_name}.\n\n'
                f"登记：apply_user_data_key(const_name={const_name!r}, data_key={data_key!r})\n"
                f'"""\n\n'
                f"{const_name}_DECLARATION = {{\n"
                f'    "meta": {{\n'
                f'        "key": {data_key!r},\n'
                f'        "type": {contract_type!r},\n'
                f'        "scope": {scope!r},{list_line}\n'
                f'        "display_name": {display_name!r},\n'
                f'        "description": {display_name!r},\n'
                f'        "loader": None,\n'
                f"    }},\n"
                f'    "params": {{}},\n'
                f'    "specific": {{}},\n'
                f"}}\n\n"
                f"__all__ = ['{const_name}_DECLARATION']\n"
            ),
            encoding="utf-8",
        )

        loader_text = loader.read_text(encoding="utf-8")
        if "MyCustomDataLoader" not in loader_text:
            raise ValueError("模板 loader.py 缺少 MyCustomDataLoader 占位")
        loader.write_text(
            loader_text.replace("MyCustomDataLoader", loader_class),
            encoding="utf-8",
        )
        _ = data_key

    @staticmethod
    def _loader_class_name(folder_key: str) -> str:
        leaf = Path(str(folder_key).replace("\\", "/")).name
        parts = [p for p in re.split(r"[^a-zA-Z0-9]+", leaf) if p]
        if not parts:
            return "CustomDataLoader"
        return "".join(p[:1].upper() + p[1:] for p in parts) + "Loader"

    @classmethod
    def _validate_meta(cls, declaration: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        meta = declaration.get("meta")
        if not meta:
            return ["缺少 meta 字段"]
        if not isinstance(meta, dict):
            return ["meta 必须是 dict"]
        for field in ("key", "type", "scope"):
            if field not in meta:
                errors.append(f"meta 缺少必要字段: {field}")
        if "type" in meta and meta["type"] not in VALID_TYPES:
            errors.append(
                f"meta.type 值无效: {meta['type']}，必须是 {sorted(VALID_TYPES)}"
            )
        if "scope" in meta and meta["scope"] not in VALID_SCOPES:
            errors.append(
                f"meta.scope 值无效: {meta['scope']}，必须是 {sorted(VALID_SCOPES)}"
            )
        if meta.get("scope") == "per_entity":
            if not str(meta.get("list_data_key") or "").strip():
                errors.append(
                    "meta.scope=per_entity 时必须提供 meta.list_data_key"
                )
        return errors

    @classmethod
    def _load_user_data_key_map(cls, path: Path) -> Optional[Dict[str, str]]:
        if not path.is_file():
            return None
        try:
            module = cls._load_py_module(path, "user_data_keys_ops")
            klass = getattr(module, "USER_DATA_KEY", None)
            if klass is None:
                return None
            out: Dict[str, str] = {}
            for name in dir(klass):
                if name.startswith("_"):
                    continue
                value = getattr(klass, name)
                if isinstance(value, str):
                    out[name] = value
            return out
        except Exception:
            return None

    @classmethod
    def _replace_user_data_key_class(
        cls, text: str, mapping: Dict[str, str]
    ) -> str:
        idx = text.find("class USER_DATA_KEY")
        if idx < 0:
            raise ValueError("data_keys.py 缺少 class USER_DATA_KEY")
        # Keep prefix (docstring / imports); rewrite from class to EOF or next top-level.
        lines = [
            "class USER_DATA_KEY:",
            '    """用户自定义数据键值（枚举常量）。"""',
            "",
        ]
        for const, value in mapping.items():
            lines.append(f"    {const} = {value!r}")
        lines.append("")
        lines.append("__all__ = ['USER_DATA_KEY']")
        lines.append("")
        # Preserve module docstring / leading comments before class
        prefix = text[:idx].rstrip() + "\n\n"
        return prefix + "\n".join(lines)

    @staticmethod
    def _load_py_module(path: Path, module_name: str) -> Any:
        # Drop stale module so edits are visible in-process.
        sys.modules.pop(module_name, None)
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

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
