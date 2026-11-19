"""Strategy 用例：scaffold / apply_settings_patch / validate_artifact。"""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
_TEMPLATE_REL = Path("_template") / "empty_strategy"
_CONTRACTS = (
    "from core.modules.strategy.contracts import Records, StrategyContext, StrategyHooks"
)


class StrategyArtifactOps:
    """userspace 策略制品编排；信道只传参。"""

    @classmethod
    def scaffold_from_template(cls, raw_path: str) -> Dict[str, Any]:
        try:
            dest, key = cls._resolve_dest(raw_path)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        root = ProjectContext.path.get_strategies_root().resolve()
        template = (root / _TEMPLATE_REL).resolve()
        if not template.is_dir():
            return {
                "ok": False,
                "error": "策略模板不存在: strategies/_template/empty_strategy",
            }
        if dest.exists():
            return {"ok": False, "error": f"目标已存在: {dest}"}

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template, dest, ignore=_IGNORE)
            settings = dest / "settings.py"
            cls._enable_in_settings(settings)
            cls._set_meta_key(settings, key)
        except OSError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": f"无法创建策略目录: {exc}"}
        except ValueError as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

        relative = f"strategies/{key}"
        return {
            "ok": True,
            "key": key,
            "path": relative,
            "dest": str(dest),
            "meta_key": key,
            "files": ["strategy.py", "settings.py"],
            "note": f"仍是空模板，meta.key 已写成 {key}",
        }

    @classmethod
    def apply_settings_patch(
        cls,
        *,
        key: str,
        strategy_py: str = "",
        settings_py: str = "",
        attribution_py: str = "",
    ) -> Dict[str, Any]:
        try:
            folder, relative = cls._folder_for_key(key)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        if not folder.is_dir():
            return {
                "ok": False,
                "error": f"策略不存在: {relative}。请先 scaffold_from_template",
            }

        if not any(
            str(x or "").strip() for x in (strategy_py, settings_py, attribution_py)
        ):
            return {
                "ok": False,
                "error": "至少提供 strategy_py、settings_py、attribution_py 之一",
            }

        written: List[str] = []
        try:
            if str(strategy_py or "").strip():
                body = cls.normalize_strategy_source(strategy_py)
                sig = cls.lint_strategy_hooks_source(body)
                if sig:
                    return {"ok": False, "key": key, "error": sig}
                (folder / "strategy.py").write_text(body, encoding="utf-8")
                written.append("strategy.py")
            if str(settings_py or "").strip():
                shape = cls._settings_shape_error(settings_py)
                if shape:
                    return {"ok": False, "key": key, "error": shape}
                merged = cls.merge_settings_text(
                    folder / "settings.py", settings_py
                )
                (folder / "settings.py").write_text(merged, encoding="utf-8")
                written.append("settings.py")
            if str(attribution_py or "").strip():
                shape = cls._attribution_shape_error(attribution_py)
                if shape:
                    return {"ok": False, "key": key, "error": shape}
                text = cls._python_literals(attribution_py)
                (folder / "attribution.py").write_text(
                    text if text.endswith("\n") else text + "\n",
                    encoding="utf-8",
                )
                written.append("attribution.py")
        except OSError:
            return {"ok": False, "error": f"无法写入 {relative} 下的策略文件"}

        return {
            "ok": True,
            "key": key,
            "path": relative,
            "files": written,
            "note": "文件已覆盖。接着 validate_artifact，通过之前不要跑回测。",
        }

    @classmethod
    def validate_artifact(cls, *, key: str) -> Dict[str, Any]:
        from core.modules.strategy import Strategy
        from core.modules.strategy.contracts import StrategyHooks

        try:
            folder, relative = cls._folder_for_key(key)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        strategy_file = folder / "strategy.py"
        settings_file = folder / "settings.py"
        if not strategy_file.is_file() or not settings_file.is_file():
            return {
                "ok": False,
                "key": key,
                "errors": [f"策略文件不齐: {relative}。需要 strategy.py 和 settings.py"],
            }

        errors: List[str] = []
        for label, path in (("strategy.py", strategy_file), ("settings.py", settings_file)):
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
                    f"meta.key={meta_key!r} 无法标识本策略"
                    f"（请求 {key}，目录叶名 {leaf}）。"
                    f"meta.key 应等于目录名/叶名，或经发现解析到同一文件夹"
                )
            if settings.get("is_enabled") is not True:
                errors.append("is_enabled 必须为 True，否则不能回测")
        else:
            errors.append(
                cls._scrub(f"无法加载settings.py: {settings}", folder, relative)
            )

        hooks_error, hooks_name = cls._hooks_status(folder, key)
        if hooks_error:
            errors.append(hooks_error)
        bar_access = cls._bar_attribute_access(strategy_file)
        if bar_access:
            errors.append(bar_access)

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
    def normalize_strategy_source(cls, body: str) -> str:
        lines = [line for line in body.splitlines() if "import StrategyHooks" not in line]
        if not any(line.strip() == _CONTRACTS for line in lines):
            insert_at = 0
            for index, line in enumerate(lines):
                if line.startswith("from __future__"):
                    insert_at = index + 1
            lines.insert(insert_at, _CONTRACTS)
        return "\n".join(lines).strip() + "\n"

    @classmethod
    def lint_strategy_hooks_source(cls, body: str) -> str:
        text = str(body or "")
        if "def is_opportunity(self, ctx" in text and "records" in text:
            return ""
        return (
            "is_opportunity 必须写成 def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool。"
            "用 records.last(2)，字段用 dict.get，不要自己构造 Records。文件没有被改。"
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
        base = data.get("base") if isinstance(data, dict) else None
        if isinstance(base, dict) and base.get("data_key") == "stock.kline.daily":
            simulation = rendered.setdefault("simulation", {})
            if isinstance(simulation, dict):
                execution = simulation.setdefault("execution", {})
                if isinstance(execution, dict):
                    execution["mode"] = "entity_based"
            if isinstance(data, dict) and "min_required_records" not in data:
                data["min_required_records"] = 60
        return "settings = " + cls._literal(rendered) + "\n"

    @classmethod
    def _resolve_dest(cls, raw_path: str) -> tuple[Path, str]:
        from core.modules.strategy import Strategy

        text = str(raw_path or "").strip()
        if not text:
            raise ValueError("目标路径不能为空")
        root = ProjectContext.path.get_strategies_root().resolve()
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
        if not Strategy.is_valid_path(key):
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
        from core.modules.strategy import Strategy

        if not Strategy.is_valid_path(text):
            raise ValueError(f"目录名不合法：{text}")
        try:
            folder = Strategy.resolve_folder(text)
            path_id = Strategy.resolve_path(text)
            return folder, f"strategies/{path_id}"
        except (FileNotFoundError, ValueError, OSError):
            root = ProjectContext.path.get_strategies_root().resolve()
            dest = (root / text).resolve()
            if not dest.is_relative_to(root):
                raise ValueError(f"目录名不合法：{text}")
            return dest, f"strategies/{text}"

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
        from core.modules.strategy import Strategy

        needle = str(parsed or "").replace("\\", "/").strip().strip("/")
        leaf = Path(needle).name if needle else ""
        if meta_key in {needle, leaf}:
            return True
        try:
            return Strategy.resolve_folder(meta_key).resolve() == folder.resolve()
        except (FileNotFoundError, ValueError, OSError):
            return False

    @classmethod
    def _hooks_status(cls, folder: Path, key: str) -> tuple[str, str]:
        from core.modules.strategy import Strategy
        from core.modules.strategy.contracts import StrategyHooks

        loaded = Strategy.load_hooks_class(folder, key)
        if loaded is None:
            return cls._hooks_exception(folder, key), ""
        hooks_name, hooks_class = loaded[1], loaded[3]
        if not issubclass(hooks_class, StrategyHooks) or hooks_class is StrategyHooks:
            return "strategy.py 的公开类必须继承 StrategyHooks", ""
        pending = sorted(getattr(hooks_class, "__abstractmethods__", ()))
        if pending:
            return "未实现钩子: " + "、".join(pending), ""
        return "", hooks_name

    @classmethod
    def _hooks_exception(cls, folder: Path, key: str) -> str:
        path = folder / "strategy.py"
        try:
            source = path.read_text(encoding="utf-8")
            compiled = compile(source, "strategy.py", "exec")
            namespace: Dict[str, Any] = {
                "__name__": f"_ntq_validate_strategy_{key.replace('/', '_')}"
            }
            exec(compiled, namespace, namespace)  # noqa: S102
        except Exception as exc:
            return f"无法加载 strategy.py: {exc}"
        return "strategy.py 缺少继承 StrategyHooks 的公开类"

    @staticmethod
    def _bar_attribute_access(path: Path) -> str:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        if ".macd_" in source or ".get(" not in source and "records.last" in source:
            return 'K 线是 dict。用 bar.get("字段")，不要写成 bar.字段'
        return ""

    @classmethod
    def _settings_shape_error(cls, body: str) -> str:
        if cls._dict_from_settings(cls._python_literals(body)) is None:
            return (
                "settings.py 必须是 Python，以 settings = { 开头。"
                "布尔写 True / False。不要写 YAML。"
                "至少包含 is_enabled、meta.key、data.base。"
                "文件没有被改。"
            )
        return ""

    @classmethod
    def _attribution_shape_error(cls, body: str) -> str:
        text = cls._python_literals(body)
        if "attribution" not in text or "{" not in text:
            return "attribution.py 须含 attribution = { ... }。文件没有被改。"
        marker = text.find("attribution")
        start = text.find("{", marker)
        if start < 0:
            return "attribution.py 须含 attribution = { ... }。文件没有被改。"
        try:
            value = ast.literal_eval(text[start:])
        except (SyntaxError, ValueError):
            return "attribution.py 无法解析为字典。文件没有被改。"
        if not isinstance(value, dict):
            return "attribution 必须是字典。文件没有被改。"
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
            return "[" + ", ".join(StrategyArtifactOps._literal(i) for i in value) + "]"
        if isinstance(value, dict):
            if not value:
                return "{}"
            parts = [
                repr(str(k)) + ": " + StrategyArtifactOps._literal(v)
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
