#!/usr/bin/env python3
"""
扫描 Python 源码在 3.9 下可能不兼容的写法（仅报告，不修改文件）。

检查项：
- PEP 604 联合类型注解（``X | Y``）且文件未 ``from __future__ import annotations``
- ``match`` / ``case``（3.10+）
- ``except*``（3.11+）
- 泛型类 ``class C[T]:``（3.12+，运行环境为 3.12+ 时）
- 若本机存在 ``python3.9``，对无法静态解析的语法再做 ``py_compile``

用法::

    python -m devtools.quick_tools.py39_compat_check
    python dev-cli.py -p -v0.3.3   # 发布准备中间步骤
"""
from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from devtools.quick_tools._paths import REPO_ROOT

_SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        ".ntq",
        "node_modules",
        "build",
        "fed",
        "venv",
        ".venv",
        ".pytest_cache",
        "dist",
        "egg-info",
    }
)

_SCAN_ROOTS: Tuple[Path, ...] = (
    REPO_ROOT / "core",
    REPO_ROOT / "setup",
    REPO_ROOT / "devtools",
    REPO_ROOT / "userspace",
)

_ROOT_PY_FILES: Tuple[Path, ...] = (
    REPO_ROOT / "launcher.py",
    REPO_ROOT / "start-cli.py",
    REPO_ROOT / "dev-cli.py",
)


@dataclass(frozen=True)
class CompatIssue:
    path: Path
    line: int
    rule: str
    message: str

    def format(self) -> str:
        rel = self.path.relative_to(REPO_ROOT).as_posix()
        return f"  {rel}:{self.line}: [{self.rule}] {self.message}"


