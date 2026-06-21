import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_python() -> Path:
    """发布/开发检查优先使用仓库 ``venv`` 解释器（含 Flask 等 dev 依赖）。"""
    if os.name == "nt":
        vpy = REPO_ROOT / "venv" / "Scripts" / "python.exe"
    else:
        vpy = REPO_ROOT / "venv" / "bin" / "python"
    if vpy.is_file():
        return vpy
    return Path(sys.executable)
