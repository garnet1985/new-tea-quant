"""ContractPool - 发现和管理 Contract Declarations。"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.modules.data_contract.core.data_class.base_contract import BaseDataKey
from core.modules.data_contract.core.data_class.base_loader import BaseDataKeyLoader

logger = logging.getLogger(__name__)


class ContractPool:
    """Contract Pool - 发现和管理 Contract Declarations。

    职责：
    1. 发现系统 contract（data_keys/*/declaration.py）
    2. 发现用户 contract（用户空间）
    3. 检查必要文件和继承关系
    4. 建立 data_key → declaration 映射

    检查内容：
    - declaration.py 文件必须存在
    - loader.py 文件必须存在
    - loader 必须继承 BaseDataKeyLoader
    - meta 必须包含必要字段（data_key, type, scope）

    使用方式：
        pool = ContractPool()
        pool.discover()  # 发现系统和用户 contract
        contract = pool.get_contract("stock.kline.daily")
        contract.fill_in_data(runtime={...})
    """

    def __init__(self):
        """初始化 ContractPool。"""
        self._declarations: Dict[str, Dict[str, Any]] = {}
        self._validation_errors: Dict[str, List[str]] = {}  # data_key -> error list

    def discover(self, user_space_path: Optional[Path] = None) -> None:
        """发现所有 contract（系统 + 用户）。

        Args:
            user_space_path: 用户空间路径（可选）
        """
        # 发现系统 contract（is_customized=False）
        self._discover_system_declarations(is_customized=False)

        # 发现用户 contract（is_customized=True）
        if user_space_path:
            self._discover_user_declarations(user_space_path, is_customized=True)

        logger.info(f"Discovery 完成：发现 {len(self._declarations)} 个有效 Declaration")

    def _discover_system_declarations(self, is_customized: bool = False) -> None:
        """发现系统 declaration 文件（data_keys/*/declaration.py）。

        Args:
            is_customized: 是否为用户自定义（系统=False，用户=True）
        """
        # 获取 data_keys 目录路径
        data_keys_dir = Path(__file__).parent.parent / "data_keys"

        if not data_keys_dir.exists():
            logger.warning(f"data_keys 目录不存在：{data_keys_dir}")
            return

        logger.debug(f"扫描系统 declaration 目录：{data_keys_dir}")

        # 扫描所有子文件夹
        for sub_dir in data_keys_dir.iterdir():
            if not sub_dir.is_dir():
                continue

            # 跳过非 DataKey 目录（如 __pycache__）
            if sub_dir.name.startswith('_') or sub_dir.name.startswith('.'):
                continue

            # 发现单个 data_key
            self._discover_single_data_key(sub_dir, is_customized=is_customized)

    def _discover_user_declarations(self, user_space_path: Path, is_customized: bool = True) -> None:
        """发现用户 declaration 文件（用户空间）。

        Args:
            user_space_path: 用户空间路径（如 userspace/data_keys/）
            is_customized: 是否为用户自定义（系统=False，用户=True）
        """
        if not user_space_path.exists():
            logger.warning(f"用户空间路径不存在：{user_space_path}")
            return

        logger.debug(f"扫描用户 declaration 目录：{user_space_path}")

        # 扫描所有子文件夹
        for sub_dir in user_space_path.iterdir():
            if not sub_dir.is_dir():
                continue

            # 跳过非 DataKey 目录
            if sub_dir.name.startswith('_') or sub_dir.name.startswith('.'):
                continue

            # 发现单个 data_key
            self._discover_single_data_key(sub_dir, is_customized=is_customized)

    def _discover_single_data_key(self, sub_dir: Path, is_customized: bool = False) -> None:
        """发现单个 data_key（检查必要文件和继承关系）。

        Args:
            sub_dir: data_key 子目录路径
            is_customized: 是否为用户自定义（系统=False，用户=True）

        检查内容：
        1. declaration.py 文件必须存在
        2. loader.py 文件必须存在
        3. loader 必须继承 BaseDataKeyLoader
        4. meta 必须包含必要字段
        5. data_key 不能重复（防止覆盖）
        """
        errors = []
        data_key_name = sub_dir.name

        # 1. 检查 declaration.py 文件
        declaration_file = sub_dir / 'declaration.py'
        if not declaration_file.exists():
            errors.append(f"缺少 declaration.py 文件")
            self._validation_errors[data_key_name] = errors
            logger.warning(f"{data_key_name}: 缺少 declaration.py 文件，跳过")
            return

        # 2. 检查 loader.py 文件
        loader_file = sub_dir / 'loader.py'
        if not loader_file.exists():
            errors.append(f"缺少 loader.py 文件")
            self._validation_errors[data_key_name] = errors
            logger.warning(f"{data_key_name}: 缺少 loader.py 文件，跳过")
            return

        # 3. 导入并验证 declaration
        try:
            module_name = f"core.modules.data_contract.core.data_keys.{sub_dir.name}.declaration"
            module = importlib.import_module(module_name)

            # 提取导出的 declaration（查找以 _DECLARATION 结尾的变量）
            declarations_found = []
            for attr_name in dir(module):
                if attr_name.endswith('_DECLARATION') and not attr_name.startswith('_'):
                    declaration_dict = getattr(module, attr_name)

                    # 验证是否为 dict
                    if isinstance(declaration_dict, dict):
                        # 验证 meta 字段
                        meta_errors = self._validate_declaration_meta(declaration_dict)
                        if meta_errors:
                            errors.extend(meta_errors)
                            logger.warning(f"{data_key_name}.{attr_name}: meta 验证失败")
                            continue

                        # 验证 contract_class（如果指定）
                        meta = declaration_dict.get("meta", {})
                        contract_class = meta.get("contract_class")
                        if contract_class:
                            # 检查是否继承 BaseDataKey
                            if not (isinstance(contract_class, type) and issubclass(contract_class, BaseDataKey)):
                                error_msg = f"contract_class 必须继承 BaseDataKey"
                                errors.append(error_msg)
                                self._validation_errors[data_key_name] = errors
                                logger.error(f"{data_key_name}.{attr_name}: {error_msg}")
                                continue

                        # 获取 data_key
                        data_key = meta.get("data_key")

                        if data_key:
                            declarations_found.append((data_key, declaration_dict, attr_name))
                        else:
                            errors.append(f"{attr_name}: 缺少 meta.data_key")
                            logger.warning(f"{attr_name}: 缺少 meta.data_key，跳过")

            if not declarations_found:
                self._validation_errors[data_key_name] = errors
                return

        except Exception as e:
            errors.append(f"导入 declaration.py 失败: {e}")
            self._validation_errors[data_key_name] = errors
            logger.error(f"{data_key_name}: 导入 declaration.py 失败: {e}")
            return

        # 4. 验证 loader 继承关系
        try:
            loader_module_name = f"core.modules.data_contract.core.data_keys.{sub_dir.name}.loader"
            loader_module = importlib.import_module(loader_module_name)

            # 查找 loader 类
            loader_classes_found = []
            for attr_name in dir(loader_module):
                attr = getattr(loader_module, attr_name)
                # 检查是否是类且继承 BaseDataKeyLoader
                if isinstance(attr, type) and issubclass(attr, BaseDataKeyLoader) and attr != BaseDataKeyLoader:
                    loader_classes_found.append(attr)

            if not loader_classes_found:
                errors.append(f"loader.py 中没有找到继承 BaseDataKeyLoader 的类")
                self._validation_errors[data_key_name] = errors
                logger.warning(f"{data_key_name}: loader 没有继承 BaseDataKeyLoader，跳过")
                return

        except Exception as e:
            errors.append(f"导入 loader.py 失败: {e}")
            self._validation_errors[data_key_name] = errors
            logger.error(f"{data_key_name}: 导入 loader.py 失败: {e}")
            return

        # 5. 添加有效的 declaration（防止重复）
        for data_key, declaration_dict, attr_name in declarations_found:
            # 检查是否已存在（防止覆盖）
            if data_key in self._declarations:
                error_msg = f"data_key '{data_key}' 已存在，不能重复声明"
                errors.append(error_msg)
                self._validation_errors[data_key_name] = errors
                logger.error(f"{data_key_name}.{attr_name}: {error_msg}")
                continue

            # 添加 is_customized 字段到 meta
            declaration_dict["meta"]["is_customized"] = is_customized

            # 添加到 pool
            self._declarations[data_key] = declaration_dict
            source = "用户自定义" if is_customized else "系统"
            logger.debug(f"发现有效 Declaration ({source}): {data_key} -> {attr_name}")

    def _validate_declaration_meta(self, declaration: Dict[str, Any]) -> List[str]:
        """验证 declaration 的 meta 字段。

        Args:
            declaration: declaration 字典

        Returns:
            List[str]: 错误列表（空列表表示验证通过）
        """
        errors = []

        meta = declaration.get("meta")
        if not meta:
            errors.append("缺少 meta 字段")
            return errors

        if not isinstance(meta, dict):
            errors.append("meta 必须是 dict")
            return errors

        # 检查必要字段
        required_fields = ["data_key", "type", "scope"]
        for field in required_fields:
            if field not in meta:
                errors.append(f"meta 缺少必要字段: {field}")

        # contract_class 是可选的（默认 BaseDataKey）
        if "contract_class" in meta:
            # 验证 contract_class 是否继承 BaseDataKey
            contract_class = meta.get("contract_class")
            if contract_class and not (isinstance(contract_class, type) and issubclass(contract_class, BaseDataKey)):
                errors.append(f"meta.contract_class 必须继承 BaseDataKey")

        # loader 是可选的（如果 contract_class 覆盖了 fill_in_data）
        # 但如果没有 contract_class，loader 是必需的

        # 检查 type 值
        if "type" in meta:
            valid_types = ["time_series", "non_time_series"]
            if meta["type"] not in valid_types:
                errors.append(f"meta.type 值无效: {meta['type']}，必须是 {valid_types}")

        # 检查 scope 值
        if "scope" in meta:
            valid_scopes = ["global", "per_entity"]
            if meta["scope"] not in valid_scopes:
                errors.append(f"meta.scope 值无效: {meta['scope']}，必须是 {valid_scopes}")

        return errors

    def get_contract(self, data_key: str) -> BaseDataKey:
        """根据 data_key 创建 Contract 实例（使用 contract_class 或 BaseDataKey）。

        Args:
            data_key: DataKey 的唯一标识符（如 'stock.kline.daily')

        Returns:
            BaseDataKey: Contract 实例（需要调用 fill_in_data 加载）

        Raises:
            KeyError: 如果 data_key 不存在
        """
        if data_key not in self._declarations:
            raise KeyError(f"DataKey {data_key} 不存在")

        declaration = self._declarations[data_key]
        
        # 使用 contract_class（如果指定）或 BaseDataKey
        meta = declaration.get("meta", {})
        contract_class = meta.get("contract_class", BaseDataKey)
        
        return contract_class(declaration)

    def get_declaration(self, data_key: str) -> Dict[str, Any]:
        """根据 data_key 获取 declaration 字典。

        Args:
            data_key: DataKey 的唯一标识符

        Returns:
            Dict[str, Any]: declaration 字典

        Raises:
            KeyError: 如果 data_key 不存在
        """
        if data_key not in self._declarations:
            raise KeyError(f"DataKey {data_key} 不存在")

        return self._declarations[data_key]

    def list_available_data_keys(self) -> List[str]:
        """列出所有可用的 data_key。

        Returns:
            List[str]: 可用 data_key 列表
        """
        return list(self._declarations.keys())

    def list_system_data_keys(self) -> List[str]:
        """列出系统 data_key（is_customized=False）。

        Returns:
            List[str]: 系统 data_key 列表
        """
        return [
            key for key, decl in self._declarations.items()
            if not decl.get("meta", {}).get("is_customized", False)
        ]

    def list_user_data_keys(self) -> List[str]:
        """列出用户 data_key（is_customized=True）。

        Returns:
            List[str]: 用户 data_key 列表
        """
        return [
            key for key, decl in self._declarations.items()
            if decl.get("meta", {}).get("is_customized", False)
        ]

    def is_customized(self, data_key: str) -> bool:
        """检查 data_key 是否为用户自定义。

        Args:
            data_key: DataKey 的唯一标识符

        Returns:
            bool: 是否为用户自定义

        Raises:
            KeyError: 如果 data_key 不存在
        """
        if data_key not in self._declarations:
            raise KeyError(f"DataKey {data_key} 不存在")

        return self._declarations[data_key].get("meta", {}).get("is_customized", False)

    def get_validation_errors(self) -> Dict[str, List[str]]:
        """获取验证错误列表。

        Returns:
            Dict[str, List[str]]: data_key -> error list
        """
        return self._validation_errors

    def register_custom_declaration(self, declaration: Dict[str, Any]) -> None:
        """注册自定义 declaration（不检查文件，只验证 meta，防止重复）。

        Args:
            declaration: declaration 字典

        Raises:
            ValueError: 如果 declaration 验证失败或 data_key 已存在
        """
        errors = self._validate_declaration_meta(declaration)
        if errors:
            raise ValueError(f"declaration 验证失败: {errors}")

        meta = declaration.get("meta", {})
        data_key = meta.get("data_key")

        if not data_key:
            raise ValueError("declaration 缺少 meta.data_key")

        # 检查是否已存在（防止覆盖）
        if data_key in self._declarations:
            raise ValueError(f"data_key '{data_key}' 已存在，不能重复声明，请使用不同的 data_key 名称")

        # 添加 is_customized 字段
        declaration["meta"]["is_customized"] = True

        self._declarations[data_key] = declaration
        logger.info(f"注册用户自定义 Declaration: {data_key}")

    def is_available(self, data_key: str) -> bool:
        """检查 data_key 是否可用。

        Args:
            data_key: DataKey 的唯一标识符

        Returns:
            bool: 是否可用
        """
        return data_key in self._declarations


__all__ = ['ContractPool']