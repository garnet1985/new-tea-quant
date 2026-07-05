"""测试 Contract 缓存功能。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from core.modules.data_contract import ContractPool
from core.modules.data_contract.core.data_class.base_contract import get_cache_manager


def test_cache_manager():
    """测试 ContractCacheManager。"""
    print("=== 测试 ContractCacheManager ===")

    # 1. 创建 ContractPool
    pool = ContractPool()
    pool.discover()
    print(f"✓ ContractPool 初始化成功")

    # 2. 获取缓存管理器
    cache_mgr = get_cache_manager()
    print(f"✓ 缓存管理器初始化成功")

    # 3. 测试生命周期
    print(f"\n=== 测试生命周期 ===")
    print(f"✓ 当前不在策略运行周期: {not cache_mgr.is_in_strategy_run()}")

    cache_mgr.enter_strategy_run()
    print(f"✓ 进入策略运行周期: {cache_mgr.is_in_strategy_run()}")

    cache_mgr.exit_strategy_run()
    print(f"✓ 退出策略运行周期: {not cache_mgr.is_in_strategy_run()}")

    # 4. 测试 global scope 缓存（以 macro.gdp 为例）
    print(f"\n=== 测试 global scope 缓存 ===")

    # 检查是否有 global scope 的 data_key
    available_keys = pool.list_available_data_keys()
    print(f"✓ 可用 data_keys: {len(available_keys)} 个")

    # 查找 global scope 的 data_key
    global_keys = []
    for key in available_keys:
        decl = pool.get_declaration(key)
        if decl.get("meta", {}).get("scope") == "global":
            global_keys.append(key)

    if global_keys:
        print(f"✓ Global scope data_keys: {global_keys}")

        # 使用第一个 global data_key 测试缓存
        test_key = global_keys[0]
        print(f"\n使用 {test_key} 测试缓存:")

        # 进入策略运行周期
        cache_mgr.enter_strategy_run()

        # 第一次加载（应该调用 loader）
        contract1 = pool.get_contract(test_key)
        runtime_params = {
            "start_time": "20200101",
            "end_time": "20201231",
        }
        contract1.fill_in_data(runtime=runtime_params)
        print(f"✓ 第一次加载完成: {test_key}")

        # 查看缓存统计
        stats = cache_mgr.get_cache_stats()
        print(f"  - Global cache size: {stats['global_cache_size']}")
        print(f"  - Strategy cache size: {stats['strategy_cache_size']}")

        # 第二次加载（应该使用缓存）
        contract2 = pool.get_contract(test_key)
        contract2.fill_in_data(runtime=runtime_params)
        print(f"✓ 第二次加载完成（应该使用缓存）: {test_key}")

        # 查看缓存统计
        stats = cache_mgr.get_cache_stats()
        print(f"  - Global cache size: {stats['global_cache_size']}")
        print(f"  - Strategy cache size: {stats['strategy_cache_size']}")

        # 测试 force_reload（强制重新加载，忽略缓存）
        contract3 = pool.get_contract(test_key)
        contract3.fill_in_data(runtime=runtime_params, force_reload=True)
        print(f"✓ 强制重新加载完成（忽略缓存）: {test_key}")

        # 退出策略运行周期
        cache_mgr.exit_strategy_run()

        # 查看缓存统计
        stats = cache_mgr.get_cache_stats()
        print(f"✓ 退出策略运行周期后的缓存:")
        print(f"  - Global cache size: {stats['global_cache_size']}")
        print(f"  - Strategy cache size: {stats['strategy_cache_size']}")
    else:
        print(f"⚠ 没有找到 global scope 的 data_key，无法测试缓存")

    print("\n=== 所有测试通过 ===")


if __name__ == "__main__":
    test_cache_manager()