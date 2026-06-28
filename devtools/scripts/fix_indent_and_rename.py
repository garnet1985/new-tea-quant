#!/usr/bin/env python3
"""
批量修复问题：
1. 修复缩进问题（test_project_context_manager.py和api.yaml）
2. 重命名ProjectContextManager为ProjectContext
3. 版本号从0.5.0改为0.4.0
"""

import os
import re
from pathlib import Path
from typing import List

# 项目根目录
PROJECT_ROOT = Path("/Users/garnet/Desktop/new-tea-quant")

# 需要修复缩进的文件
FIX_INDENT_FILES = [
    PROJECT_ROOT / "core/infra/project_context/__test__/test_project_context_manager.py",
    PROJECT_ROOT / "core/infra/project_context/api.yaml",
]

def fix_indent_test_file(file_path: Path):
    """修复test_project_context_manager.py的缩进"""
    content = file_path.read_text(encoding="utf-8")
    
    # 修复错误的缩进（删除多余的空格）
    # 模式：方法内的代码行有多余缩进
    lines = content.split("\n")
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 检查是否是方法定义
        if line.strip().startswith("def test_"):
            fixed_lines.append(line)
            continue
        
        # 检查是否是方法内的代码（应该有正确的缩进）
        if line.strip() and not line.strip().startswith("#"):
            # 检查前一行是否是方法定义或空行
            prev_line = lines[i-1] if i > 0 else ""
            if prev_line.strip().startswith("def test_") or not prev_line.strip():
                # 如果前一行是方法定义或空行，这行应该有8个空格（方法内第一行）
                if line.startswith("                "):
                    # 将16个空格改为8个空格
                    line = line[8:]
        
        fixed_lines.append(line)
    
    content = "\n".join(fixed_lines)
    file_path.write_text(content, encoding="utf-8")
    print(f"✅ 已修复缩进：{file_path.relative_to(PROJECT_ROOT)}")

def fix_indent_yaml_file(file_path: Path):
    """修复api.yaml的缩进"""
    content = file_path.read_text(encoding="utf-8")
    
    # 修复example字段的缩进
    # 模式：example字段内有多余缩进
    lines = content.split("\n")
    fixed_lines = []
    
    in_example = False
    for i, line in enumerate(lines):
        # 检查是否进入example字段
        if "example:" in line:
            in_example = True
            fixed_lines.append(line)
            continue
        
        # 检查是否离开example字段（下一个字段）
        if in_example and line.strip() and not line.startswith(" ") and ":" in line:
            in_example = False
        
        # 如果在example字段内，修复缩进
        if in_example and line.strip():
            # example字段内的代码应该有正确的缩进（2个空格）
            if line.startswith("                "):
                # 将16个空格改为8个空格（example字段内应该有8个空格）
                line = line[8:]
        
        fixed_lines.append(line)
    
    content = "\n".join(fixed_lines)
    file_path.write_text(content, encoding="utf-8")
    print(f"✅ 已修复缩进：{file_path.relative_to(PROJECT_ROOT)}")

def rename_project_context_manager():
    """重命名ProjectContextManager为ProjectContext"""
    # 找出所有Python文件
    python_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT / "core"):
        dirs[:] = [d for d in dirs if d not in ["venv", ".git", "__pycache__"]]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    
    # 批量重命名
    renamed_count = 0
    for file_path in python_files:
        content = file_path.read_text(encoding="utf-8")
        
        # 检查是否包含ProjectContextManager
        if "ProjectContextManager" in content:
            # 重命名
            content = content.replace("ProjectContextManager", "ProjectContext")
            file_path.write_text(content, encoding="utf-8")
            renamed_count += 1
    
    print(f"✅ 已重命名 {renamed_count} 个文件（ProjectContextManager → ProjectContext）")

def update_version_to_0_4_0():
    """将版本号从0.5.0改为0.4.0"""
    files_to_update = [
        PROJECT_ROOT / "core/infra/project_context/api.yaml",
        PROJECT_ROOT / "core/infra/project_context/module_info.yaml",
        PROJECT_ROOT / "core/infra/project_context/docs/ARCHITECTURE.md",
        PROJECT_ROOT / "core/infra/project_context/docs/DESIGN.md",
        PROJECT_ROOT / "core/infra/project_context/docs/DECISIONS.md",
    ]
    
    for file_path in files_to_update:
        content = file_path.read_text(encoding="utf-8")
        
        # 替换版本号
        content = content.replace("0.5.0", "0.4.0")
        content = content.replace("0.5.1", "0.4.0")
        
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ 已更新版本号：{file_path.relative_to(PROJECT_ROOT)}")

def main():
    """主函数"""
    import os
    
    print("🚀 开始批量修复问题...")
    
    # 1. 修复缩进问题
    print("\n📁 修复缩进问题...")
    fix_indent_test_file(FIX_INDENT_FILES[0])
    fix_indent_yaml_file(FIX_INDENT_FILES[1])
    
    # 2. 重命名ProjectContextManager为ProjectContext
    print("\n📝 重命名...")
    rename_project_context_manager()
    
    # 3. 更新版本号
    print("\n🔢 更新版本号...")
    update_version_to_0_4_0()
    
    print("\n🎉 批量修复完成！")

if __name__ == "__main__":
    main()