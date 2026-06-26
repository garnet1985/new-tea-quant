"""
清理 api.yaml 文件，删除所有 deprecated API

删除所有 stability: deprecated 的API定义
"""
import re
from pathlib import Path


def clean_api_yaml():
    """清理 api.yaml 文件"""
    api_yaml_path = Path("/Users/garnet/Desktop/new-tea-quant/core/infra/project_context/api.yaml")

    content = api_yaml_path.read_text(encoding='utf-8')

    # 删除所有 deprecated API定义
    # 使用正则表达式匹配整个deprecated API块
    pattern = r'    [a-zA-Z_]+(?:\([^)]*\))?:\s*\n(?:.*?\n)*?      stability: deprecated\s*\n(?:.*?\n)*?      deprecated_reason:.*?\n'

    # 替换为空字符串
    cleaned_content = re.sub(pattern, '', content)

    # 同时删除 "# Deprecated APIs" 注释行
    cleaned_content = re.sub(r'    # Deprecated APIs.*?\n', '', cleaned_content)

    # 删除多余的空行（超过2个连续空行）
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)

    api_yaml_path.write_text(cleaned_content, encoding='utf-8')

    print(f"✅ Cleaned {api_yaml_path}")


if __name__ == "__main__":
    clean_api_yaml()