#!/usr/bin/env python3
"""
UI 最小依赖 import 冒烟：仅在 ``core/bff/requirements.txt`` 已安装的环境下，
验证 launcher / BFF 冷启动链不会因顶层 import 拉起未声明的三方包。

用法::

    python -m core.infra.cli.dev.scripts.minimal_import_check
    python devcli.py ic

CI 见 ``.github/workflows/ci.yml`` 任务 ``minimal-ui-imports``。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import textwrap
import venv
from dataclasses import dataclass
from pathlib import Path

from core.infra.cmd_layout import CmdLayout
from core.infra.cli.dev.services.paths import REPO_ROOT
from core.infra.setup import Setup

BFF_REQUIREMENTS = Setup.env.ui_bff_requirements()
DEFAULT_VENV_DIR = REPO_ROOT / ".ntq" / "ci-minimal-venv"


@dataclass(frozen=True)
class ImportCheck:
    """单条 import 探针。"""

    check_id: str
    code: str
    description: str = ""


# 与 launcher.py / install_ui_runtime / BFF 注册蓝图对齐；勿在此调用 launch_ui_stack 或 ensure_venv。
UI_BOOTSTRAP_CHECKS: tuple[ImportCheck, ...] = (
    ImportCheck(
        "core.ui.ports",
        "import core.ui.ports",
        "UI 端口常量",
    ),
    ImportCheck(
        "core.system",
        "from core.system import python_minimum, system_meta",
        "launcher / install_runtime 版本元信息",
    ),
    ImportCheck(
        "setup.facade",
        "from core.infra.setup import Setup",
        "安装域门面",
    ),
    ImportCheck(
        "core.bff.app",
        textwrap.dedent(
            """
            from core.bff.app import create_app
            create_app()
            """
        ).strip(),
        "BFF 注册全部蓝图（含 setup / workbench 路由模块）",
    ),
    ImportCheck(
        "setup.steps.sys_req_check",
        textwrap.dedent(
            """
            import os
            os.environ["NTQ_SKIP_AUTO_VENV"] = "1"
            import importlib.util
            path = os.path.join("setup", "steps", "sys_req_check", "install.py")
            spec = importlib.util.spec_from_file_location("ntq_sys_req_check", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            """
        ).strip(),
        "UI Setup 首步 install 脚本（sys_req_check）",
    ),
)


def _probe_import(python: Path, repo_root: Path, check: ImportCheck) -> tuple[bool, str]:
    lines = [
        "import os",
        "import sys",
        f"repo = {str(repo_root)!r}",
        "os.chdir(repo)",
        "if repo not in sys.path:",
        "    sys.path.insert(0, repo)",
        'os.environ.setdefault("NTQ_SKIP_AUTO_VENV", "1")',
    ]
    lines.extend(line for line in check.code.strip().splitlines())
    wrapper = "\n".join(lines)
    env = os.environ.copy()
    env["NTQ_SKIP_AUTO_VENV"] = "1"
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [str(python), "-c", wrapper],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, ""
    err = (proc.stderr or proc.stdout or "").strip()
    return False, err or f"exit code {proc.returncode}"


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _ensure_venv(venv_dir: Path) -> Path:
    vpy = _venv_python(venv_dir)
    if not vpy.is_file():
        print(f"创建最小环境 venv: {venv_dir}", flush=True)
        builder = venv.EnvBuilder(with_pip=True, clear=True)
        builder.create(venv_dir)
    pip = venv_dir / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    print(f"安装 BFF 依赖: {BFF_REQUIREMENTS}", flush=True)
    if not BFF_REQUIREMENTS.is_file():
        raise FileNotFoundError(BFF_REQUIREMENTS)
    subprocess.run(
        [str(pip), "install", "--upgrade", "pip"],
        check=True,
    )
    subprocess.run(
        [str(pip), "install", "-r", str(BFF_REQUIREMENTS)],
        check=True,
    )
    return vpy


def run_ui_bootstrap_checks(*, python: Path, repo_root: Path = REPO_ROOT) -> list[tuple[ImportCheck, str]]:
    failures: list[tuple[ImportCheck, str]] = []
    for check in UI_BOOTSTRAP_CHECKS:
        ok, err = _probe_import(python, repo_root, check)
        mark = CmdLayout.icon.i("success") if ok else CmdLayout.icon.i("error")
        print(f"  {mark} {check.check_id}", flush=True)
        if not ok:
            failures.append((check, err))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UI 最小依赖 import 冒烟检查")
    parser.add_argument(
        "--python",
        default="",
        help="用于探针的解释器；默认在 --venv-dir 或临时 venv 中创建",
    )
    parser.add_argument(
        "--venv-dir",
        default=str(DEFAULT_VENV_DIR),
        help=f"最小 venv 目录（默认 {DEFAULT_VENV_DIR}）",
    )
    parser.add_argument(
        "--no-create-venv",
        action="store_true",
        help="不创建/安装 venv，使用 --python 或当前 sys.executable",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="仓库根目录（默认自动检测）",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if args.no_create_venv:
        # 勿 resolve()：macOS venv/bin/python 链到系统框架时，resolve 会丢掉 site-packages。
        python = Path(args.python or sys.executable)
        if not python.is_file():
            print(f"解释器不存在: {python}", file=sys.stderr)
            return 2
    else:
        venv_dir = Path(args.venv_dir).resolve()
        venv_dir.parent.mkdir(parents=True, exist_ok=True)
        python = _ensure_venv(venv_dir)

    print(f"探针解释器: {python}", flush=True)
    print(f"依赖清单: {BFF_REQUIREMENTS}", flush=True)
    print("开始 import 检查:", flush=True)

    failures = run_ui_bootstrap_checks(python=python, repo_root=repo_root)
    if not failures:
        print(f"{CmdLayout.icon.i('success')} 全部通过。", flush=True)
        return 0

    print(f"\n失败 {len(failures)} 项:", file=sys.stderr, flush=True)
    for check, err in failures:
        print(f"\n--- {check.check_id} ---", file=sys.stderr, flush=True)
        if check.description:
            print(check.description, file=sys.stderr, flush=True)
        print(err, file=sys.stderr, flush=True)
    print(
        "\n提示: 将重依赖移入函数内 import，或把缺失包加入 core/bff/requirements.txt；"
        "工作台首请求栈需全量 requirements.txt，不在本检查范围。",
        file=sys.stderr,
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
