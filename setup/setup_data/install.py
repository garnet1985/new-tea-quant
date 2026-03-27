#!/usr/bin/env python3
"""
安装流程步骤：导入初始化数据（必跑）。

行为：
- 若 setup/init_data 无数据包：结束本步骤并明确提示如何导入
- 若有数据包：完整性检查 -> 创建清单 -> 按现有逻辑导入并显示进度
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

from setup.setup import NewTeaQuantSetup
from setup.setup_data.installer import SetupDataInstaller


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入 setup/init_data 初始化数据")
    parser.add_argument("--force", action="store_true", help="忽略清单并全量重导")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    inst = SetupDataInstaller(table_prefix="")
    inst.run(force=args.force, remove_extract=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