def _has_future_annotations(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "__future__":
            continue
        for alias in node.names:
            if alias.name == "annotations":
                return True
    return False


def _annotation_uses_pep604_union(node: Optional[ast.AST]) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return True
    if isinstance(node, ast.Subscript):
        return _annotation_uses_pep604_union(node.value) or _annotation_uses_pep604_union(
            node.slice
        )
    if isinstance(node, ast.Tuple):
        return any(_annotation_uses_pep604_union(elt) for elt in node.elts)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return False
    return False


def _iter_annotation_nodes(tree: ast.AST) -> Iterator[Tuple[int, ast.AST]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.returns is not None:
                yield node.lineno, node.returns
            args = list(getattr(node.args, "posonlyargs", []))
            args += node.args.args + node.args.kwonlyargs
            if node.args.vararg and node.args.vararg.annotation:
                yield node.args.vararg.lineno, node.args.vararg.annotation
            if node.args.kwarg and node.args.kwarg.annotation:
                yield node.args.kwarg.lineno, node.args.kwarg.annotation
            for arg in args:
                if arg.annotation is not None:
                    yield arg.lineno, arg.annotation
        elif isinstance(node, ast.AsyncFunctionDef):
            if node.returns is not None:
                yield node.lineno, node.returns
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.annotation is not None:
                    yield arg.lineno, arg.annotation
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            yield node.lineno, node.annotation
        elif isinstance(node, ast.arg) and node.annotation is not None:
            yield node.lineno, node.annotation


def _ast_issues_for_file(path: Path, source: str) -> List[CompatIssue]:
    issues: List[CompatIssue] = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        issues.append(
            CompatIssue(
                path=path,
                line=int(exc.lineno or 1),
                rule="syntax",
                message=f"当前解释器无法解析: {exc.msg}",
            )
        )
        return issues

    if not isinstance(tree, ast.Module):
        return issues

    if not _has_future_annotations(tree):
        for lineno, ann in _iter_annotation_nodes(tree):
            if _annotation_uses_pep604_union(ann):
                issues.append(
                    CompatIssue(
                        path=path,
                        line=lineno,
                        rule="pep604",
                        message=(
                            "使用了 ``X | Y`` 类型注解但未 "
                            "``from __future__ import annotations``（3.9 运行时会报错）"
                        ),
                    )
                )

    for node in ast.walk(tree):
        if type(node).__name__ == "Match":
            issues.append(
                CompatIssue(
                    path=path,
                    line=int(getattr(node, "lineno", 1) or 1),
                    rule="match",
                    message="``match`` 语句需要 Python 3.10+",
                )
            )
        if type(node).__name__ == "TryStar":
            issues.append(
                CompatIssue(
                    path=path,
                    line=int(getattr(node, "lineno", 1) or 1),
                    rule="except-star",
                    message="``except*`` 需要 Python 3.11+",
                )
            )
        if isinstance(node, ast.ClassDef) and getattr(node, "type_params", None):
            issues.append(
                CompatIssue(
                    path=path,
                    line=int(node.lineno or 1),
                    rule="pep695",
                    message="``class C[T]:`` 泛型语法需要 Python 3.12+",
                )
            )

    return issues


def _find_python39() -> Optional[str]:
    for name in ("python3.9", "python3.9.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _py39_compile_issues(paths: Sequence[Path], py39: str) -> List[CompatIssue]:
    issues: List[CompatIssue] = []
    for path in paths:
        proc = subprocess.run(
            [py39, "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            continue
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        msg = detail[-1] if detail else "py_compile 失败"
        line = 1
        if "line " in msg:
            try:
                frag = msg.split("line ", 1)[1]
                line = int(frag.split(")", 1)[0].strip())
            except (IndexError, ValueError):
                line = 1
        issues.append(
            CompatIssue(
                path=path,
                line=line,
                rule="py39-compile",
                message=msg,
            )
        )
    return issues


def iter_scan_paths() -> Iterator[Path]:
    seen: set[Path] = set()
    for root in _SCAN_ROOTS:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".py":
            resolved = root.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield root
            continue
        for path in sorted(root.rglob("*.py")):
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            if "core/ui/fed" in path.as_posix():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path
    for path in _ROOT_PY_FILES:
        if path.is_file():
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield path


def collect_py39_compat_issues(
    *,
    paths: Optional[Iterable[Path]] = None,
    use_py39_compile: bool = True,
) -> List[CompatIssue]:
    """收集所有兼容性问题；不修改源码。"""
    py_paths = list(paths) if paths is not None else list(iter_scan_paths())
    all_issues: List[CompatIssue] = []
    compile_candidates: List[Path] = []

    for path in py_paths:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            all_issues.append(
                CompatIssue(
                    path=path,
                    line=1,
                    rule="io",
                    message=f"无法读取: {exc}",
                )
            )
            continue
        file_issues = _ast_issues_for_file(path, source)
        all_issues.extend(file_issues)
        if not file_issues:
            compile_candidates.append(path)

    py39 = _find_python39() if use_py39_compile else None
    if py39 and compile_candidates:
        all_issues.extend(_py39_compile_issues(compile_candidates, py39))

    return sorted(all_issues, key=lambda i: (i.path.as_posix(), i.line, i.rule))


def run_py39_compat_check(*, use_py39_compile: bool = True) -> int:
    """打印报告；有发现问题时返回 1。"""
    print("\n[检查] Python 3.9 兼容性（仅报告，不自动修改）…", flush=True)
    issues = collect_py39_compat_issues(use_py39_compile=use_py39_compile)
    py39 = _find_python39()
    if py39:
        print(f"  已使用 {py39} 做 py_compile 补充检查", flush=True)
    else:
        print(
            "  未找到 python3.9 可执行文件，跳过 py_compile（仍执行 AST 静态检查）",
            flush=True,
        )

    if not issues:
        print("  未发现已知的 3.9 不兼容写法。", flush=True)
        return 0

    by_file: dict[str, List[CompatIssue]] = {}
    for issue in issues:
        key = issue.path.relative_to(REPO_ROOT).as_posix()
        by_file.setdefault(key, []).append(issue)

    print(f"  发现 {len(issues)} 处可能不兼容（{len(by_file)} 个文件）：", flush=True)
    for issue in issues:
        print(issue.format(), flush=True)
    print(
        "\n  说明：带 ``from __future__ import annotations`` 的 ``X | Y`` 注解在 3.9 下通常可运行；"
        "请按上表逐项确认。",
        flush=True,
    )
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Python 3.9 兼容性扫描（只读）")
    parser.add_argument(
        "--no-py39-compile",
        action="store_true",
        help="不调用本机 python3.9 py_compile",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    return run_py39_compat_check(use_py39_compile=not args.no_py39_compile)


if __name__ == "__main__":
    raise SystemExit(main())
