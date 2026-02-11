#!/bin/bash
# 一键安装脚本 - 项目依赖
# 支持 macOS 和 Linux
# 支持中国网络环境（自动检测或通过 USE_CHINA_MIRROR=1 强制使用国内镜像）

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo -e "\n${BLUE}📦 $1${NC}\n"
}

# 检测是否使用国内镜像
# 可以通过环境变量强制指定: USE_CHINA_MIRROR=1 ./install.sh
USE_CHINA_MIRROR="${USE_CHINA_MIRROR:-0}"

# 如果未设置，尝试自动检测（检测 DNS 解析时间或 IP 地理位置）
if [ "$USE_CHINA_MIRROR" = "0" ]; then
    # 简单检测：尝试 ping GitHub，如果超时则可能在中国
    # 注意：timeout 命令在某些系统可能不可用，使用更兼容的方式
    if command -v timeout >/dev/null 2>&1; then
        if timeout 2 ping -c 1 github.com >/dev/null 2>&1; then
            USE_CHINA_MIRROR=0
        else
            USE_CHINA_MIRROR=1
            print_info "检测到网络环境可能较慢，将使用国内镜像源"
        fi
    else
        # 如果没有 timeout 命令，尝试直接 ping（macOS 默认没有 timeout）
        if ping -c 1 -W 2000 github.com >/dev/null 2>&1 2>/dev/null || ping -c 1 -t 2 github.com >/dev/null 2>&1; then
            USE_CHINA_MIRROR=0
        else
            USE_CHINA_MIRROR=1
            print_info "检测到网络环境可能较慢，将使用国内镜像源"
        fi
    fi
fi

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}


# 配置 Homebrew 国内镜像（清华源）
setup_brew_mirror() {
    if [ "$USE_CHINA_MIRROR" = "1" ]; then
        print_info "配置 Homebrew 使用国内镜像源（清华）..."
        
        # 替换 Homebrew 源
        export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git"
        export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git"
        export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles"
        
        # 如果 brew 已安装，更新镜像配置
        if command_exists brew; then
            git -C "$(brew --repo)" remote set-url origin https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git 2>/dev/null || true
            git -C "$(brew --repo homebrew/core)" remote set-url origin https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git 2>/dev/null || true
            print_success "Homebrew 镜像配置完成"
        fi
    fi
}

# macOS 安装（无需额外系统依赖）
install_macos() {
    print_info "检测到 macOS 系统"
    # macOS 系统无需额外安装，直接安装 Python 依赖即可
}

# Linux 安装（无需额外系统依赖）
install_linux() {
    print_info "检测到 Linux 系统"
    # Linux 系统无需额外安装，直接安装 Python 依赖即可
}


# 配置 pip 国内镜像
setup_pip_mirror() {
    if [ "$USE_CHINA_MIRROR" = "1" ]; then
        print_info "配置 pip 使用国内镜像源（清华）..."
        
        # 创建 pip 配置目录
        PIP_CONFIG_DIR="$HOME/.pip"
        mkdir -p "$PIP_CONFIG_DIR"
        
        # 创建或更新 pip.conf
        cat > "$PIP_CONFIG_DIR/pip.conf" <<EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
        print_success "pip 镜像配置完成"
    fi
}

# 安装 Python 依赖
install_python_deps() {
    print_step "安装 Python 依赖"
    
    if [ ! -f "requirements.txt" ]; then
        print_error "未找到 requirements.txt"
        exit 1
    fi
    
    # 配置 pip 镜像
    setup_pip_mirror
    
    
    print_info "安装 Python 包..."
    if [ "$USE_CHINA_MIRROR" = "1" ]; then
        pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
    else
        pip3 install -r requirements.txt
    fi
    
    print_success "Python 依赖安装成功！"
}

# 主函数
main() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "  New Tea Quant 一键安装脚本"
    echo "============================================================"
    echo -e "${NC}\n"
    
    # 显示镜像源配置信息
    if [ "$USE_CHINA_MIRROR" = "1" ]; then
        print_info "🌏 使用国内镜像源模式"
        print_info "   如需使用官方源，请设置: USE_CHINA_MIRROR=0 ./install.sh"
    else
        print_info "🌍 使用官方源模式"
        print_info "   如需使用国内镜像，请设置: USE_CHINA_MIRROR=1 ./install.sh"
    fi
    echo ""
    
    OS_TYPE=$(detect_os)
    print_info "检测到操作系统: $OS_TYPE"
    
    # 安装 Python 依赖
    install_python_deps
    
    echo -e "\n${GREEN}"
    echo "============================================================"
    echo "  安装完成！"
    echo "============================================================"
    echo -e "${NC}\n"
    
    print_info "下一步:"
    echo "  1. 配置数据库连接 (config/database/db_config.json)"
    echo "  2. 运行迁移脚本迁移数据"
    echo ""
    if [ "$USE_CHINA_MIRROR" = "1" ]; then
        print_info "💡 提示: 当前使用国内镜像源，如遇到问题可尝试:"
        echo "    USE_CHINA_MIRROR=0 ./install.sh  # 使用官方源"
    fi
}

main "$@"
