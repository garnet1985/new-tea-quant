"""calculator：安全算术表达式求值。"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any, Dict

_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "ceil": math.ceil,
    "floor": math.floor,
}
_CONSTS = {
    "pi": math.pi,
    "e": math.e,
}


def calculator(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """计算表达式。支持 + - * / // % **、括号，以及 abs/round/sqrt/log 等。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"expression"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    expr = args.get("expression")
    if not isinstance(expr, str) or not expr.strip():
        return {"ok": False, "error": "expression 不能为空"}
    expr = expr.strip()
    if len(expr) > 500:
        return {"ok": False, "error": "expression 过长"}
    try:
        tree = ast.parse(expr, mode="eval")
        value = _eval(tree.body)
    except Exception as exc:
        return {"ok": False, "error": f"无法计算: {exc}"}
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return {"ok": False, "error": "结果必须是数字"}
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return {"ok": False, "error": "结果无效（NaN/Inf）"}
    return {
        "ok": True,
        "expression": expr,
        "result": value,
        "note": "仅算术。策略收益数字仍以报告工具为准。",
    }


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("只允许数字常量")
    if isinstance(node, ast.Name):
        if node.id in _CONSTS:
            return _CONSTS[node.id]
        raise ValueError(f"未知名称: {node.id}")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left = _eval(node.left)
        right = _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("指数过大")
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise ValueError("除零")
        return _BIN[type(node.op)](left, right)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ValueError("只允许白名单函数")
        if node.keywords:
            raise ValueError("不支持关键字参数")
        fn = _FUNCS[node.func.id]
        values = [_eval(a) for a in node.args]
        return fn(*values)
    raise ValueError(f"不支持的语法: {type(node).__name__}")
