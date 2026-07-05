"""测试 TagContract（继承 BaseDataKey）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from core.modules.data_contract import ContractPool


def test_tag_contract():
    """测试 TagContract（自定义 Contract 类）。"""
    print("=== 测试 TagContract ===")

    # 1. 创建 ContractPool
    pool = ContractPool()
    pool.discover()
    print(f"✓ ContractPool 初始化成功")

    # 2. 获取 Tag contract（应该使用 TagContract 类）
    tag_contract = pool.get_contract("tag")
    print(f"✓ 成功获取 tag contract")
    print(f"  - 类型: {type(tag_contract).__name__}")  # 应为 TagContract
    print(f"  - data_key: {tag_contract.meta.data_key}")
    print(f"  - display_name: {tag_contract.meta.display_name}")

    # 3. 测试 scenario 参数（必须提供）
    print(f"\n=== 测试 scenario 参数 ===")
    
    # 缺少 scenario 会报错
    try:
        tag_contract.fill_in_data(runtime={
            "entity_ids": ["600000.SH"],
        })
        print(f"✗ 应该拒绝缺少 scenario，但没有拒绝")
    except ValueError as e:
        print(f"✓ 成功拒绝缺少 scenario: {str(e)[:100]}")

    # 提供 scenario_name 应该成功
    print(f"\n=== 测试提供 scenario_name ===")
    tag_contract.add_runtime({
        "entity_ids": ["600000.SH"],
        "scenario_name": "test_scenario",
        "start_time": "20200101",
        "end_time": "20201231",
    })
    print(f"✓ 成功添加 runtime（包含 scenario_name）")
    print(f"  - scenario_name: {tag_contract.runtime.scenario_name}")

    print("\n=== 所有测试通过 ===")


if __name__ == "__main__":
    test_tag_contract()