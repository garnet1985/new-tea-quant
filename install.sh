#!/bin/bash
# 一键安装脚本 - 项目依赖
# 支持 macOS 和 Linux
# 支持中国网络环境（自动检测或通过 USE_CHINA_MIRROR=1 强制使用国内镜像）
#
# 可选：安装完成后导入 Demo 数据（需已配置数据库，且 userspace/demo_data 下存在 .zip）
#   INSTALL_DEMO_DATA=1 ./install.sh
#   ./install.sh --with-demo-data
# 非交互环境不会自动运行导入，请手动: python3 -m setup.demo_data_handler

set -e

# 可选 Demo 导入：环境变量 INSTALL_DEMO_DATA=1，或传参 --with-demo-data
INSTALL_DEMO_DATA="${INSTALL_DEMO_DATA:-0}"

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


# 安装 Python 依赖（实现位于 setup/resolve_dep/install_python_deps.sh）
install_python_deps() {
    print_step "安装 Python 依赖"
    if [ ! -f "setup/resolve_dep/install_python_deps.sh" ]; then
        print_error "未找到 setup/resolve_dep/install_python_deps.sh"
        exit 1
    fi
    export USE_CHINA_MIRROR
    bash "$SCRIPT_DIR/setup/resolve_dep/install_python_deps.sh"
}

# 可选：在依赖装完后导入 Demo 数据（失败不导致整脚本失败）
install_demo_data_optional() {
    if [ "$INSTALL_DEMO_DATA" != "1" ]; then
        return 0
    fi

    print_step "Demo 数据导入（可选）"
    print_info "将使用已配置的 config/database，并向带前缀（默认 test_）的表写入数据。"
    print_info "请确保 userspace/demo_data 下已放入官网提供的 .zip。"

    if [ ! -t 0 ] || [ ! -t 1 ]; then
        print_warning "当前为非交互终端，跳过自动导入 Demo。"
        print_info "配置数据库后可手动执行:"
        echo "    bash setup/run_demo_data.sh"
        echo "    非交互且目标表已有数据时追加: --confirm --yes"
        return 0
    fi

    if [ ! -f "setup/run_demo_data.sh" ]; then
        print_warning "未找到 setup/run_demo_data.sh，跳过 Demo 导入。"
        return 0
    fi

    print_info "启动 Demo 安装（终端将提示输入大写 YES 确认计划）..."
    set +e
    bash "$SCRIPT_DIR/setup/run_demo_data.sh"
    demo_exit=$?
    set -e
    if [ "$demo_exit" -eq 0 ]; then
        print_success "Demo 数据导入步骤已完成"
    else
        print_warning "Demo 数据导入未成功（exit=$demo_exit）。可检查 zip、数据库与表注册后重试。"
    fi
}

# 主函数
main() {
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$SCRIPT_DIR"

    echo -e "${GREEN}"
    echo "============================================================"
    echo "  New Tea Quant 一键安装脚本"
    echo "============================================================"
    echo -e "${NC}\n"

    print_step "检查 Python 版本"
    python3 setup/sys_req_check/sys_req_check.py
    print_success "Python 版本符合要求"
    
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

    # 识别 --with-demo-data（与 pip 安装无关，仅影响末尾是否尝试 Demo 导入）
    for _arg in "$@"; do
        if [ "$_arg" = "--with-demo-data" ]; then
            INSTALL_DEMO_DATA=1
            break
        fi
    done
    if [ "$INSTALL_DEMO_DATA" = "1" ]; then
        print_info "已启用 Demo 数据导入（INSTALL_DEMO_DATA=1 或 --with-demo-data）"
    fi
    
    # 安装 Python 依赖
    install_python_deps

    install_demo_data_optional
    
    echo -e "\n${GREEN}"
    echo "============================================================"
    echo "  安装完成！"
    echo "============================================================"
    echo -e "${NC}\n"
    
    print_info "下一步:"
    echo "  1. 配置数据库: python3 setup/db_init/db_install.py"
    echo "     或复制模板: python3 setup/db_init/db_install.py --from-examples"
    echo "  2. 建表: python3 setup/db_init/bootstrap_db.py"
    echo "  3. （可选）导入 Demo: bash setup/run_demo_data.sh"
    echo "     或在安装时: INSTALL_DEMO_DATA=1 ./install.sh  或  ./install.sh --with-demo-data"
    echo "  说明见 setup/README.md"
    echo ""
    if [ "$USE_CHINA_MIRROR" = "1" ]; then
        print_info "💡 提示: 当前使用国内镜像源，如遇到问题可尝试:"
        echo "    USE_CHINA_MIRROR=0 ./install.sh  # 使用官方源"
    fi
}

main "$@"
