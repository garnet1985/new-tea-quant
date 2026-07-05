"""测试 ContractPool 发现机制。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from core.modules.data_contract import ContractPool


def test_contract_pool():
    """测试 ContractPool 基本功能。"""
    print("=== 测试 ContractPool 发现机制 ===")

    # 1. 创建 ContractPool
    pool = ContractPool()
    print(f"✓ ContractPool 初始化成功")

    # 2. 发现系统 contract
    pool.discover()
    print(f"✓ 发现完成")

    # 3. 列出可用的 data_keys
    available_keys = pool.list_available_data_keys()
    print(f"✓ 发现 {len(available_keys)} 个 data_keys:")
    for key in sorted(available_keys):
        print(f"  - {key}")

    # 4. 区分系统和用户
    system_keys = pool.list_system_data_keys()
    user_keys = pool.list_user_data_keys()
    print(f"\n=== 区分系统和用户 ===")
    print(f"✓ 系统 data_keys: {len(system_keys)} 个")
    print(f"✓ 用户 data_keys: {len(user_keys)} 个")

    # 5. 检查是否为用户自定义
    if "stock.kline.daily" in available_keys:
        is_custom = pool.is_customized("stock.kline.daily")
        print(f"✓ stock.kline.daily is_customized: {is_custom} (应为 False)")

    # 6. 获取验证错误（如果有）
    errors = pool.get_validation_errors()
    if errors:
        print(f"\n⚠ 发现 {len(errors)} 个验证错误:")
        for data_key, error_list in errors.items():
            print(f"  - {data_key}:")
            for error in error_list:
                print(f"    - {error}")
    else:
        print(f"\n✓ 所有 declaration 验证通过")

    # 7. 测试防止重复声明
    print(f"\n=== 测试防止重复声明 ===")
    try:
        # 尝试注册一个已存在的 data_key
        duplicate_declaration = {
            "meta": {
                "data_key": "stock.kline.daily",  # 已存在
                "type": "time_series",
                "scope": "per_entity",
                "loader": None,
            }
        }
        pool.register_custom_declaration(duplicate_declaration)
        print(f"✗ 应该拒绝重复声明，但没有拒绝")
    except ValueError as e:
        print(f"✓ 成功拒绝重复声明: {e}")

    # 8. 获取某个 contract
    if "stock.kline.daily" in available_keys:
        contract = pool.get_contract("stock.kline.daily")
        print(f"\n=== 测试 Contract 实例 ===")
        print(f"✓ 成功获取 contract: {contract.meta.data_key}")
        print(f"  - display_name: {contract.meta.display_name}")
        print(f"  - type: {contract.meta.type}")
        print(f"  - scope: {contract.meta.scope}")
        print(f"  - unique_keys: {contract.meta.unique_keys}")
        print(f"  - loader: {contract.meta.loader}")
        print(f"  - is_customized: {contract.meta.is_customized}")

    print("\n=== 所有测试通过 ===")


if __name__ == "__main__":
    test_contract_pool()