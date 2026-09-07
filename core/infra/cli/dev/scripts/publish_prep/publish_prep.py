"""
发布前自动化检查与版本元数据同步。

由 ``devcli.py pack`` 调用。
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
from typing import List

from core.infra.cmd_layout import CmdLayout
from core.infra.cli.dev.scripts.publish_prep.changelog_sync import (
    compare_system_new_features,
    sync_version_metadata_from_changelog,
)
from core.infra.cli.dev.scripts.publish_prep.module_versions import (
    check_module_info_files,
    sync_module_doc_versions,
    validate_module_doc_versions,
    validate_module_info_changelog,
    validate_module_info_names,
)
from core.infra.project_context import ProjectContext
from core.infra.setup import Setup

REPO_ROOT = ProjectContext.path.get_project_root()
SYSTEM_JSON = REPO_ROOT / "core" / "system.json"
README_FILES = (REPO_ROOT / "README.md", REPO_ROOT / "README_en.md")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
BADGE_ANCHOR = "https://img.shields.io/badge/version-"


@dataclass
class PublishPrepOptions:
    version: str
    check_only: bool = False
    skip_tests: bool = False
    skip_ic: bool = False
    skip_fed_build: bool = False
    skip_py39: bool = False
    package_userspace: bool = False
    skip_dep_check: bool = False  # 跳过依赖风险检测
    skip_icon_check: bool = False  # 跳过裸状态 emoji 扫描


def normalize_version(raw: str) -> str:
    v = str(raw or "").strip().lstrip("vV")
    if not VERSION_RE.match(v):
        raise ValueError(f"版本号须为 X.Y.Z，收到: {raw!r}")
    return v


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
        [sys.executable, "-m", "core.infra.cli.dev.scripts.minimal_import_check"],
        cwd=str(REPO_ROOT),
    )
    return int(proc.returncode or 0)


def run_pytest() -> int:
    print("\n[检查] pytest…", flush=True)
    py = ProjectContext.path.get_python()
    try:
        py_label = py.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        py_label = str(py)
    print(f"  解释器: {py_label}", flush=True)
    if not ProjectContext.path.get_venv_python().is_file():
        print(
            f"  {CmdLayout.icon.i('warning')} 未找到 venv/，当前 Python 可能缺少 Flask；"
            "建议先运行 setup/install.py 或 pip install -r requirements-dev.txt",
            flush=True,
        )
    proc = subprocess.run(
        [str(py), "-m", "pytest", "-q"],
        cwd=str(REPO_ROOT),
    )
    return int(proc.returncode or 0)


def _node_toolchain_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


def run_fed_build() -> int:
    """``core/ui/fed`` 生产构建（BFF 生产模式依赖 ``fed/build``）。"""
    fed_root = Setup.env.ui_fed_root()
    print("\n[检查] FED 前端构建（npm run build）…", flush=True)
    if not _node_toolchain_available():
        print(f"  {CmdLayout.icon.i('error')} 未检测到 node / npm", flush=True)
        return 1
    if not (fed_root / "package.json").is_file():
        print(f"  {CmdLayout.icon.i('error')} 缺少 {fed_root.relative_to(REPO_ROOT)}/package.json", flush=True)
        return 1
    if not (fed_root / "node_modules").is_dir():
        print("  正在安装 FED 依赖（npm install）…", flush=True)
        install = subprocess.run(["npm", "install"], cwd=str(fed_root))
        if install.returncode != 0:
            return int(install.returncode or 1)
    env = {**os.environ, "CI": "true"}
    proc = subprocess.run(["npm", "run", "build"], cwd=str(fed_root), env=env)
    if proc.returncode != 0:
        return int(proc.returncode or 1)
    if not Setup.runtime.fed_build_ready():
        print(
            f"  {CmdLayout.icon.i('error')} 构建完成但未找到 "
            f"{(fed_root / 'build' / 'index.html').relative_to(REPO_ROOT)}",
            flush=True,
        )
        return 1
    print(f"  {CmdLayout.icon.i('success')} {fed_root.relative_to(REPO_ROOT)}/build 已就绪", flush=True)
    return 0


def run_publish_prep(opts: PublishPrepOptions) -> int:
    version = normalize_version(opts.version)
    release_date = date.today().isoformat()
    failures: List[str] = []

    print(f"发布准备: v{version}  check_only={opts.check_only}", flush=True)

    if not opts.check_only:
        try:
            features = sync_version_metadata_from_changelog(version, release_date=release_date)
            print(
                f"已写入 {SYSTEM_JSON.relative_to(REPO_ROOT)}: "
                f"version={version}, new_features={len(features)} 条（release_date 优先取 CHANGELOG 标题日期）",
                flush=True,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"{CmdLayout.icon.i('error')} CHANGELOG → system 同步失败: {exc}", flush=True)
            return 1
        sync_readme_version_badges(version)
    else:
        cur = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
        print(
            f"仅检查模式：当前 system.json version={cur.get('version')!r}，"
            f"目标 {version!r}",
            flush=True,
        )

    print("\n[检查] CHANGELOG → system.json new_features …", flush=True)
    meta_issues = compare_system_new_features(version)
    if meta_issues:
        failures.append("CHANGELOG/system new_features 未同步")
        for line in meta_issues:
            print(f"  {CmdLayout.icon.i('error')} {line}", flush=True)
    else:
        print(
            f"  {CmdLayout.icon.i('success')} CHANGELOG v{version} 与 system.json new_features 一致",
            flush=True,
        )

    print("\n[检查] module_info.yaml 是否齐全…", flush=True)
    missing = check_module_info_files()
    if missing:
        failures.append("module_info 缺失")
        for line in missing:
            print(f"  {CmdLayout.icon.i('error')} {line}", flush=True)
    else:
        print(
            f"  {CmdLayout.icon.i('success')} core/modules/*、core/infra/*、core/ui、core/bff、core/tables 均已具备 module_info.yaml",
            flush=True,
        )

    changelog_issues = validate_module_info_changelog()
    if changelog_issues:
        failures.append("module_info changelog 校验未通过")
        for line in changelog_issues:
            print(f"  {CmdLayout.icon.i('error')} {line}", flush=True)
    else:
        print(f"  {CmdLayout.icon.i('success')} 各 module_info changelog 与 version 一致", flush=True)

    print("\n[检查] module_info.name 是否符合目录约定…", flush=True)
    name_issues = validate_module_info_names()
    if name_issues:
        failures.append("module_info.name 校验未通过")
        for line in name_issues:
            print(f"  {CmdLayout.icon.i('error')} {line}", flush=True)
    else:
        print(
            f"  {CmdLayout.icon.i('success')} name = modules.* / infra.* / ui / bff / tables",
            flush=True,
        )

    if not opts.check_only:
        print("\n[同步] 按 module_info 改写文档文首版本字段…", flush=True)
        synced = sync_module_doc_versions()
        if synced:
            for line in synced:
                print(f"  {CmdLayout.icon.i('success')} {line}", flush=True)
        else:
            print(f"  {CmdLayout.icon.i('success')} 无需改写", flush=True)

    print("\n[检查] 模块文档版本字段是否与 module_info 一致…", flush=True)
    doc_issues = validate_module_doc_versions()
    if doc_issues:
        failures.append("模块文档版本校验未通过")
        for line in doc_issues:
            print(f"  {CmdLayout.icon.i('error')} {line}", flush=True)
    else:
        print(
            f"  {CmdLayout.icon.i('success')} **版本：** / # Version: / 最低支持核心版本 与 module_info 一致",
            flush=True,
        )

    if not opts.skip_py39:
        from core.infra.cli.dev.scripts.py39_compat_check import run_py39_compat_check

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

    # 依赖安装风险检测
    if not opts.skip_dep_check:
        print("\n[检查] 依赖安装风险（Windows 兼容性、未使用依赖等）…", flush=True)
        from core.infra.cli.dev.scripts.dependency_risk import run_dependency_check

        dep_check_result = run_dependency_check(verbose=True)
        if dep_check_result == 1:
            failures.append("依赖风险检测发现关键问题")
        elif dep_check_result == 2:
            print(f"  {CmdLayout.icon.i('warning')} 发现高危依赖项，建议修复但允许继续", flush=True)
            # 高危不阻止打包，只警告
    else:
        print("\n[跳过] 依赖安装风险检测", flush=True)

    if not opts.skip_icon_check:
        from core.infra.cli.dev.scripts.raw_icon_scan import run_raw_icon_scan

        if run_raw_icon_scan(verbose=True) != 0:
            failures.append("裸状态 emoji 扫描未通过（请改用 IconService / i()）")
    else:
        print("\n[跳过] 裸状态 emoji 扫描", flush=True)

    print("\n---", flush=True)
    if failures:
        print(f"{CmdLayout.icon.i('error')} 未通过: " + ", ".join(failures), flush=True)
        print("请处理 CHANGELOG 发布清单中的手工项（Changelog、module 文档、gitignore 等）。", flush=True)
        return 1

    print(f"{CmdLayout.icon.i('success')} 自动化项已通过。", flush=True)

    if opts.package_userspace:
        if opts.check_only:
            print("\n[跳过] init userspace 打包（--check-only）", flush=True)
        else:
            from core.infra.project_context import ProjectContext
            from core.infra.updater import Updater
            from core.infra.setup import Setup

            print("\n[执行] 打包 init userspace…", flush=True)
            dest = ProjectContext.path.get_updater_directory()
            Updater.runtime.sync_orchestrator(dest)
            if Setup.artifacts.package_userspace() != 0:
                return 1

    if not opts.check_only:
        print(
            f"请继续：更新 CHANGELOG v{version}、按需更新模块文档与 module_info 依赖项，然后提交/打 tag。",
            flush=True,
        )
    return 0
