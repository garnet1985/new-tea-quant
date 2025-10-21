#!/usr/bin/env python3
"""
RTB策略快速启动工具
提供常用的RTB策略分析和优化功能

使用方法:
    python rtb_quick_start.py [command] [options]

可用命令:
    analyze      - 分析RTB交易结果
    compare      - 对比RTB和脚本识别的反转点
    optimize     - 优化RTB条件
    simulate     - 运行RTB策略模拟
    help         - 显示帮助信息

示例:
    python rtb_quick_start.py analyze
    python rtb_quick_start.py compare
    python rtb_quick_start.py optimize
    python rtb_quick_start.py simulate
"""

import sys
import os
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def run_command(script_path, *args):
    """运行指定的脚本"""
    try:
        cmd = [sys.executable, str(script_path)] + list(args)
        # 确保在项目根目录下运行，并设置PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        result = subprocess.run(cmd, cwd=project_root, env=env, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        return False

def analyze_results():
    """分析RTB交易结果"""
    print("🔍 开始分析RTB交易结果...")
    script_path = project_root / "app" / "analyzer" / "strategy" / "RTB" / "ml" / "analyze_rtb_trading_results.py"
    return run_command(script_path)

def compare_reversals():
    """对比RTB和脚本识别的反转点"""
    print("🔄 开始对比RTB和脚本识别的反转点...")
    script_path = project_root / "app" / "analyzer" / "strategy" / "RTB" / "ml" / "compare_rtb_vs_script_reversals.py"
    return run_command(script_path)

def optimize_conditions():
    """优化RTB条件"""
    print("⚡ 开始优化RTB条件...")
    script_path = project_root / "app" / "analyzer" / "strategy" / "RTB" / "ml" / "simple_rtb_condition_optimization.py"
    return run_command(script_path)

def run_simulation():
    """运行RTB策略模拟"""
    print("🚀 开始运行RTB策略模拟...")
    script_path = project_root / "start.py"
    return run_command(script_path)

def show_help():
    """显示帮助信息"""
    print(__doc__)
    print("\n📁 RTB相关文件位置:")
    print("   策略代码: app/analyzer/strategy/RTB/")
    print("   机器学习: app/analyzer/strategy/RTB/ml/")
    print("   特征识别: app/analyzer/strategy/RTB/feature_identity/")
    print("   模拟结果: app/analyzer/strategy/RTB/tmp/")
    
    print("\n🔧 常用工作流程:")
    print("   1. 运行模拟: python rtb_quick_start.py simulate")
    print("   2. 分析结果: python rtb_quick_start.py analyze")
    print("   3. 对比反转点: python rtb_quick_start.py compare")
    print("   4. 优化条件: python rtb_quick_start.py optimize")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "analyze":
        success = analyze_results()
    elif command == "compare":
        success = compare_reversals()
    elif command == "optimize":
        success = optimize_conditions()
    elif command == "simulate":
        success = run_simulation()
    elif command in ["help", "-h", "--help"]:
        show_help()
        return
    else:
        print(f"❌ 未知命令: {command}")
        print("使用 'python rtb_quick_start.py help' 查看可用命令")
        return
    
    if success:
        print("✅ 操作完成！")
    else:
        print("❌ 操作失败！")

if __name__ == "__main__":
    main()
