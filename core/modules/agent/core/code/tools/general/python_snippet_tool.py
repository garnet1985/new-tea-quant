"""run_python_snippet：受限短脚本沙箱（列表/统计；无 import / IO / 网络）。"""

from __future__ import annotations

import ast
import io
import math
import statistics
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any, Dict, Set

from core.modules.agent.core.code.conf.conf import (
    PYTHON_SNIPPET_MAX_CHARS,
    PYTHON_SNIPPET_RESULT_MAX_CHARS,
    PYTHON_SNIPPET_STDOUT_MAX_CHARS,
    PYTHON_SNIPPET_TIMEOUT_SECONDS,
)

_FORBIDDEN_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
    ast.ClassDef,
    ast.AsyncFunctionDef,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
    ast.With,
    ast.While,
    ast.Delete,
)

_SAFE_BUILTINS: Dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "pow": pow,
    "print": None,  # filled per-run
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


def run_python_snippet(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """执行短 Python 片段。请把最终答案赋给 ``result``；也可用 print。

    预置 ``math`` / ``statistics``；禁止 import、文件/网络、while、类定义。
    """
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"code"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    code = args.get("code")
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "error": "code 不能为空"}
    code = code.strip()
    if len(code) > PYTHON_SNIPPET_MAX_CHARS:
        return {
            "ok": False,
            "error": f"code 过长（最多 {PYTHON_SNIPPET_MAX_CHARS} 字符）",
        }

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return {"ok": False, "error": f"语法错误: {exc}"}

    bad = _find_forbidden(tree)
    if bad:
        return {"ok": False, "error": f"不允许的语法/名称: {bad}"}

    stdout = io.StringIO()

    def _print(*values: Any, **kwargs: Any) -> None:
        kwargs = dict(kwargs)
        kwargs["file"] = stdout
        print(*values, **kwargs)

    builtins = dict(_SAFE_BUILTINS)
    builtins["print"] = _print
    globals_dict: Dict[str, Any] = {
        "__builtins__": builtins,
        "math": math,
        "statistics": statistics,
    }
    locals_dict: Dict[str, Any] = {}

    def _run() -> None:
        exec(compile(tree, "<snippet>", "exec"), globals_dict, locals_dict)  # noqa: S102

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_run)
            fut.result(timeout=float(PYTHON_SNIPPET_TIMEOUT_SECONDS))
    except FuturesTimeout:
        return {
            "ok": False,
            "error": f"执行超时（>{PYTHON_SNIPPET_TIMEOUT_SECONDS}s）",
        }
    except Exception as exc:
        return {"ok": False, "error": f"执行失败: {type(exc).__name__}: {exc}"}

    if "result" not in locals_dict and "result" not in globals_dict:
        text = stdout.getvalue()
        if text.strip():
            return {
                "ok": True,
                "result": None,
                "stdout": _clip(text, PYTHON_SNIPPET_STDOUT_MAX_CHARS),
                "note": "未赋值 result；仅返回 stdout。请把最终值赋给 result。",
            }
        return {
            "ok": False,
            "error": "请把最终答案赋给 result（例如 result = statistics.median(xs)）",
        }

    raw = locals_dict.get("result", globals_dict.get("result"))
    try:
        result = _jsonify(raw)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    out: Dict[str, Any] = {
        "ok": True,
        "result": result,
        "note": "沙箱结果仅供算术/列表统计；回测收益仍以 read_*_report 为准。",
    }
    text = stdout.getvalue()
    if text:
        out["stdout"] = _clip(text, PYTHON_SNIPPET_STDOUT_MAX_CHARS)
    return out


def _find_forbidden(tree: ast.AST) -> str:
    for node in ast.walk(tree):
        if isinstance(node, _FORBIDDEN_NODES):
            return type(node).__name__
        if isinstance(node, ast.Attribute):
            if str(node.attr).startswith("_"):
                return f"Attribute.{node.attr}"
        if isinstance(node, ast.Name):
            name = str(node.id)
            if name.startswith("_"):
                return f"Name.{name}"
            if name in {
                "getattr",
                "setattr",
                "delattr",
                "globals",
                "locals",
                "vars",
                "dir",
                "type",
                "eval",
                "exec",
                "compile",
                "open",
                "input",
                "breakpoint",
                "__import__",
                "memoryview",
                "bytearray",
                "object",
                "super",
                "classmethod",
                "staticmethod",
                "property",
                "help",
                "exit",
                "quit",
            }:
                return f"Name.{name}"
        if isinstance(node, ast.Call):
            # block fancy calls like ().__class__ already caught by Attribute
            pass
    return ""


def _jsonify(value: Any, *, _depth: int = 0, _seen: Set[int] | None = None) -> Any:
    if _depth > 8:
        raise ValueError("result 嵌套过深")
    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str) and len(value) > PYTHON_SNIPPET_RESULT_MAX_CHARS:
            raise ValueError("result 字符串过长")
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("result 含 NaN/Inf")
        return value
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, (list, tuple)):
        if len(value) > 500:
            raise ValueError("result 列表过长（最多 500）")
        return [_jsonify(v, _depth=_depth + 1, _seen=_seen) for v in value]
    if isinstance(value, dict):
        if len(value) > 200:
            raise ValueError("result 字典过大（最多 200 键）")
        out: Dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, (str, int)):
                raise ValueError("result 字典键须为 str/int")
            out[str(k)] = _jsonify(v, _depth=_depth + 1, _seen=_seen)
        return out
    if isinstance(value, set):
        return [_jsonify(v, _depth=_depth + 1, _seen=_seen) for v in sorted(value, key=str)]
    raise ValueError(f"result 类型不可序列化: {type(value).__name__}")


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 12)] + "\n…(truncated)"
