"""Userspace 序列关系脚手架 / 写 settings / 校验（域逻辑；信道只传参）。"""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.modules.series_relation.core.constants import SETTINGS_FILE_NAME
from core.modules.series_relation.core.persist.settings_io import write_settings_py
from core.modules.series_relation.core.settings.relation_settings import validate_settings

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "README.md")
_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
_TEMPLATE_REL = Path("_template") / "empty_relation"
KEY_RULE = "每段以字母开头，仅含字母、数字、下划线；勿用 _ 开头；勿用模板目录名"


class UserSeriesRelationOps:
    """_template/empty_relation → userspace series_relation；无独立 register（发现即注册）。"""

    @classmethod
    def scaffold(
        cls,
        *,
        key: str,
        display_name: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed

        dest, relative = cls._folder(parsed)
        if dest.exists():
            return {"ok": False, "error": f"目标已存在: {relative}"}

        root = ProjectContext.path.get_series_relation_root()
        template = (root / _TEMPLATE_REL).resolve()
        if not template.is_dir():
            return {
                "ok": False,
                "error": "序列关系模板不存在: extensions/series_relation/_template/empty_relation",
            }

        meta_key = Path(parsed).name
        title = str(display_name or "").strip() or meta_key
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template, dest, ignore=_IGNORE)
            settings_file = dest / SETTINGS_FILE_NAME
            cls._rewrite_meta(settings_file, meta_key=meta_key, display_name=title)
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建序列关系目录: {exc}"}
        except ValueError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "meta_key": meta_key,
            "files": [SETTINGS_FILE_NAME],
            "note": (
                f"已生成骨架，meta.key={meta_key}。"
                "接着 write_user_series_relation_settings 改 series，再 validate_user_series_relation。"
            ),
        }

    @classmethod
    def write_settings(
        cls,
        *,
        key: str,
        settings_py: str = "",
    ) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        dest, relative = cls._folder(parsed)
        if not dest.is_dir():
            return {
                "ok": False,
                "error": f"序列关系不存在: {relative}。请先 scaffold_user_series_relation",
            }
        if any(seg.startswith("_") for seg in Path(parsed).parts):
            return {"ok": False, "error": f"拒绝写入模板/私有目录: {relative}"}

        body = str(settings_py or "")
        if not body.strip():
            return {"ok": False, "error": "必须提供 settings_py"}

        syntax = cls._syntax_error(body, SETTINGS_FILE_NAME)
        if syntax:
            return {"ok": False, "key": parsed, "error": syntax}
        shape = cls._settings_shape_error(body)
        if shape:
            return {"ok": False, "key": parsed, "error": shape}

        # 强制 meta.key 与目录叶名一致（与 SeriesRelation.save 对齐）
        leaf = Path(parsed).name
        try:
            settings = cls._load_settings_dict(body)
            if settings is None:
                return {
                    "ok": False,
                    "key": parsed,
                    "error": "settings.py 须含 settings = { ... }。文件没有被改。",
                }
            meta = dict(settings.get("meta") or {})
            meta["key"] = leaf
            if not str(meta.get("display_name") or "").strip():
                meta["display_name"] = leaf
            settings["meta"] = meta
            write_settings_py(dest / SETTINGS_FILE_NAME, settings)
        except OSError:
            return {"ok": False, "error": f"无法写入 {relative}/settings.py"}
        except Exception as exc:
            return {"ok": False, "key": parsed, "error": f"写入失败: {exc}"}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "files": [SETTINGS_FILE_NAME],
            "note": "settings.py 已覆盖（meta.key 已对齐目录）。接着 validate_user_series_relation。",
        }

    @classmethod
    def validate(cls, *, key: str) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        dest, relative = cls._folder(parsed)
        settings_file = dest / SETTINGS_FILE_NAME
        if not settings_file.is_file():
            return {
                "ok": False,
                "key": parsed,
                "errors": [f"缺少 {SETTINGS_FILE_NAME}: {relative}"],
            }

        errors: List[str] = []
        try:
            source = settings_file.read_text(encoding="utf-8")
            ast.parse(source, filename=SETTINGS_FILE_NAME)
        except SyntaxError as exc:
            return {
                "ok": False,
                "key": parsed,
                "errors": [
                    f"{SETTINGS_FILE_NAME} 语法错误: 第 {exc.lineno or '?'} 行: {exc.msg}"
                ],
            }
        except Exception as exc:
            return {"ok": False, "key": parsed, "errors": [f"无法读取 settings.py: {exc}"]}

        loaded = Discovery.file.load_python_config(
            settings_file, var_name="settings"
        )
        if not isinstance(loaded, dict):
            return {
                "ok": False,
                "key": parsed,
                "errors": ["settings.py 须定义 settings = {...}"],
            }

        leaf = Path(parsed).name
        meta = dict(loaded.get("meta") or {}) if isinstance(loaded.get("meta"), dict) else {}
        if str(meta.get("key") or "").strip() != leaf:
            errors.append(
                f"meta.key={meta.get('key')!r} 须等于目录叶名 {leaf!r}"
            )

        from core.modules.series_relation import SeriesRelation

        normalized, v_errors = validate_settings(
            loaded,
            declaration_lookup=SeriesRelation._declaration_lookup(),
        )
        errors.extend(v_errors)
        if errors:
            return {"ok": False, "key": parsed, "errors": cls._unique(errors)}

        return {
            "ok": True,
            "key": parsed,
            "path": relative,
            "meta_key": leaf,
            "display_name": (normalized or {}).get("meta", {}).get("display_name")
            or leaf,
            "series_count": len((normalized or {}).get("series") or []),
            "note": "校验通过。可用 SeriesRelation.run / cli srel 跑批。",
        }

    @classmethod
    def describe(cls, *, key: str) -> Dict[str, Any]:
        parsed = cls._normalize_key(key)
        if isinstance(parsed, dict):
            return parsed
        from core.modules.series_relation import SeriesRelation

        info = SeriesRelation.find(parsed) or SeriesRelation.find(Path(parsed).name)
        if info is None:
            return {"ok": False, "error": f"未发现序列关系: {parsed}"}
        settings = info.settings if isinstance(info.settings, dict) else {}
        meta = settings.get("meta") if isinstance(settings.get("meta"), dict) else {}
        series = settings.get("series") if isinstance(settings.get("series"), list) else []
        return {
            "ok": True,
            "key": info.key,
            "path": f"extensions/series_relation/{info.relative_path}",
            "display_name": str(meta.get("display_name") or info.key),
            "series_count": len(series),
            "normalize": settings.get("normalize"),
            "fill": settings.get("fill"),
            "analyze": settings.get("analyze"),
            "note": "只读摘要。改 settings 后须 validate_user_series_relation。",
        }

    @classmethod
    def list_summaries(cls) -> Dict[str, Any]:
        from core.modules.series_relation import SeriesRelation

        try:
            infos = SeriesRelation.list_infos()
        except Exception as exc:
            return {"ok": False, "error": f"无法列出序列关系: {exc}"}
        rows: List[Dict[str, Any]] = []
        for info in infos:
            settings = info.settings if isinstance(info.settings, dict) else {}
            meta = settings.get("meta") if isinstance(settings.get("meta"), dict) else {}
            series = settings.get("series") if isinstance(settings.get("series"), list) else []
            rows.append(
                {
                    "key": info.key,
                    "display_name": str(meta.get("display_name") or info.key),
                    "path": info.relative_path,
                    "series_count": len(series),
                }
            )
        return {"ok": True, "relations": rows, "count": len(rows)}

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
        root = ProjectContext.path.get_series_relation_root().resolve()
        dest = (root / key).resolve()
        if not dest.is_relative_to(root) or dest == root:
            raise ValueError(
                f"路径必须在 userspace/extensions/series_relation 下: {key}"
            )
        relative = f"extensions/series_relation/{key}"
        return dest, relative

    @classmethod
    def _rewrite_meta(
        cls, settings_file: Path, *, meta_key: str, display_name: str
    ) -> None:
        if not settings_file.is_file():
            raise ValueError(f"模板复制后缺少 {SETTINGS_FILE_NAME}")
        text = settings_file.read_text(encoding="utf-8")
        text, n_key = re.subn(
            r'("key"\s*:\s*")[^"]*(")',
            rf"\g<1>{meta_key}\g<2>",
            text,
            count=1,
        )
        text, n_name = re.subn(
            r'("display_name"\s*:\s*")[^"]*(")',
            rf"\g<1>{display_name}\g<2>",
            text,
            count=1,
        )
        if n_key != 1:
            raise ValueError("无法写入 meta.key")
        if n_name != 1:
            raise ValueError("无法写入 meta.display_name")
        settings_file.write_text(text, encoding="utf-8")

    @classmethod
    def _settings_shape_error(cls, body: str) -> str:
        if cls._load_settings_dict(body) is None:
            return (
                "settings.py 必须是 Python，含全局变量 settings = { ... }。"
                "须含 meta.key 与非空 series。文件没有被改。"
            )
        return ""

    @staticmethod
    def _load_settings_dict(body: str) -> Optional[Dict[str, Any]]:
        try:
            tree = ast.parse(body)
        except SyntaxError:
            return None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "settings":
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
