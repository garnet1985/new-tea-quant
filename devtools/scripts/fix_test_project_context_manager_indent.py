#!/usr/bin/env python3
"""
重新修复test_project_context_manager.py的缩进问题
"""

from pathlib import Path

TEST_FILE = Path("/Users/garnet/Desktop/new-tea-quant/core/infra/project_context/__test__/test_project_context_manager.py")

def fix_indent():
    """修复缩进"""
    content = TEST_FILE.read_text(encoding="utf-8")
    
    # 删除多余的缩进（8个空格）
    lines = content.split("\n")
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 检查是否是方法定义
        if line.strip().startswith("def test_"):
            fixed_lines.append(line)
            continue
        
        # 检查是否是方法内的代码（应该有正确的缩进）
        if line.strip() and not line.strip().startswith("#"):
            # 如果这行有多余的缩进（超过8个空格），删除多余的8个空格
            if line.startswith("                "):
                line = line[8:]
        
        fixed_lines.append(line)
    
    content = "\n".join(fixed_lines)
    
    # 删除ctx变量相关的测试（因为现在是类方法，不需要实例）
    # 删除 test_is_api_implementation 和 test_init
    import re
    
    # 删除 test_is_api_implementation
    pattern1 = r"def test_is_api_implementation\(self\):\s*\n\s*\"\"\"测试是否实现了 ProjectContextAPI\"\"\"\s*\n\s*assert isinstance\(ctx, ProjectContextAPI\)\s*\n"
    content = re.sub(pattern1, "", content)
    
    # 删除 test_init
    pattern2 = r"def test_init\(self\):\s*\n\s*\"\"\"测试初始化\"\"\"\s*\n\s*# 验证实例创建成功\s*\n\s*assert ctx is not None\s*\n"
    content = re.sub(pattern2, "", content)
    
    # 删除所有 ctx 引用
    content = re.sub(r"ctx", "", content)
    
    TEST_FILE.write_text(content, encoding="utf-8")
    print("✅ 已修复 test_project_context_manager.py 的缩进问题")

if __name__ == "__main__":
    fix_indent()