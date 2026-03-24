"""
安装流程共用工具（供根目录 install.py 与各 setup/*/install.py 使用）。

职责：仓库路径、sys.path、虚拟环境、打印、环境变量读取、单步子进程调用。
不包含：安装步骤顺序与编排（由根目录 install.py 负责）。

各子目录 install.py 负责该步的具体逻辑。
"""
from __future__ import annotations

import os
import platform
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
            return
        raw = os.environ.get("NTQ_SKIP_AUTO_VENV", "").strip().lower()
        if raw in ("1", "true", "yes"):
            return

        vpy = cls.venv_python()
        if not vpy.is_file():
            print("正在创建虚拟环境 venv/ …", flush=True)
            subprocess.run(
                [sys.executable, "-m", "venv", str(cls.venv_dir)],
                cwd=str(cls.repo_root),
                check=True,
            )
        argv = [str(vpy), str(cls.repo_root / "install.py")] + sys.argv[1:]
        os.execv(str(vpy), argv)

    @classmethod
    def to_root_dir(cls) -> None:
        os.chdir(cls.repo_root)

    @classmethod    
    def print_info(cls, title: str, msg: str, icon: str = None) -> None:
        cls.ensure_sys_path()
        from core.utils import i
        if icon:
            print(f"\n{i(icon)} {title}: {msg}")
        else:
            print(f"\n{title}: {msg}")

    @classmethod
    def print_heading(cls, title: str, *, done: bool = False) -> None:
        line = "=" * 60
        prefix = "\n" if done else ""
        print(f"{prefix}{line}")
        print(f"  {title}")
        print(f"{line}\n")

    # def use_china_mirror(self) -> bool:
    #     raw = os.environ.get("USE_CHINA_MIRROR", "").strip().lower()
    #     return raw in ("1", "true", "yes")

    # def should_import_demo_data(self) -> bool:
    #     return os.environ.get("INSTALL_DEMO_DATA", "0").strip() == "1"

    # def install_script_path(self, step_name: str) -> Path:
    #     """setup/<step_name>/install.py"""
    #     return self.root / "setup" / step_name / "install.py"

    # def run_install_script(
    #     self,
    #     step_name: str,
    #     script_args: Sequence[str] = (),
    # ) -> int:
    #     """
    #     以当前解释器执行 setup/<step_name>/install.py，并传入 script_args 作为其命令行参数。
    #     返回子进程退出码；脚本不存在时返回 1。
    #     """
    #     script = self.install_script_path(step_name)
    #     if not script.is_file():
    #         self.print_info("错误", f"未找到步骤脚本: {script}", "failed")
    #         return 1
    #     cmd = [sys.executable, str(script), *script_args]
    #     r = subprocess.run(
    #         cmd,
    #         cwd=str(self.root),
    #         env=os.environ.copy(),
    #     )
    #     return int(r.returncode)
