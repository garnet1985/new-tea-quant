#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安装脚本 - 自动安装项目依赖

支持平台：
- macOS
- Linux
- Windows
"""
import sys
import subprocess
import platform
import shutil
import os
from pathlib import Path
from typing import Optional, Tuple

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_step(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}📦 {msg}{Colors.RESET}\n")


def run_command(cmd: list, check: bool = True, capture_output: bool = False) -> Tuple[int, str, str]:
    """
    运行命令
    
    Returns:
        (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
        stdout = result.stdout if capture_output else ""
        stderr = result.stderr if capture_output else ""
        return result.returncode, stdout, stderr
    except subprocess.CalledProcessError as e:
        if capture_output:
            return e.returncode, e.stdout or "", e.stderr or ""
        return e.returncode, "", ""


def check_command_exists(cmd: str) -> bool:
    """检查命令是否存在"""
    return shutil.which(cmd) is not None


def detect_os() -> str:
    """检测操作系统"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    else:
        return "unknown"




def install_python_dependencies() -> bool:
    """安装 Python 依赖"""
    print_step("安装 Python 依赖")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print_error(f"未找到 requirements.txt: {requirements_file}")
        return False
    
    
    print_info("安装 Python 包...")
    returncode, _, _ = run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
        check=False
    )
    
    if returncode == 0:
        print_success("Python 依赖安装成功！")
        return True
    else:
        print_error("Python 依赖安装失败")
        return False




def main():
    """主函数"""
    print(f"{Colors.BOLD}{Colors.GREEN}")
    print("=" * 60)
    print("  stocks-py 一键安装脚本")
    print("=" * 60)
    print(f"{Colors.RESET}\n")
    
    # 检测操作系统
    os_type = detect_os()
    print_info(f"检测到操作系统: {os_type}")
    
    # 安装 Python 依赖
    if not install_python_dependencies():
        print_error("Python 依赖安装失败")
        sys.exit(1)
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("=" * 60)
    print("  安装完成！")
    print("=" * 60)
    print(f"{Colors.RESET}\n")
    print_info("下一步:")
    print("  1. 配置数据库连接 (config/database/db_config.json)")
    print("  2. 运行迁移脚本迁移数据")


if __name__ == "__main__":
    main()
