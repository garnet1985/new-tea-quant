#!/usr/bin/env python3
"""
发现 userspace 中的 DataKey（字符串 id）-> Contract 工厂，并与 core 路由合并。

约定（与 data_source Provider 类似）：
- 包：`userspace.data_contract`
- 每个子模块（如 `contract_routes.py`、`plugin_foo.py`）可导出::

      def register_data_contract_routes(registry: ContractRouteRegistry) -> None: ...

  发现器会 import 该包下**所有子模块**并调用上述函数（若存在）。
- 不在 core 的 `data_keys.py` 里改枚举；用户自定义 key 使用稳定字符串（建议集中放在 userspace 常量模块中）。
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Optional

from core.infra.project_context import PathManager
from core.modules.data_contract.contract_route_registry import (
    ContractRouteRegistry,
    build_core_contract_route_registry,
)

logger = logging.getLogger(__name__)

_DEFAULT_REGISTRY: Optional[ContractRouteRegistry] = None

USERSPACE_DATA_CONTRACT_PACKAGE = "userspace.data_contract"


def load_userspace_contract_route_registry() -> ContractRouteRegistry:
    """
    扫描 `userspace.data_contract` 子模块，收集 `register_data_contract_routes`。
    包不存在或导入失败时返回空表（不抛错）。

    目录位置与 `PathManager.data_contract()` 一致（受 userspace 根路径、环境变量影响）。
    """
    reg = ContractRouteRegistry()

    us_root = PathManager.userspace()
    data_contract_dir = PathManager.data_contract()
    logger.debug(
        "data_contract discovery: project_root=%s userspace_root=%s data_contract_dir=%s exists=%s",
        PathManager.get_root(),
        us_root,
        data_contract_dir,
        data_contract_dir.exists(),
    )

    try:
        pkg = importlib.import_module(USERSPACE_DATA_CONTRACT_PACKAGE)
    except ImportError:
        logger.debug("userspace.data_contract 包未找到，跳过 userspace contract 注册")
        return reg

    pkg_file = getattr(pkg, "__file__", None)
    if pkg_file:
        logger.debug("userspace.data_contract 包已加载: __file__=%s", pkg_file)

    if not hasattr(pkg, "__path__"):
        return reg

    for mod in pkgutil.iter_modules(pkg.__path__, prefix=f"{USERSPACE_DATA_CONTRACT_PACKAGE}."):
        name = mod.name
        short = name.rsplit(".", 1)[-1]
        if short.startswith("_"):
            continue
        try:
            submodule = importlib.import_module(name)
        except Exception as e:
            logger.warning("加载 userspace data_contract 子模块失败 %s: %s", name, e)
            continue
        if not hasattr(submodule, "register_data_contract_routes"):
            continue
        try:
            submodule.register_data_contract_routes(reg)
        except Exception as e:
            logger.exception("register_data_contract_routes 失败: module=%s err=%s", name, e)
            raise

    return reg


def build_merged_contract_route_registry(*, userspace_wins: bool = True) -> ContractRouteRegistry:
    """
    core 白名单路由 + userspace 发现结果。同名 key 默认 **userspace 覆盖 core**（显式传入 userspace_wins=False 可反转）。
    """
    core = build_core_contract_route_registry()
    user = load_userspace_contract_route_registry()
    return core.merge(user, other_wins=userspace_wins)


def default_contract_route_registry() -> ContractRouteRegistry:
    """进程内懒构建的合并表（core + userspace）。"""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = build_merged_contract_route_registry()
    return _DEFAULT_REGISTRY
