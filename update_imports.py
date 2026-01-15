#!/usr/bin/env python3
"""
导入语句更新脚本

将所有 `from app.core` 和 `import core` 更新为 `from core` 和 `import core`
"""

import re
from pathlib import Path
from typing import List, Tuple

# 需要更新的导入模式
IMPORT_PATTERNS = [
    # from core.xxx import yyy
    (r'from\s+app\.core\.', 'from core.'),
    # import core.xxx
    (r'import\s+app\.core\.', 'import core.'),
    # from core import xxx
    (r'from\s+app\.core\s+import', 'from core import'),
    # import core
    (r'import\s+app\.core\b', 'import core'),
]

def update_file_imports(file_path: Path) -> Tuple[int, List[str]]:
    """
    更新文件中的导入语句
    
    Returns:
        (更新数量, 更新的行列表)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            original_content = content
    except Exception as e:
        print(f"⚠️  读取文件失败: {file_path}, error={e}")
        return 0, []
    
    updated_lines = []
    changes_count = 0
    
    # 应用所有替换模式
    for pattern, replacement in IMPORT_PATTERNS:
        matches = list(re.finditer(pattern, content))
        if matches:
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                updated_lines.append(f"  Line {line_num}: {match.group()}")
            content = re.sub(pattern, replacement, content)
            changes_count += len(matches)
    
    # 如果有更新，写回文件
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_count, updated_lines
        except Exception as e:
            print(f"⚠️  写入文件失败: {file_path}, error={e}")
            return 0, []
    
    return 0, []

def find_python_files(root: Path) -> List[Path]:
    """查找所有 Python 文件"""
    python_files = []
    for path in root.rglob("*.py"):
        # 跳过备份目录和虚拟环境
        if any(skip in str(path) for skip in ['backup_', '__pycache__', '.venv', 'venv']):
            continue
        python_files.append(path)
    return python_files

def main():
    """主函数"""
    print("=" * 60)
    print("导入语句更新脚本")
    print("=" * 60)
    print("\n此脚本将更新所有 Python 文件中的导入语句：")
    print("  from core.xxx -> from core.xxx")
    print("  import core.xxx -> import core.xxx")
    print()
    
    response = input("是否继续? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ 取消更新")
        return
    
    # 获取项目根目录
    root = Path(__file__).parent.resolve()
    print(f"\n📂 项目根目录: {root}")
    
    # 查找所有 Python 文件
    print("\n🔍 查找 Python 文件...")
    python_files = find_python_files(root)
    print(f"✅ 找到 {len(python_files)} 个 Python 文件")
    
    # 更新文件
    print("\n📝 开始更新导入语句...")
    total_changes = 0
    updated_files = []
    
    for file_path in python_files:
        changes, lines = update_file_imports(file_path)
        if changes > 0:
            total_changes += changes
            updated_files.append((file_path, changes, lines))
            print(f"✅ {file_path.relative_to(root)}: {changes} 处更新")
    
    # 输出摘要
    print("\n" + "=" * 60)
    print("✅ 更新完成！")
    print("=" * 60)
    print(f"\n📊 统计：")
    print(f"  - 更新文件数: {len(updated_files)}")
    print(f"  - 总更新数: {total_changes}")
    
    if updated_files:
        print(f"\n📋 更新的文件列表：")
        for file_path, changes, lines in updated_files[:20]:  # 只显示前20个
            print(f"  - {file_path.relative_to(root)} ({changes} 处)")
        if len(updated_files) > 20:
            print(f"  ... 还有 {len(updated_files) - 20} 个文件")
    
    print("\n下一步：")
    print("1. 检查更新结果（git diff）")
    print("2. 运行测试验证功能正常")
    print("3. 如果一切正常，提交更改")

if __name__ == "__main__":
    main()
