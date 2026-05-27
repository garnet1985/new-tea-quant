"""
发布前自动化检查与版本元数据同步。

由 ``dev-cli.py -p -vX.Y.Z`` 调用。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Sequence, Tuple

from core.utils import i as icon
from devtools.quick_tools._paths import REPO_ROOT
from setup.install_runtime import UI_FED_ROOT, fed_build_ready

SYSTEM_JSON = REPO_ROOT / "core" / "system.json"
SYSTEM_PY = REPO_ROOT / "core" / "system.py"
README_FILES = (REPO_ROOT / "README.md", REPO_ROOT / "README_en.md")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
BADGE_ANCHOR = "https://img.shields.io/badge/version-"

# ``core/modules/*``、``core/infra/*`` 每个子包；``core/ui`` 仅顶层模块（不含 bff/fed 子目录）
_MODULE_PACKAGE_ROOTS: Tuple[Tuple[str, Path], ...] = (
    ("core/modules", REPO_ROOT / "core" / "modules"),
    ("core/infra", REPO_ROOT / "core" / "infra"),
)
_SINGLE_MODULE_ROOTS: Tuple[Tuple[str, Path], ...] = (
    ("core/ui", REPO_ROOT / "core" / "ui"),
)


@dataclass
class PublishPrepOptions:
    version: str
    check_only: bool = False
    skip_tests: bool = False
    skip_ic: bool = False
    skip_fed_build: bool = False
    skip_py39: bool = False


def normalize_version(raw: str) -> str:
    v = str(raw or "").strip().lstrip("vV")
    if not VERSION_RE.match(v):
        raise ValueError(f"版本号须为 X.Y.Z，收到: {raw!r}")
    return v


def _module_package_dirs(root: Path) -> List[Path]:
    if not root.is_dir():
        return []
    out: List[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") or name.startswith("__"):
            continue
        out.append(child)
    return out


def check_module_info_files() -> List[str]:
    """返回缺少 module_info.yaml 的模块目录（相对路径）。"""
    missing: List[str] = []
    for label, root in _MODULE_PACKAGE_ROOTS:
        for pkg in _module_package_dirs(root):
            rel = pkg.relative_to(REPO_ROOT).as_posix()
            if not (pkg / "module_info.yaml").is_file():
                missing.append(f"{label}/{pkg.name} ({rel})")
    for label, root in _SINGLE_MODULE_ROOTS:
        if not (root / "module_info.yaml").is_file():
            missing.append(f"{label} ({root.relative_to(REPO_ROOT).as_posix()})")
    return missing


def update_system_json(version: str, release_date: str) -> None:
    data = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{SYSTEM_JSON} 不是 object")
    data["version"] = version
    data["release_date"] = release_date
    SYSTEM_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已写入 {SYSTEM_JSON.relative_to(REPO_ROOT)}: version={version}, release_date={release_date}", flush=True)


def update_system_py_fallback(version: str, release_date: str) -> None:
    text = SYSTEM_PY.read_text(encoding="utf-8")
    block_start = text.find("_FALLBACK:")
    if block_start < 0:
        raise RuntimeError("core/system.py 中未找到 _FALLBACK")
    block_end = text.find("\n\n\ndef _load_payload", block_start)
    if block_end < 0:
        block_end = text.find("\ndef _load_payload", block_start)
    if block_end < 0:
        raise RuntimeError("无法定位 _FALLBACK 块结束")
    block = text[block_start:block_end]
    block = re.sub(
        r'("version":\s*")[^"]+(")',
        rf"\g<1>{version}\2",
        block,
        count=1,
    )
    block = re.sub(
        r'("release_date":\s*")[^"]+(")',
        rf"\g<1>{release_date}\2",
        block,
        count=1,
    )
    new_text = text[:block_start] + block + text[block_end:]
    SYSTEM_PY.write_text(new_text, encoding="utf-8")
    print(f"已同步 {SYSTEM_PY.relative_to(REPO_ROOT)} 内 _FALLBACK 版本字段", flush=True)


def sync_readme_version_badges(version: str) -> None:
    for readme in README_FILES:
        if not readme.is_file():
            raise FileNotFoundError(readme)
        content = readme.read_text(encoding="utf-8")
        idx = content.find(BADGE_ANCHOR)
        if idx < 0:
            raise RuntimeError(f"{readme.name} 中未找到版本徽章")
        start = idx + len(BADGE_ANCHOR)
        end = content.find("-", start)
        if end <= start:
            raise RuntimeError(f"{readme.name} 版本徽章格式异常")
        new_content = content[:start] + version + content[end:]
        readme.write_text(new_content, encoding="utf-8")
        print(f"已同步 {readme.relative_to(REPO_ROOT)} 版本徽章 → {version}", flush=True)


def run_minimal_import_check() -> int:
    print("\n[检查] UI 最小依赖 import（-ic）…", flush=True)
    proc = subprocess.run(
        [sys.executable, "-m", "devtools.quick_tools.minimal_import_check"],
        cwd=str(REPO_ROOT),
    )
    return int(proc.returncode or 0)


def run_pytest() -> int:
    print("\n[检查] pytest…", flush=True)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(REPO_ROOT),
    )
    return int(proc.returncode or 0)


def _node_toolchain_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


def run_fed_build() -> int:
    """``core/ui/fed`` 生产构建（BFF 生产模式依赖 ``fed/build``）。"""
    print("\n[检查] FED 前端构建（npm run build）…", flush=True)
    if not _node_toolchain_available():
        print(f"  {icon('error')} 未检测到 node / npm", flush=True)
        return 1
    if not (UI_FED_ROOT / "package.json").is_file():
        print(f"  {icon('error')} 缺少 {UI_FED_ROOT.relative_to(REPO_ROOT)}/package.json", flush=True)
        return 1
    if not (UI_FED_ROOT / "node_modules").is_dir():
        print("  正在安装 FED 依赖（npm install）…", flush=True)
        install = subprocess.run(["npm", "install"], cwd=str(UI_FED_ROOT))
        if install.returncode != 0:
            return int(install.returncode or 1)
    env = {**os.environ, "CI": "true"}
    proc = subprocess.run(["npm", "run", "build"], cwd=str(UI_FED_ROOT), env=env)
    if proc.returncode != 0:
        return int(proc.returncode or 1)
    if not fed_build_ready():
        print(
            f"  {icon('error')} 构建完成但未找到 "
            f"{(UI_FED_ROOT / 'build' / 'index.html').relative_to(REPO_ROOT)}",
            flush=True,
        )
        return 1
    print(f"  {icon('success')} {UI_FED_ROOT.relative_to(REPO_ROOT)}/build 已就绪", flush=True)
    return 0


def run_publish_prep(opts: PublishPrepOptions) -> int:
    version = normalize_version(opts.version)
    release_date = date.today().isoformat()
    failures: List[str] = []

    print(f"发布准备: v{version}  check_only={opts.check_only}", flush=True)

    if not opts.check_only:
        update_system_json(version, release_date)
        update_system_py_fallback(version, release_date)
        sync_readme_version_badges(version)
    else:
        cur = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
        print(
            f"仅检查模式：当前 system.json version={cur.get('version')!r}，"
            f"目标 {version!r}",
            flush=True,
        )

    print("\n[检查] module_info.yaml 是否齐全（仅检查文件存在，不比对各模块 version 字段）…", flush=True)
    missing = check_module_info_files()
    if missing:
        failures.append("module_info 缺失")
        for line in missing:
            print(f"  {icon('error')} {line}", flush=True)
    else:
        print(
            f"  {icon('success')} core/modules/*、core/infra/*、core/ui 均已具备 module_info.yaml",
            flush=True,
        )

    if not opts.skip_py39:
        from devtools.quick_tools.py39_compat_check import run_py39_compat_check

        if run_py39_compat_check() != 0:
            failures.append("Python 3.9 兼容性检查未通过")
    else:
        print("\n[跳过] Python 3.9 兼容性检查", flush=True)

    if not opts.skip_ic:
        if run_minimal_import_check() != 0:
            failures.append("minimal import check 失败")
    else:
        print("\n[跳过] UI 最小依赖 import", flush=True)

    if not opts.skip_fed_build:
        if run_fed_build() != 0:
            failures.append("FED npm run build 失败")
    else:
        print("\n[跳过] FED 前端构建", flush=True)

    if not opts.skip_tests:
        if run_pytest() != 0:
            failures.append("pytest 失败")
    else:
        print("\n[跳过] pytest", flush=True)

    print("\n---", flush=True)
    if failures:
        print(f"{icon('error')} 未通过: " + ", ".join(failures), flush=True)
        print("请处理 CHANGELOG 发布清单中的手工项（Changelog、module 文档、gitignore 等）。", flush=True)
        return 1

    print(f"{icon('success')} 自动化项已通过。", flush=True)
    if not opts.check_only:
        print(
            f"请继续：更新 CHANGELOG v{version}、按需更新模块文档与 module_info 依赖项，然后提交/打 tag。",
            flush=True,
        )
    return 0


def parse_publish_argv(argv: Sequence[str]) -> Tuple[PublishPrepOptions | None, List[str]]:
    """从 argv 解析 ``-p`` / ``-v0.3.2`` 等；返回 (options, 剩余 argv)。"""
    raw = list(argv)
    if "-p" not in raw:
        return None, raw

    i = raw.index("-p")
    rest = raw[:i] + raw[i + 1 :]
    version: str | None = None
    check_only = False
    skip_tests = False
    skip_ic = False
    skip_fed_build = False
    skip_py39 = False
    j = 0
    while j < len(rest):
        tok = rest[j]
        if tok == "--check-only":
            check_only = True
            del rest[j]
            continue
        if tok == "--skip-tests":
            skip_tests = True
            del rest[j]
            continue
        if tok == "--skip-ic":
            skip_ic = True
            del rest[j]
            continue
        if tok == "--skip-fed-build":
            skip_fed_build = True
            del rest[j]
            continue
        if tok == "--skip-py39":
            skip_py39 = True
            del rest[j]
            continue
        if tok.startswith("-v") and len(tok) > 2:
            version = tok[2:]
            del rest[j]
            continue
        if tok in ("-v", "--version") and j + 1 < len(rest):
            version = rest[j + 1]
            del rest[j : j + 2]
            continue
        j += 1

    if not version:
        print("发布准备需要版本号，例如: python dev-cli.py -p -v0.3.2", file=sys.stderr)
        raise SystemExit(2)

    return (
        PublishPrepOptions(
            version=version,
            check_only=check_only,
            skip_tests=skip_tests,
            skip_ic=skip_ic,
            skip_fed_build=skip_fed_build,
            skip_py39=skip_py39,
        ),
        rest,
    )
