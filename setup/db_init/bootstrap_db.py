#!/usr/bin/env python3
"""
连接数据库并创建 Base Tables（DataManager.initialize）。

前置：已配置 userspace/config/database/（见 setup/db_init/db_install.py）。
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        from core.modules.data_manager import DataManager

        dm = DataManager(is_verbose=True)
        dm.initialize()
    except Exception as e:
        logger.exception("bootstrap 失败: %s", e)
        sys.exit(1)
    print("✅ 数据库连接与 Base Tables 建表流程已完成", file=sys.stderr)


if __name__ == "__main__":
    main()
