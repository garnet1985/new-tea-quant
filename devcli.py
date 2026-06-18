#!/usr/bin/env python3
# NTQ 开发 CLI。与 python devcli.py -h 相同；维护请改 core/infra/devcli/help_text.py
#
# 规则: xx=命令  -v=版本  --xx=对象参数
#
# python devcli.py ui                      启动 UI
# python devcli.py csc                     清策略模拟缓存
# python devcli.py p -core_v0.3.2          发布检查
# python devcli.py ssp 500                 分层样本池
#
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.infra.devcli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
