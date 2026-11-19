"""Userspace Adapter / PostProcessor 脚手架与校验（域逻辑；信道只传参）。"""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

from core.infra.project_context import ProjectContext

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "README.md")
_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
KEY_RULE = "每段以字母开头，仅含字母、数字、下划线；勿用 _ 开头"


class UserPostProcessOps:
    """adapters/_template/empty_adapter + post_processors/_template；发现即注册。"""

    # ------------------------------------------------------------------
    # Adapter
    # ------------------------------------------------------------------

    @classmethod
    def scaffold_adapter(
        cls,
        *,
        name: str,
        display_name: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(name)
        if isinstance(parsed, dict):
            return parsed

        root = ProjectContext.path.get_adapters_directory()
        dest = (root / parsed).resolve()
        relative = f"extensions/post_process/adapters/{parsed}"
        if not dest.is_relative_to(root.resolve()) or dest == root.resolve():
            return {"ok": False, "error": f"路径非法: {parsed}"}
        if dest.exists():
            return {"ok": False, "error": f"目标已存在: {relative}"}

        template = (
            ProjectContext.path.get_post_process_extensions_directory()
            / "_template"
            / "empty_adapter"
        )
        if not template.is_dir():
            return {
                "ok": False,
                "error": "Adapter 模板不存在: extensions/post_process/_template/empty_adapter",
            }

        class_name = cls._adapter_class_name(parsed)
        title = str(display_name or "").strip() or parsed
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template, dest, ignore=_IGNORE)
            cls._rewrite_adapter_placeholders(
                dest, class_name=class_name, display_name=title
            )
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建 adapter 目录: {exc}"}
        except ValueError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

        return {
            "ok": True,
            "name": parsed,
            "path": relative,
            "adapter_class": class_name,
            "files": ["adapter.py", "settings.py"],
            "note": (
                f"已生成 Adapter 骨架（{class_name}）。"
                "接着 write_user_adapter_files，再 validate_user_adapter；"
                "要用扫描后处理还需 scaffold/write post_processor 并 is_enabled。"
            ),
        }

    @classmethod
    def write_adapter_files(
        cls,
        *,
        name: str,
        adapter_py: str = "",
        settings_py: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(name)
        if isinstance(parsed, dict):
            return parsed
        root = ProjectContext.path.get_adapters_directory().resolve()
        dest = (root / parsed).resolve()
        relative = f"extensions/post_process/adapters/{parsed}"
        if not dest.is_dir() or not dest.is_relative_to(root):
            return {
                "ok": False,
                "error": f"adapter 不存在: {relative}。请先 scaffold_user_adapter",
            }
        if parsed.startswith("_"):
            return {"ok": False, "error": f"拒绝写入模板/私有目录: {relative}"}

        adapter_body = str(adapter_py or "")
        settings_body = str(settings_py or "")
        if not adapter_body.strip() and not settings_body.strip():
            return {"ok": False, "error": "至少提供 adapter_py、settings_py 之一"}

        written: List[str] = []
        try:
            if adapter_body.strip():
                syntax = cls._syntax_error(adapter_body, "adapter.py")
                if syntax:
                    return {"ok": False, "name": parsed, "error": syntax}
                lint = cls._adapter_source_lint(adapter_body)
                if lint:
                    return {"ok": False, "name": parsed, "error": lint}
                (dest / "adapter.py").write_text(
                    adapter_body if adapter_body.endswith("\n") else adapter_body + "\n",
                    encoding="utf-8",
                )
                written.append("adapter.py")
            if settings_body.strip():
                syntax = cls._syntax_error(settings_body, "settings.py")
                if syntax:
                    return {"ok": False, "name": parsed, "error": syntax}
                if "settings" not in settings_body and "config" not in settings_body:
                    return {
                        "ok": False,
                        "name": parsed,
                        "error": "settings.py 须含 settings 或 config 字典。文件没有被改。",
                    }
                (dest / "settings.py").write_text(
                    settings_body
                    if settings_body.endswith("\n")
                    else settings_body + "\n",
                    encoding="utf-8",
                )
                written.append("settings.py")
        except OSError:
            return {"ok": False, "error": f"无法写入 {relative}"}

        return {
            "ok": True,
            "name": parsed,
            "path": relative,
            "files": written,
            "note": "文件已覆盖。接着 validate_user_adapter。",
        }

    @classmethod
    def validate_adapter(cls, *, name: str) -> Dict[str, Any]:
        parsed = cls._normalize_key(name)
        if isinstance(parsed, dict):
            return parsed
        root = ProjectContext.path.get_adapters_directory().resolve()
        dest = (root / parsed).resolve()
        relative = f"extensions/post_process/adapters/{parsed}"
        adapter_file = dest / "adapter.py"
        if not adapter_file.is_file():
            return {
                "ok": False,
                "name": parsed,
                "errors": [f"缺少 adapter.py: {relative}"],
            }

        errors: List[str] = []
        try:
            source = adapter_file.read_text(encoding="utf-8")
            ast.parse(source, filename="adapter.py")
            lint = cls._adapter_source_lint(source)
            if lint:
                errors.append(lint)
        except SyntaxError as exc:
            errors.append(f"adapter.py 语法错误: 第 {exc.lineno or '?'} 行: {exc.msg}")
        except Exception as exc:
            errors.append(f"无法读取 adapter.py: {exc}")

        if errors:
            return {"ok": False, "name": parsed, "errors": cls._unique(errors)}

        from core.modules.post_process.core.adapter_validator import AdapterValidator

        ok, err = AdapterValidator.validate(parsed)
        if not ok:
            return {
                "ok": False,
                "name": parsed,
                "errors": [err or "AdapterValidator 失败"],
            }
        return {
            "ok": True,
            "name": parsed,
            "path": relative,
            "note": "校验通过。可在 post_processor.yaml 的 adapters 中引用。",
        }

    # ------------------------------------------------------------------
    # PostProcessor
    # ------------------------------------------------------------------

    @classmethod
    def scaffold_post_processor(
        cls,
        *,
        key: str,
        name: str = "",
        adapter_name: str = "",
        is_enabled: bool = False,
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed

        root = ProjectContext.path.get_post_processors_directory()
        dest = (root / parsed).resolve()
        relative = f"extensions/post_process/post_processors/{parsed}"
        if not dest.is_relative_to(root.resolve()) or dest == root.resolve():
            return {"ok": False, "error": f"路径非法: {parsed}"}
        if dest.exists() or (root / f"{parsed}.yaml").exists():
            return {"ok": False, "error": f"目标已存在: {relative}"}

        template = (
            ProjectContext.path.get_post_process_extensions_directory()
            / "_template"
            / "empty_post_processor"
            / "post_processor.yaml"
        )
        if not template.is_file():
            return {
                "ok": False,
                "error": (
                    "PostProcessor 模板不存在: "
                    "extensions/post_process/_template/empty_post_processor"
                ),
            }

        title = str(name or "").strip() or parsed
        adapter_ref = str(adapter_name or "").strip()
        try:
            dest.mkdir(parents=True, exist_ok=False)
            raw = yaml.safe_load(template.read_text(encoding="utf-8")) or {}
            if not isinstance(raw, dict):
                raw = {}
            raw["key"] = parsed
            raw["name"] = title
            raw["is_enabled"] = bool(is_enabled)
            if adapter_ref:
                raw["adapters"] = {adapter_ref: {"config": {}}}
            else:
                raw.setdefault("adapters", {})
            out_path = dest / "post_processor.yaml"
            out_path.write_text(
                yaml.safe_dump(raw, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建 post_processor: {exc}"}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "files": ["post_processor.yaml"],
            "is_enabled": bool(is_enabled),
            "note": (
                "已生成 PostProcessor 骨架（默认 is_enabled=false）。"
                "接着 write_user_post_processor_yaml 挂 adapters，再 validate_user_post_processor。"
            ),
        }

    @classmethod
    def write_post_processor_yaml(
        cls,
        *,
        key: str,
        yaml_body: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        root = ProjectContext.path.get_post_processors_directory().resolve()
        dest_dir = (root / parsed).resolve()
        relative = f"extensions/post_process/post_processors/{parsed}"
        body = str(yaml_body or "")
        if not body.strip():
            return {"ok": False, "error": "必须提供 yaml_body"}

        try:
            raw = yaml.safe_load(body)
        except Exception as exc:
            return {"ok": False, "key": parsed, "error": f"YAML 解析失败: {exc}"}
        if not isinstance(raw, dict):
            return {"ok": False, "key": parsed, "error": "YAML 根须为对象"}

        raw["key"] = parsed
        if "adapters" not in raw or not isinstance(raw.get("adapters"), dict):
            return {
                "ok": False,
                "key": parsed,
                "error": "须含 adapters 对象（可先为空 dict）。文件没有被改。",
            }

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            path = dest_dir / "post_processor.yaml"
            path.write_text(
                yaml.safe_dump(raw, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        except OSError as exc:
            return {"ok": False, "error": f"无法写入 {relative}: {exc}"}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "files": ["post_processor.yaml"],
            "note": "YAML 已覆盖（key 已对齐目录）。接着 validate_user_post_processor。",
        }

    @classmethod
    def validate_post_processor(cls, *, key: str) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        from core.modules.post_process.core.post_processor_validator import (
            PostProcessorValidator,
        )

        ok, err = PostProcessorValidator.validate(parsed)
        if not ok:
            return {
                "ok": False,
                "key": parsed,
                "errors": [err or "PostProcessorValidator 失败"],
            }
        return {
            "ok": True,
            "key": parsed,
            "path": f"extensions/post_process/post_processors/{parsed}",
            "note": "校验通过。is_enabled=true 时扫描结束后会自动跑。",
        }

    @classmethod
    def describe_adapter(cls, *, name: str) -> Dict[str, Any]:
        parsed = cls._normalize_key(name)
        if isinstance(parsed, dict):
            return parsed
        from core.modules.post_process import PostProcess

        summary = PostProcess.summarize_adapter(parsed)
        if not summary:
            return {"ok": False, "error": f"未发现 adapter: {parsed}"}
        return {"ok": True, "adapter": summary}

    @classmethod
    def describe_post_processor(cls, *, key: str) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        from core.modules.post_process import PostProcess

        summary = PostProcess.summarize_post_processor(parsed)
        if not summary:
            return {"ok": False, "error": f"未发现 post_processor: {parsed}"}
        return {"ok": True, "post_processor": summary}

    @classmethod
    def list_adapter_summaries(cls) -> Dict[str, Any]:
        from core.modules.post_process import PostProcess

        try:
            rows = PostProcess.list_adapter_summaries()
        except Exception as exc:
            return {"ok": False, "error": f"无法列出 adapters: {exc}"}
        return {"ok": True, "adapters": rows, "count": len(rows)}

    @classmethod
    def list_post_processor_summaries(cls) -> Dict[str, Any]:
        from core.modules.post_process import PostProcess

        try:
            rows = PostProcess.list_post_processor_summaries()
        except Exception as exc:
            return {"ok": False, "error": f"无法列出 post_processors: {exc}"}
        return {"ok": True, "post_processors": rows, "count": len(rows)}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @classmethod
    def is_valid_folder_key(cls, relative_path: str) -> bool:
        text = str(relative_path or "").strip().strip("/")
        if not text or text.startswith("_") or "/" in text or "\\" in text:
            return False
        return bool(_PATH_SEGMENT_RE.match(text))

    @classmethod
    def _normalize_key(cls, key: str) -> str | Dict[str, Any]:
        text = str(key or "").strip().strip("/")
        if not text:
            return {"ok": False, "error": "key 不能为空"}
        if not cls.is_valid_folder_key(text):
            return {"ok": False, "error": f"名称不合法：{text}。{KEY_RULE}（单段，无斜杠）"}
        return text

    @staticmethod
    def _adapter_class_name(name: str) -> str:
        parts = [p for p in re.split(r"[^a-zA-Z0-9]+", name) if p]
        if not parts:
            return "CustomAdapter"
        return "".join(p[:1].upper() + p[1:] for p in parts) + "Adapter"

    @classmethod
    def _rewrite_adapter_placeholders(
        cls, dest: Path, *, class_name: str, display_name: str
    ) -> None:
        adapter = dest / "adapter.py"
        settings = dest / "settings.py"
        if not adapter.is_file():
            raise ValueError("模板复制后缺少 adapter.py")
        text = adapter.read_text(encoding="utf-8")
        if "EmptyAdapter" not in text:
            raise ValueError("模板 adapter.py 缺少 EmptyAdapter 占位")
        adapter.write_text(text.replace("EmptyAdapter", class_name), encoding="utf-8")
        if settings.is_file():
            s = settings.read_text(encoding="utf-8")
            s, n = re.subn(
                r'("display_name"\s*:\s*")[^"]*(")',
                rf"\g<1>{display_name}\g<2>",
                s,
                count=1,
            )
            if n == 1:
                settings.write_text(s, encoding="utf-8")

    @classmethod
    def _adapter_source_lint(cls, body: str) -> str:
        if "BaseAdapter" not in body:
            return "adapter.py 须继承 BaseAdapter。文件没有被改。"
        if "class " not in body:
            return "adapter.py 缺少类定义。文件没有被改。"
        if re.search(r"\bdef\s+run\s*\(", body) is None:
            return "adapter.py 须实现 run(...)。文件没有被改。"
        return ""

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
