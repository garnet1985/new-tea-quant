#!/usr/bin/env python3
"""
全面检查 ProjectContext 的使用情况
"""

import os
import re
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path("/Users/garnet/Desktop/new-tea-quant")

def check_project_context_usage() -> Dict[str, List[str]]:
    """检查所有文件中 ProjectContext 的使用情况"""
    results = {
        "old_api_usage": [],      # 使用旧API（ctx.path.等）
        "ctx_instance": [],       # 还在创建ctx实例
        "import_errors": [],      # 导入错误
        "indent_errors": [],      # 缩进错误
        "correct_usage": [],      # 正确使用
    }
    
    # 找出所有Python文件
    python_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT / "core"):
        dirs[:] = [d for d in dirs if d not in ["venv", ".git", "__pycache__", "node_modules", "build"]]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    
    for file_path in python_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            rel_path = file_path.relative_to(PROJECT_ROOT)
            
            # 检查旧API使用（ctx.path.、ctx.config.、ctx.discovery.、ctx.load_python）
            old_api_patterns = [
                r"ctx\.path\.",
                r"ctx\.config\.",
                r"ctx\.discovery\.",
                r"ctx\.load_python",
                r"ctx\.file\.",
                r"ctx\.meta\.",
            ]
            
            for pattern in old_api_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    results["old_api_usage"].append(f"{rel_path}: 使用旧API {pattern}")
            
            # 检查还在创建ctx实例
            ctx_instance_pattern = r"ctx\s*=\s*ProjectContext\(\)"
            if re.search(ctx_instance_pattern, content):
                results["ctx_instance"].append(f"{rel_path}: 还在创建ctx实例")
            
            # 检查导入错误
            import_error_patterns = [
                r"from\s+core\.infra\.project_context\s+import\s+.*FileManager",
                r"from\s+core\.infra\.project_context\s+import\s+.*PathManager",
                r"from\s+core\.infra\.project_context\s+import\s+.*ConfigManager",
                r"from\s+core\.infra\.project_context\s+import\s+.*DiscoveryManager",
            ]
            
            for pattern in import_error_patterns:
                if re.search(pattern, content):
                    results["import_errors"].append(f"{rel_path}: 导入内部Manager")
            
            # 检查缩进错误（通过尝试编译）
            try:
                compile(content, str(file_path), 'exec')
            except IndentationError as e:
                results["indent_errors"].append(f"{rel_path}: 缩进错误 {e}")
            
            # 检查正确使用
            correct_patterns = [
                r"ProjectContext\.get_project_root\(\)",
                r"ProjectContext\.get_core_root\(\)",
                r"ProjectContext\.load_core_config\(\)",
                r"ProjectContext\.discover_strategies\(\)",
            ]
            
            for pattern in correct_patterns:
                if re.search(pattern, content):
                    results["correct_usage"].append(f"{rel_path}: 正确使用 {pattern}")
        
        except Exception as e:
            results["import_errors"].append(f"{rel_path}: 检查错误 {e}")
    
    return results

def main():
    """主函数"""
    print("🚀 开始全面检查 ProjectContext 使用情况...")
    
    results = check_project_context_usage()
    
    print(f"\n📊 检查结果：")
    print(f"  ❌ 旧API使用：{len(results['old_api_usage'])} 个文件")
    print(f"  ❌ 还在创建ctx实例：{len(results['ctx_instance'])} 个文件")
    print(f"  ❌ 导入错误：{len(results['import_errors'])} 个文件")
    print(f"  ❌ 缩进错误：{len(results['indent_errors'])} 个文件")
    print(f"  ✅ 正确使用：{len(results['correct_usage'])} 个文件")
    
    if results['old_api_usage']:
        print(f"\n❌ 旧API使用：")
        for item in results['old_api_usage'][:10]:
            print(f"  {item}")
        if len(results['old_api_usage']) > 10:
            print(f"  ... 还有 {len(results['old_api_usage']) - 10} 个")
    
    if results['ctx_instance']:
        print(f"\n❌ 还在创建ctx实例：")
        for item in results['ctx_instance'][:10]:
            print(f"  {item}")
    
    if results['import_errors']:
        print(f"\n❌ 导入错误：")
        for item in results['import_errors'][:10]:
            print(f"  {item}")
    
    if results['indent_errors']:
        print(f"\n❌ 缩进错误：")
        for item in results['indent_errors'][:10]:
            print(f"  {item}")
    
    if results['correct_usage']:
        print(f"\n✅ 正确使用（前10个）：")
        for item in results['correct_usage'][:10]:
            print(f"  {item}")

if __name__ == "__main__":
    main()