#!/usr/bin/env bash
# 导入 Demo 数据（zip 放在 userspace/demo_data/）
# 等价于: python3 -m setup.demo_data_handler
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 -m setup.demo_data_handler "$@"
