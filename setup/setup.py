"""
安装流程共用工具（供根目录 install.py 与各 setup/*/install.py 使用）。

职责：仓库路径、sys.path、虚拟环境、打印、环境变量读取、单步子进程调用。
不包含：安装步骤顺序与编排（由根目录 install.py 负责）。

各子目录 install.py 负责该步的具体逻辑。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import ClassVar, Sequence


class NewTeaQuantSetup:
    """安装共用：路径、venv、打印、环境约定；不定义「要跑哪些步骤」。"""

    repo_root: ClassVar[Path] = Path(__file__).resolve().parent.parent
    venv_dir: ClassVar[Path] = repo_root / "venv"

    @classmethod
    def ensure_sys_path(cls) -> None:
        """将仓库根加入 sys.path，便于导入 core（幂等）。"""
        r = str(cls.repo_root)
        if r not in sys.path:
            sys.path.insert(0, r)

    @classmethod
    def venv_python(cls) -> Path:
        if os.name == "nt":
            return cls.venv_dir / "Scripts" / "python.exe"
        return cls.venv_dir / "bin" / "python"

    @staticmethod
    def in_virtualenv() -> bool:
        """标准库 venv：prefix 与 base_prefix 不同即视为在虚拟环境中。"""
        return sys.prefix != sys.base_prefix

    @classmethod
    def ensure_venv(cls) -> None:
        """未在 venv 中时创建 venv/ 并用其解释器替换当前进程，避免后续装到全局。"""
        if cls.in_virtualenv():
            print(f"使用虚拟环境解释器: {sys.executable}", flush=True)
            return
        raw = os.environ.get("NTQ_SKIP_AUTO_VENV", "").strip().lower()
        if raw in ("1", "true", "yes"):
            print(f"已跳过自动 venv，当前解释器: {sys.executable}", flush=True)
            return

        vpy = cls.venv_python()
        if not vpy.is_file():
            print("正在创建虚拟环境 venv/ …", flush=True)
            subprocess.run(
                [sys.executable, "-m", "venv", str(cls.venv_dir)],
                cwd=str(cls.repo_root),
                check=True,
            )
        else:
            print(f"检测到已有虚拟环境: {vpy}", flush=True)
        print(f"切换到虚拟环境解释器: {vpy}", flush=True)
        argv = [str(vpy), str(cls.repo_root / "install.py")] + sys.argv[1:]
        os.execv(str(vpy), argv)

    @classmethod
    def to_root_dir(cls) -> None:
        os.chdir(cls.repo_root)

    @classmethod
    def print_info(cls, title: str, msg: str, icon: str = None) -> None:
        icon_map = {
            "success": "✅",
            "green_dot": "🟢",
            "failed": "❌",
            "ongoing": "⏳",
        }
        icon_text = icon_map.get(icon, "")
        if icon:
            print(f"\n{icon_text} {title}: {msg}")
        else:
            print(f"\n{title}: {msg}")

    @classmethod
    def print_heading(cls, title: str, *, done: bool = False) -> None:
        line = "=" * 60
        prefix = "\n" if done else ""
        print(f"{prefix}{line}")
        print(f"  {title}")
        print(f"{line}\n")

    @staticmethod
    def print_check_item(status: str, msg: str) -> None:
        """
        统一 checklist 输出（ASCII）：
        - running: [..]
        - done:    [OK]
        - warn:    [WARN]
        - skip:    [SKIP]
        - fail:    [FAIL]
        """
        marks = {
            "running": "[..]",
            "done": "[OK]",
            "warn": "[WARN]",
            "skip": "[SKIP]",
            "fail": "[FAIL]",
        }
        mark = marks.get(status, "[ ]")
        print(f"{mark} {msg}", flush=True)

    @staticmethod
    def print_check_ok(msg: str) -> None:
        print(f"✅ {msg}", flush=True)

    @staticmethod
    def print_check_fail(msg: str) -> None:
        print(f"❌ {msg}", flush=True)

    @staticmethod
    def print_check_info(msg: str) -> None:
        print(f"-> {msg}", flush=True)

    @classmethod
    def check_file_exists(cls, path: Path, ok_msg: str, fail_msg: str) -> bool:
        if path.is_file():
            cls.print_check_ok(ok_msg)
            return True
        cls.print_check_fail(f"{fail_msg}: {path}")
        return False

    @classmethod
    def install_script_path(cls, step_name: str) -> Path:
        return cls.repo_root / "setup" / step_name / "install.py"

    @classmethod
    def run_install_script(cls, step_name: str, script_args: Sequence[str] = ()) -> int:
        script = cls.install_script_path(step_name)
        if not script.is_file():
            cls.print_check_item("fail", f"未找到步骤脚本: {script}")
            return 1
        cmd = [sys.executable, str(script), *script_args]
        r = subprocess.run(cmd, cwd=str(cls.repo_root), env=os.environ.copy())
        return int(r.returncode)
