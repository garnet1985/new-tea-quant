#!/usr/bin/env python3
"""
批量重构脚本：将 ProjectContextManager 从实例方法改为类方法

改动内容：
1. 删除 ctx = ProjectContextManager() 实例化语句
2. 将 ProjectContextManager.method() 改为 ProjectContextManager.method()
3. 删除多余的导入（PathManager、FileManager、ConfigManager、DiscoveryManager）
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 需要扫描的目录（排除venv、.git、__pycache__等）
SCAN_DIRS = [
    PROJECT_ROOT / "core",
    PROJECT_ROOT / "devtools",
]

# 排除的目录
EXCLUDE_DIRS = [
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
]

# 需要删除的导入（内部Manager）
INTERNAL_MANAGERS = ["PathManager", "FileManager", "ConfigManager", "DiscoveryManager"]


def find_python_files() -> List[Path]:
    """找出所有Python文件"""
    python_files = []
    for scan_dir in SCAN_DIRS:
        for root, dirs, files in os.walk(scan_dir):
            # 排除特定目录
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)
    return python_files


def refactor_file(file_path: Path) -> Tuple[bool, str]:
    """
    重构单个文件
    
    返回：(是否改动, 改动描述)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        
        # 1. 删除 ctx = ProjectContextManager() 实例化语句
        # 匹配模式：ctx = ProjectContextManager() 或         ctx_pattern = r"ctx\s*=\s*ProjectContextManager\(\s*\)\s*(#\s*module-level\s+instance\s*)?\n"
        content = re.sub(ctx_pattern, "", content)
        
        # 2. 将 ProjectContextManager.method() 改为 ProjectContextManager.method()
        # 匹配模式：ProjectContextManager.method_name(...)
        ctx_call_pattern = r"ctx\.(\w+)\("
        content = re.sub(ctx_call_pattern, r"ProjectContextManager.\1(", content)
        
        # 3. 删除多余的导入（内部Manager）
        # 匹配模式：from core.infra.project_context import ProjectContextManager
        for manager in INTERNAL_MANAGERS:
            # 删除导入中的内部Manager
            import_pattern = rf"from\s+core\.infra\.project_context\s+import\s+([^;\n]+)"
            
            def clean_import(match):
                imports_str = match.group(1)
                # 分割导入项
                imports = [item.strip() for item in imports_str.split(",")]
                # 删除内部Manager
                imports = [item for item in imports if item not in INTERNAL_MANAGERS]
                # 如果只剩ProjectContextManager，保留；否则删除整个导入语句
                if imports:
                    return f"from core.infra.project_context import {', '.join(imports)}"
                else:
                    return ""
            
            content = re.sub(import_pattern, clean_import, content)
        
        # 4. 删除多余的 from core.infra.project_context import PathManager 等单独导入
        for manager in INTERNAL_MANAGERS:
            single_import_pattern = rf"from\s+core\.infra\.project_context\s+import\s+{manager}\s*\n"
            content = re.sub(single_import_pattern, "", content)
        
        # 检查是否有改动
        if content != original_content:
            # 写回文件
            file_path.write_text(content, encoding="utf-8")
            return True, f"已更新 {file_path.relative_to(PROJECT_ROOT)}"
        else:
            return False, ""
            
    except Exception as e:
        return False, f"错误：{file_path} - {e}"


def main():
    """主函数"""
    print("🚀 开始批量重构 ProjectContextManager 为类方法...")
    
    python_files = find_python_files()
    print(f"📁 找到 {len(python_files)} 个Python文件")
    
    updated_files = []
    error_files = []
    
    for file_path in python_files:
        is_updated, message = refactor_file(file_path)
        if is_updated:
            updated_files.append(message)
        elif message.startswith("错误："):
            error_files.append(message)
    
    # 输出结果
    print(f"\n✅ 成功更新 {len(updated_files)} 个文件：")
    for msg in updated_files[:10]:  # 只显示前10个
        print(f"  {msg}")
    if len(updated_files) > 10:
        print(f"  ... 还有 {len(updated_files) - 10} 个文件")
    
    if error_files:
        print(f"\n❌ 错误文件：")
        for msg in error_files:
            print(f"  {msg}")
    
    print(f"\n🎉 批量重构完成！")


if __name__ == "__main__":
    main()