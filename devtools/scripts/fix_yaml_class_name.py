#!/usr/bin/env python3
"""
更新yaml文件中的命名：ProjectContextManager → ProjectContext
"""

import re
from pathlib import Path
import os

# 项目根目录
PROJECT_ROOT = Path("/Users/garnet/Desktop/new-tea-quant")

def update_yaml_files():
    """更新所有yaml文件"""
    # 找出所有yaml文件
    yaml_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT / "core"):
        dirs[:] = [d for d in dirs if d not in ["venv", ".git", "__pycache__"]]
        for file in files:
            if file.endswith(".yaml") or file.endswith(".yml"):
                yaml_files.append(Path(root) / file)
    
    # 更新yaml文件
    for file_path in yaml_files:
        content = file_path.read_text(encoding="utf-8")
        
        # 检查是否包含ProjectContextManager
        if "ProjectContextManager" in content:
            # 重命名
            content = content.replace("ProjectContextManager", "ProjectContext")
            file_path.write_text(content, encoding="utf-8")
            print(f"✅ 已更新：{file_path.relative_to(PROJECT_ROOT)}")

if __name__ == "__main__":
    print("🚀 开始更新yaml文件...")
    update_yaml_files()
    print("🎉 更新完成！")