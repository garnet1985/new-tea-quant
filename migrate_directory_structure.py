#!/usr/bin/env python3
"""
目录结构迁移脚本

将 app/core 和 app/userspace 移动到项目根目录
"""

import shutil
import sys
from pathlib import Path
from typing import List, Tuple

def backup_directories(root: Path) -> bool:
    """备份要移动的目录"""
    print("📦 开始备份...")
    
    app_dir = root / "app"
    if not app_dir.exists():
        print("❌ app/ 目录不存在，无需迁移")
        return False
    
    backup_dir = root / "backup_before_migration"
    if backup_dir.exists():
        print(f"⚠️  备份目录已存在: {backup_dir}")
        response = input("是否删除旧备份并重新备份? (y/n): ")
        if response.lower() != 'y':
            print("❌ 取消备份")
            return False
        shutil.rmtree(backup_dir)
    
    try:
        # 只备份 core 和 userspace
        backup_dir.mkdir(exist_ok=True)
        if (app_dir / "core").exists():
            shutil.copytree(app_dir / "core", backup_dir / "core")
            print(f"✅ 已备份: app/core -> backup_before_migration/core")
        if (app_dir / "userspace").exists():
            shutil.copytree(app_dir / "userspace", backup_dir / "userspace")
            print(f"✅ 已备份: app/userspace -> backup_before_migration/userspace")
        
        print("✅ 备份完成")
        return True
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return False

def move_directories(root: Path) -> bool:
    """移动目录"""
    print("\n📁 开始移动目录...")
    
    app_dir = root / "app"
    if not app_dir.exists():
        print("❌ app/ 目录不存在")
        return False
    
    moved = []
    
    # 移动 core
    core_src = app_dir / "core"
    core_dst = root / "core"
    if core_src.exists():
        if core_dst.exists():
            print(f"⚠️  目标目录已存在: {core_dst}")
            response = input("是否删除并覆盖? (y/n): ")
            if response.lower() != 'y':
                print("❌ 取消移动 core")
                return False
            shutil.rmtree(core_dst)
        
        try:
            shutil.move(str(core_src), str(core_dst))
            moved.append(("core", core_src, core_dst))
            print(f"✅ 已移动: app/core -> core")
        except Exception as e:
            print(f"❌ 移动 core 失败: {e}")
            return False
    
    # 移动 userspace
    userspace_src = app_dir / "userspace"
    userspace_dst = root / "userspace"
    if userspace_src.exists():
        if userspace_dst.exists():
            print(f"⚠️  目标目录已存在: {userspace_dst}")
            response = input("是否删除并覆盖? (y/n): ")
            if response.lower() != 'y':
                print("❌ 取消移动 userspace")
                return False
            shutil.rmtree(userspace_dst)
        
        try:
            shutil.move(str(userspace_src), str(userspace_dst))
            moved.append(("userspace", userspace_src, userspace_dst))
            print(f"✅ 已移动: app/userspace -> userspace")
        except Exception as e:
            print(f"❌ 移动 userspace 失败: {e}")
            # 回滚
            for name, src, dst in reversed(moved):
                print(f"🔄 回滚: {dst} -> {src}")
                shutil.move(str(dst), str(src))
            return False
    
    print("✅ 目录移动完成")
    return True

def check_app_dir_empty(root: Path) -> bool:
    """检查 app 目录是否为空（除了可能的 __pycache__ 等）"""
    app_dir = root / "app"
    if not app_dir.exists():
        return True
    
    # 忽略一些常见文件/目录
    ignore = {'__pycache__', '.pyc', '.pyo', '.DS_Store', '.git'}
    
    items = [item for item in app_dir.iterdir() 
             if item.name not in ignore and not item.name.startswith('.')]
    
    return len(items) == 0

def main():
    """主函数"""
    print("=" * 60)
    print("目录结构迁移脚本")
    print("=" * 60)
    print("\n此脚本将执行以下操作：")
    print("1. 备份 app/core 和 app/userspace")
    print("2. 移动 app/core -> core")
    print("3. 移动 app/userspace -> userspace")
    print("\n⚠️  警告：此操作不可逆，请确保已提交代码到版本控制！")
    print()
    
    response = input("是否继续? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ 取消迁移")
        return
    
    # 获取项目根目录
    root = Path(__file__).parent.resolve()
    print(f"\n📂 项目根目录: {root}")
    
    # 1. 备份
    if not backup_directories(root):
        print("❌ 备份失败，终止迁移")
        return
    
    # 2. 移动目录
    if not move_directories(root):
        print("❌ 移动失败，请检查备份目录")
        return
    
    # 3. 检查 app 目录
    if check_app_dir_empty(root):
        print("\n✅ app/ 目录已清空（仅剩系统文件）")
        print("   可以手动删除 app/ 目录（如果确认不再需要）")
    else:
        print("\n⚠️  app/ 目录仍有其他文件，请手动检查")
    
    print("\n" + "=" * 60)
    print("✅ 目录迁移完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 运行 update_imports.py 更新所有导入语句")
    print("2. 运行测试验证功能正常")
    print("3. 如果一切正常，可以删除 backup_before_migration/ 目录")

if __name__ == "__main__":
    main()
