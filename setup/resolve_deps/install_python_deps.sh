#!/usr/bin/env bash
# 安装 Python 依赖（requirements.txt）
# 在仓库根目录执行；由根目录 install.py 间接使用，也可单独运行：
#   USE_CHINA_MIRROR=1 bash setup/resolve_dep/install_python_deps.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

USE_CHINA_MIRROR="${USE_CHINA_MIRROR:-0}"

# 与根 install.py 行为一致：可选写入 ~/.pip/pip.conf
_setup_pip_mirror() {
    if [ "$USE_CHINA_MIRROR" != "1" ]; then
        return 0
    fi
    echo "ℹ️  配置 pip 使用国内镜像源（清华）..."
    PIP_CONFIG_DIR="${HOME}/.pip"
    mkdir -p "$PIP_CONFIG_DIR"
    cat > "$PIP_CONFIG_DIR/pip.conf" <<'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
    echo "✅ pip 镜像配置完成"
}

if [ ! -f "requirements.txt" ]; then
    echo "❌ 未找到 requirements.txt（请在仓库根目录运行）" >&2
    exit 1
fi

_setup_pip_mirror

echo "ℹ️  安装 Python 包..."
if [ "$USE_CHINA_MIRROR" = "1" ]; then
    pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
else
    pip3 install -r requirements.txt
fi

echo "✅ Python 依赖安装成功"
