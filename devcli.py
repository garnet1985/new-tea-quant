#!/usr/bin/env python3
"""
开发常用命令（仓库根目录）。

语义与缩写等价，例如::

    python devcli.py ui run
    python devcli.py -ui

完整说明::

    python devcli.py -h
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.infra.devcli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
