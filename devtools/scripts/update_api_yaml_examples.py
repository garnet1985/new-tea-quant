#!/usr/bin/env python3
"""
批量更新api.yaml的示例代码，改为类方法调用方式
"""

from core.infra.cmd_layout import i

import re
from pathlib import Path

# api.yaml 文件路径
API_YAML_FILE = Path("/Users/garnet/Desktop/new-tea-quant/core/infra/project_context/api.yaml")

def update_api_yaml():
    """更新api.yaml"""
    content = API_YAML_FILE.read_text(encoding="utf-8")
    
    # 1. 删除 ctx = ProjectContextManager() 实例化语句
    ctx_pattern = r"ctx = ProjectContextManager\(\)\s*\n"
    content = re.sub(ctx_pattern, "", content)
    
    # 2. 将 ctx.method() 改为 ProjectContextManager.method()
    ctx_call_pattern = r"ctx\.(\w+)\("
    content = re.sub(ctx_call_pattern, r"ProjectContextManager.\1(", content)
    
    # 3. 更新版本号（从0.4.0改为0.5.0）
    content = content.replace("# Version: 0.4.0", "# Version: 0.5.0")
    
    # 4. 添加改动说明
    description_pattern = r"description: \"项目上下文管理器 - Facade，对外唯一入口\""
    new_description = "description: \"项目上下文管理器 - Facade，对外唯一入口（v0.5.0改为类方法，调用更简洁）\""
    content = re.sub(description_pattern, new_description, content)
    
    # 写回文件
    API_YAML_FILE.write_text(content, encoding="utf-8")
    print(f"{i('success')} 已更新 api.yaml")

if __name__ == "__main__":
    update_api_yaml()