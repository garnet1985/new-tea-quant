#!/usr/bin/env python3
"""
清理test_api.py中的fixture和ctx参数（因为改为类方法）
"""

from core.infra.cmd_layout import i

import re
from pathlib import Path

# test_api.py 文件路径
TEST_API_FILE = Path("/Users/garnet/Desktop/new-tea-quant/core/infra/project_context/__test__/test_api.py")

def clean_test_api():
    """清理test_api.py"""
    content = TEST_API_FILE.read_text(encoding="utf-8")
    
    # 1. 删除 @pytest.fixture def ctx(self): fixture定义
    fixture_pattern = r"@pytest\.fixture\s*\n\s*def ctx\(self\):\s*\n\s*\"\"\"创建ProjectContextManager实例\"\"\"\s*\n\s*return ProjectContextManager\(\)\s*\n"
    content = re.sub(fixture_pattern, "", content)
    
    # 2. 删除测试方法中的 ctx 参数
    ctx_param_pattern = r"def (\w+)\(self, ctx(, \w+)?\):"
    
    def clean_ctx_param(match):
        method_name = match.group(1)
        other_param = match.group(2) or ""
        if other_param:
            return f"def {method_name}(self{other_param}):"
        else:
            return f"def {method_name}(self):"
    
    content = re.sub(ctx_param_pattern, clean_ctx_param, content)
    
    # 3. 修改测试方法名称
    content = content.replace(
        "test_all_api_methods_are_instance_methods",
        "test_all_api_methods_are_classmethods"
    )
    
    # 4. 修改测试描述
    content = content.replace(
        """验证所有API方法都是实例方法""",
        """验证所有API方法都是类方法"""
    )
    
    # 写回文件
    TEST_API_FILE.write_text(content, encoding="utf-8")
    print(f"{i('success')} 已清理 test_api.py")

if __name__ == "__main__":
    clean_test_api()