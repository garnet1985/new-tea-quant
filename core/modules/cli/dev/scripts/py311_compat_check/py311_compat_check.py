#!/usr/bin/env python3
"""
用当前解释器扫描 3.12+ 语法（仅报告，不修改文件）。

当前解释器必须是 Python 3.11+。检查项：
- 泛型类 ``class C[T]:``（3.12+）
- ``ast.parse``（与当前解释器语法一致；不再对每个文件起 ``py_compile`` 子进程）

用法::

    python -m core.modules.cli.dev.scripts.py311_compat_check
    python devcli.py p -core_v0.3.3   # 发布准备中间步骤
"""
from __future__ import annotations

import argparse
import ast
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from core.infra.project_context import ProjectContext

REPO_ROOT = ProjectContext.path.get_project_root()

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
    REPO_ROOT / "ci",
    ProjectContext.path.get_userspace_root(),
)

_ROOT_PY_FILES: Tuple[Path, ...] = (
    REPO_ROOT / "launcher.py",
    REPO_ROOT / "cli.py",
    REPO_ROOT / "devcli.py",
)


@dataclass(frozen=True)
class CompatIssue:
    path: Path
    line: int
    rule: str
    message: str

    def format(self) -> str:
        try:
            rel = self.path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = self.path.as_posix()
        return f"  {rel}:{self.line}: [{self.rule}] {self.message}"


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

    for node in ast.walk(tree):
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
        for path in root.rglob("*.py"):
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


def collect_py311_compat_issues(
    *,
    paths: Optional[Iterable[Path]] = None,
    use_py311_compile: bool = True,
) -> List[CompatIssue]:
    """收集所有兼容性问题；不修改源码。

    ``use_py311_compile`` 保留兼容旧调用方；同解释器下 ``ast.parse`` 已覆盖
    原先逐文件 ``py_compile`` 子进程的语法检查，故该参数不再触发额外编译。
    """
    del use_py311_compile  # 见 docstring：避免 2000+ 次子进程启动
    py_paths = list(paths) if paths is not None else list(iter_scan_paths())
    all_issues: List[CompatIssue] = []

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
        all_issues.extend(_ast_issues_for_file(path, source))

    return sorted(all_issues, key=lambda i: (i.path.as_posix(), i.line, i.rule))


def run_py311_compat_check(*, use_py311_compile: bool = True) -> int:
    """打印报告；有发现问题时返回 1。"""
    print("\n[检查] Python 3.11 语法（仅报告，不自动修改）…", flush=True)
    if sys.version_info < (3, 11):
        print(
            f"  当前解释器是 Python {sys.version_info.major}.{sys.version_info.minor}，需要 3.11+",
            flush=True,
        )
        return 1
    t0 = time.perf_counter()
    py_paths = list(iter_scan_paths())
    issues = collect_py311_compat_issues(
        paths=py_paths,
        use_py311_compile=use_py311_compile,
    )
    elapsed = time.perf_counter() - t0
    print(
        f"  已用 {sys.executable} AST 扫描 {len(py_paths)} 个 .py（{elapsed:.1f}s）",
        flush=True,
    )

    if not issues:
        print("  未发现已知的 3.11 不兼容写法。", flush=True)
        return 0

    by_file: dict[str, List[CompatIssue]] = {}
    for issue in issues:
        key = issue.path.relative_to(REPO_ROOT).as_posix()
        by_file.setdefault(key, []).append(issue)

    print(f"  发现 {len(issues)} 处可能不兼容（{len(by_file)} 个文件）：", flush=True)
    for issue in issues:
        print(issue.format(), flush=True)
    print(
        "\n  说明：最低版本是 3.11。``class C[T]:`` 这类 3.12 语法不能用。"
        "请按上表逐项确认。",
        flush=True,
    )
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Python 3.11 兼容性扫描（只读）")
    parser.add_argument(
        "--no-py311-compile",
        action="store_true",
        help="兼容旧开关；现已始终只用 AST，不再起 py_compile 子进程",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    return run_py311_compat_check(use_py311_compile=not args.no_py311_compile)


if __name__ == "__main__":
    raise SystemExit(main())
