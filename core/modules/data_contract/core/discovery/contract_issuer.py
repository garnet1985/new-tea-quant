"""ContractPool - 发现和管理 Contract Declarations。"""
from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.infra.project_context import ProjectContext
from core.modules.data_contract.core.base.base_contract import BaseDataContract
from core.modules.data_contract.core.base.base_time_series_contract import BaseTimeSeriesContract
from core.modules.data_contract.core.base.base_non_time_series_contract import BaseNonTimeSeriesContract
from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader

logger = logging.getLogger(__name__)


class ContractIssuer:
    """Contract Issuer - 发现和管理 Contract Declarations。

    职责：
    1. 发现系统 contract（data_contracts/*/declaration.py）
    2. 发现用户 contract（用户空间）
    3. 检查必要文件和继承关系
    4. 建立 key → declaration 映射

    检查内容：
    - declaration.py 文件必须存在
    - loader.py 文件必须存在
    - loader 必须继承 BaseDataContractLoader
    - meta 必须包含必要字段（key, type, scope；per_entity 另需 list_data_key）

    使用方式：
        # 方式1：实例方式（传统）
        issuer = ContractIssuer()
        issuer.discover()  # 发现系统和用户 contract
        contract = issuer.get_contract("stock.kline.daily")
        contract.fill_in_data(runtime={...})
        
        # 方式2：静态方式（推荐，简化API）
        contract = ContractIssuer.issue("stock.list")
        stock_list = contract.data
        
        contract = ContractIssuer.issue("stock.kline.daily", entity_ids=["600000.SH"])
        kline = contract.data
    """

    # 类属性（用于issue静态方法）
    _discovered: bool = False
    _declarations_cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        """初始化 ContractIssuer。"""
        self._declarations: Dict[str, Dict[str, Any]] = {}
        self._validation_errors: Dict[str, List[str]] = {}  # key -> error list
        self._data_keys: List[str] = []  # 注册的 data keys（系统 + 用户）

    def discover(self, user_space_path: Optional[Path] = None) -> None:
        """发现所有 contract（系统 + 用户）。

        Args:
            user_space_path: 用户空间路径（可选）
        """
        # Step 1: 加载并合并 data_keys（系统 + 用户）
        self._load_data_keys(user_space_path)
        
        # Step 2: 发现系统 contract（is_customized=False）
        self._discover_system_declarations(is_customized=False)

        # Step 3: 发现用户 contract（is_customized=True）
        if user_space_path:
            self._discover_user_declarations(user_space_path, is_customized=True)

        logger.info(f"Discovery 完成：发现 {len(self._declarations)} 个有效 Declaration")
        
    def _load_data_keys(self, user_space_path: Optional[Path] = None) -> None:
        """加载并合并 data_keys（系统 + 用户）。
        
        Args:
            user_space_path: 用户空间路径（可选）
        
        流程：
        1. 加载系统 data_keys.py
        2. 加载用户 data_keys.py（如果存在）
        3. 合并（系统 + 用户）
        """
        # 加载系统 data_keys
        system_keys = self._load_system_data_keys()
        
        # 加载用户 data_keys（如果存在）
        user_keys = []
        if user_space_path:
            user_keys = self._load_user_data_keys(user_space_path)
        
        # 合并
        self._data_keys = system_keys + user_keys
        
        logger.info(f"加载 data_keys：系统={len(system_keys)}个，用户={len(user_keys)}个，合并={len(self._data_keys)}个")
        
    def _load_system_data_keys(self) -> List[str]:
        """加载系统 data_keys.py 文件。
        
        Returns:
            系统 DATA_KEYS 列表
        """
        try:
            # 导入系统 SYS_DATA_KEY
            from core.modules.data_contract.core.data_contracts.data_keys import SYS_DATA_KEY
            return SYS_DATA_KEY.all_keys()
        except Exception as e:
            logger.warning(f"加载系统 SYS_DATA_KEY 失败：{e}")
            return []
            
    def _load_user_data_keys(self, user_space_path: Optional[Path] = None) -> List[str]:
        """加载用户 data_keys.py 文件（USER_DATA_KEY类）。

        Args:
            user_space_path: 保留参数（与 discover 签名对齐）；实际路径取自 ProjectContext。

        Returns:
            用户 DATA_KEYS 列表（从USER_DATA_KEY类提取）
            
        使用ProjectContext API避免硬编码路径错误。
        """
        _ = user_space_path
        # 使用ProjectContext API获取路径（避免硬编码）
        user_data_keys_file = ProjectContext.path.get_data_contract_root() / "data_keys.py"
        
        if not user_data_keys_file.exists():
            logger.debug(f"用户 data_keys.py 不存在：{user_data_keys_file}")
            return []
        
        try:
            # 动态导入用户 data_keys.py
            spec = importlib.util.spec_from_file_location("user_data_keys", user_data_keys_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查USER_DATA_KEY类是否存在
            if not hasattr(module, 'USER_DATA_KEY'):
                logger.warning(f"用户 data_keys.py 没有 USER_DATA_KEY 类")
                return []
            
            # 获取USER_DATA_KEY类
            user_data_key_class = module.USER_DATA_KEY
            
            # 提取所有类属性（枚举常量）
            user_keys = []
            for attr_name in dir(user_data_key_class):
                # 跳过私有属性和特殊方法
                if not attr_name.startswith('_') and attr_name not in ['all_keys']:
                    attr_value = getattr(user_data_key_class, attr_name)
                    # 只添加字符串类型的类属性
                    if isinstance(attr_value, str):
                        user_keys.append(attr_value)
                        logger.debug(f"用户 DATA_KEY: {attr_name} = {attr_value}")
            
            return user_keys
        except Exception as e:
            logger.warning(f"加载用户 data_keys.py 失败：{e}")
            return []

    def _discover_system_declarations(self, is_customized: bool = False) -> None:
        """发现系统 declaration 文件（data_contracts/*/declaration.py）。

        Args:
            is_customized: 是否为用户自定义（系统=False，用户=True）
        """
        # 获取 data_contracts 目录路径
        data_contracts_dir = Path(__file__).parent.parent / "data_contracts"

        if not data_contracts_dir.exists():
            logger.warning(f"data_contracts 目录不存在：{data_contracts_dir}")
            return

        logger.debug(f"扫描系统 declaration 目录：{data_contracts_dir}")

        # 扫描所有子文件夹
        for sub_dir in data_contracts_dir.iterdir():
            if not sub_dir.is_dir():
                continue

            # 跳过非 Contract 目录（如 __pycache__）
            if sub_dir.name.startswith('_') or sub_dir.name.startswith('.'):
                continue

            # 发现单个 contract
            self._discover_single_contract(sub_dir, is_customized=is_customized)

    def _discover_user_declarations(self, user_space_path: Path, is_customized: bool = True) -> None:
        """发现用户 declaration 文件（用户空间）。

        Args:
            user_space_path: 用户空间路径（如 userspace/data_contracts/）
            is_customized: 是否为用户自定义（系统=False，用户=True）
            
        使用ProjectContext API避免硬编码路径错误。
        """
        # 使用ProjectContext API获取路径（避免硬编码）
        user_contract_root = ProjectContext.path.get_data_contract_root()
        
        if not user_contract_root.exists():
            logger.warning(f"用户contract目录不存在：{user_contract_root}")
            return

        logger.debug(f"扫描用户 declaration 目录：{user_contract_root}")

        # 扫描所有子文件夹
        for sub_dir in user_contract_root.iterdir():
            if not sub_dir.is_dir():
                continue

            # 跳过非 Contract 目录
            if sub_dir.name.startswith('_') or sub_dir.name.startswith('.'):
                continue

            # 发现单个 contract
            self._discover_single_contract(sub_dir, is_customized=is_customized)

    def _discover_single_contract(self, sub_dir: Path, is_customized: bool = False) -> None:
        """发现单个 contract（检查必要文件和继承关系）。

        Args:
            sub_dir: contract 子目录路径
            is_customized: 是否为用户自定义（系统=False，用户=True）

        检查内容：
        1. declaration.py 文件必须存在
        2. loader.py 文件必须存在
        3. loader 必须继承 BaseDataContractLoader
        4. meta 必须包含必要字段
        5. key 不能重复（防止覆盖）
        """
        errors = []
        contract_name = sub_dir.name

        # 1. 检查 declaration.py 文件
        declaration_file = sub_dir / 'declaration.py'
        if not declaration_file.exists():
            errors.append(f"缺少 declaration.py 文件")
            self._validation_errors[contract_name] = errors
            logger.warning(f"{contract_name}: 缺少 declaration.py 文件，跳过")
            return

        # 2. 检查 loader.py 文件
        loader_file = sub_dir / 'loader.py'
        if not loader_file.exists():
            errors.append(f"缺少 loader.py 文件")
            self._validation_errors[contract_name] = errors
            logger.warning(f"{contract_name}: 缺少 loader.py 文件，跳过")
            return

        # 3. 导入并验证 declaration
        try:
            module_name = f"core.modules.data_contract.core.data_contracts.{sub_dir.name}.declaration"
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
                            logger.warning(f"{contract_name}.{attr_name}: meta 验证失败")
                            continue

                        # 验证 contract_class（如果指定）
                        meta = declaration_dict.get("meta", {})
                        contract_class = meta.get("contract_class")
                        if contract_class:
                            # 检查是否继承 BaseDataContract
                            if not (isinstance(contract_class, type) and issubclass(contract_class, BaseDataContract)):
                                error_msg = f"contract_class 必须继承 BaseDataContract"
                                errors.append(error_msg)
                                self._validation_errors[contract_name] = errors
                                logger.error(f"{contract_name}.{attr_name}: {error_msg}")
                                continue

                        # 获取 key
                        key = meta.get("key")

                        if key:
                            declarations_found.append((key, declaration_dict, attr_name))
                            # UX提示：建议使用常量（不影响功能，只是最佳实践提示）
                            # 检查是否使用了硬字符串（通过检查declaration源文件）
                            self._check_key_usage_best_practice(key, declaration_file, is_customized)
                        else:
                            errors.append(f"{attr_name}: 缺少 meta.key")
                            logger.warning(f"{attr_name}: 缺少 meta.key，跳过")

            if not declarations_found:
                self._validation_errors[contract_name] = errors
                return

        except Exception as e:
            errors.append(f"导入 declaration.py 失败: {e}")
            self._validation_errors[contract_name] = errors
            logger.error(f"{contract_name}: 导入 declaration.py 失败: {e}")
            return

        # 4. 验证 loader 继承关系
        try:
            loader_module_name = f"core.modules.data_contract.core.data_contracts.{sub_dir.name}.loader"
            loader_module = importlib.import_module(loader_module_name)

            # 查找 loader 类
            loader_classes_found = []
            for attr_name in dir(loader_module):
                attr = getattr(loader_module, attr_name)
                # 检查是否是类且继承 BaseDataContractLoader
                if isinstance(attr, type) and issubclass(attr, BaseDataContractLoader) and attr != BaseDataContractLoader:
                    loader_classes_found.append(attr)

            if not loader_classes_found:
                errors.append(f"loader.py 中没有找到继承 BaseDataContractLoader 的类")
                self._validation_errors[contract_name] = errors
                logger.warning(f"{contract_name}: loader 没有继承 BaseDataContractLoader，跳过")
                return

        except Exception as e:
            errors.append(f"导入 loader.py 失败: {e}")
            self._validation_errors[contract_name] = errors
            logger.error(f"{contract_name}: 导入 loader.py 失败: {e}")
            return

        # 5. 添加有效的 declaration（防止重复 + 验证 data_key 注册）
        for key, declaration_dict, attr_name in declarations_found:
            # 验证 key 是否在 data_keys 中注册
            if self._data_keys and key not in self._data_keys:
                # 根据是否为用户自定义，给出不同的错误提示
                if is_customized:
                    error_msg = (
                        f"您的 contract key '{key}' 没有在 userspace/data_keys.py 的 USER_DATA_KEY 类中枚举注册，"
                        f"请按照 SYS_DATA_KEY 的方式在 USER_DATA_KEY 中添加对应的常量。"
                        f"\n示例：class USER_DATA_KEY:"
                        f"\n    MY_CUSTOM_DATA = '{key}'  # 在此处添加"
                    )
                else:
                    error_msg = f"系统 contract key '{key}' 未在 SYS_DATA_KEY 中注册，请检查系统配置"
                
                errors.append(error_msg)
                self._validation_errors[contract_name] = errors
                logger.error(f"{contract_name}.{attr_name}: {error_msg}")
                continue
            
            # 检查是否已存在（防止覆盖）
            if key in self._declarations:
                error_msg = f"key '{key}' 已存在，不能重复声明"
                errors.append(error_msg)
                self._validation_errors[contract_name] = errors
                logger.error(f"{contract_name}.{attr_name}: {error_msg}")
                continue

            # 记录 is_customized（不在 meta 里，而是 declaration 顶层）
            declaration_dict["_is_customized"] = is_customized

            # 添加到 pool
            self._declarations[key] = declaration_dict
            source = "用户自定义" if is_customized else "系统"
            logger.debug(f"发现有效 Declaration ({source}): {key} -> {attr_name}")

    def _check_key_usage_best_practice(self, key: str, declaration_file: Path, is_customized: bool) -> None:
        """检查 key 使用最佳实践（UX提示，不影响功能）。
        
        Args:
            key: Contract key
            declaration_file: declaration.py 文件路径
            is_customized: 是否为用户自定义
        
        检查内容：
        - 是否导入了 SYS_DATA_KEY 或 USER_DATA_KEY
        - 是否使用了常量引用（如 SYS_DATA_KEY.STOCK_LIST）
        - 如果没有，给出 warning 提示（不影响验证结果）
        
        设计：
        - 只给出提示，不影响 contract 加载
        - 避免硬字符串，推荐使用常量
        """
        try:
            # 读取 declaration.py 源文件
            with open(declaration_file, 'r', encoding='utf-8') as f:
                source_content = f.read()
            
            # 检查是否导入了 DATA_KEY 类
            data_key_imported = False
            if is_customized:
                # 用户自定义：检查是否导入 USER_DATA_KEY
                if 'USER_DATA_KEY' in source_content:
                    data_key_imported = True
            else:
                # 系统：检查是否导入 SYS_DATA_KEY
                if 'SYS_DATA_KEY' in source_content or 'SystemDataKeys' in source_content:
                    data_key_imported = True
            
            # 如果没有导入 DATA_KEY，给出提示
            if not data_key_imported:
                data_key_class = "USER_DATA_KEY" if is_customized else "SYS_DATA_KEY"
                data_key_file = "userspace/extensions/data_contract/data_keys.py" if is_customized else "core/modules/data_contract/core/data_contracts/data_keys.py"
                
                warning_msg = (
                    f"建议：{declaration_file.name} 中的 meta.key '{key}' 没有使用 {data_key_class} 常量，"
                    f"建议使用常量引用以避免拼写错误。"
                )
                example_msg = (
                    f"示例："
                    f"\n  from {data_key_file.replace('/', '.').replace('.py', '')} import {data_key_class}"
                    f"\n  meta: key: {data_key_class}.{key.upper().replace('.', '_')}"
                )
                
                logger.warning(warning_msg + "\n" + example_msg)
                
        except Exception as e:
            # 验证失败不影响功能，只记录 debug
            logger.debug(f"检查 key 使用最佳实践失败：{e}")

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
        required_fields = ["key", "type", "scope"]
        for field in required_fields:
            if field not in meta:
                errors.append(f"meta 缺少必要字段: {field}")

        # contract_class 是可选的（默认 BaseDataContract）
        if "contract_class" in meta:
            # 验证 contract_class 是否继承 BaseDataContract
            contract_class = meta.get("contract_class")
            if contract_class and not (isinstance(contract_class, type) and issubclass(contract_class, BaseDataContract)):
                errors.append(f"meta.contract_class 必须继承 BaseDataContract")

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

        # per_entity 必须声明所属实体 list 的 data_key
        if meta.get("scope") == "per_entity":
            list_data_key = str(meta.get("list_data_key") or "").strip()
            if not list_data_key:
                errors.append(
                    "meta.scope=per_entity 时必须提供 meta.list_data_key"
                    "（指向 GLOBAL list 的 data_key，如 stock.list）"
                )

        return errors

    def get_contract(self, key: str) -> BaseDataContract:
        """根据 key 创建 Contract 实例（使用 contract_class 或 BaseDataContract）。

        Args:
            key: Contract 的唯一标识符（如 'stock.kline.daily')

        Returns:
            BaseDataContract: Contract 实例（需要调用 fill_in_data 加载）

        Raises:
            KeyError: 如果 key 不存在
        """
        if key not in self._declarations:
            raise KeyError(f"Contract {key} 不存在")

        declaration = self._declarations[key]
        
        # 使用 contract_class（如果指定）或根据 type 选择基类
        meta = declaration.get("meta", {})
        contract_class = meta.get("contract_class")
        
        # 如果用户没有指定 contract_class，根据 type 选择基类
        if contract_class is None:
            contract_type = meta.get("type", "time_series")
            if contract_type == "time_series":
                contract_class = BaseTimeSeriesContract
            else:
                contract_class = BaseNonTimeSeriesContract
        
        # 创建 Contract
        contract = contract_class(declaration)
        
        # 设置 is_customized（从 declaration 顶层读取）
        contract.is_customized = declaration.get("_is_customized", False)
        
        return contract

    def get_declaration(self, key: str) -> Dict[str, Any]:
        """根据 key 获取 declaration 字典。

        Args:
            key: Contract 的唯一标识符

        Returns:
            Dict[str, Any]: declaration 字典

        Raises:
            KeyError: 如果 key 不存在
        """
        if key not in self._declarations:
            raise KeyError(f"Contract {key} 不存在")

        return self._declarations[key]

    def list_available_keys(self) -> List[str]:
        """列出所有可用的 key。

        Returns:
            List[str]: 可用 key 列表
        """
        return list(self._declarations.keys())

    def list_system_keys(self) -> List[str]:
        """列出系统 key（is_customized=False）。

        Returns:
            List[str]: 系统 key 列表
        """
        return [
            data_key
            for data_key, decl in self._declarations.items()
            if not decl.get("_is_customized", False)
        ]

    def list_user_keys(self) -> List[str]:
        """列出用户 key（is_customized=True）。

        Returns:
            List[str]: 用户 key 列表
        """
        return [
            data_key
            for data_key, decl in self._declarations.items()
            if decl.get("_is_customized", False)
        ]

    def is_customized(self, key: str) -> bool:
        """检查 key 是否为用户自定义。

        Args:
            key: Contract 的唯一标识符

        Returns:
            bool: 是否为用户自定义

        Raises:
            KeyError: 如果 key 不存在
        """
        if key not in self._declarations:
            raise KeyError(f"Contract {key} 不存在")

        return self._declarations[key].get("_is_customized", False)

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
        key = meta.get("key")

        if not key:
            raise ValueError("declaration 缺少 meta.key")

        # 检查是否已存在（防止覆盖）
        if key in self._declarations:
            raise ValueError(f"key '{key}' 已存在，不能重复声明，请使用不同的 key 名称")

        # 记录 is_customized
        declaration["_is_customized"] = True

        self._declarations[key] = declaration
        logger.info(f"注册自定义 Declaration: {key}")

    def is_available(self, key: str) -> bool:
        """检查 key 是否可用。

        Args:
            key: Contract 的唯一标识符

        Returns:
            bool: 是否可用
        """
        return key in self._declarations

    @classmethod
    def issue(
        cls,
        key: str,
        entity_ids: Optional[List[str]] = None,
        runtime: Optional[Dict[str, Any]] = None,
        fill_in_data: bool = False,
    ) -> BaseDataContract:
        """发行数据契约（简化API，自动discovery）。

        Args:
            key: Contract 的唯一标识符（字符串，如 DATA_KEY.STOCK_LIST)
            entity_ids: Entity IDs列表（per_entity contract必需，global contract不需要）
            runtime: Runtime参数字典（params，如 {"start_time": "...", "adjust": "qfq"})
            fill_in_data: 是否自动加载数据（默认 False）

        Returns:
            BaseDataContract: Contract 实例

        使用示例：
            # Global contract（stock.list）
            contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
            stock_list = contract.get_data()
            
            # Per_entity contract（entity_ids单独传递）
            contract = ContractIssuer.issue(
                DATA_KEY.STOCK_KLINE_DAILY,
                entity_ids=["600000.SH"],
                runtime={
                    "start_time": "20200101",
                    "end_time": "20201231",
                    "adjust": "qfq",
                },
                fill_in_data=True,
            )
            kline_data = contract.get_data()

        设计：
        - entity_ids 单独传递（对应 declaration 中的 runtime.entity_ids）
        - runtime 只包含 params（对应 declaration 中的 params）
        - 自动 discovery（只执行一次）
        - fill_in_data 默认 False（需要显式声明）
        """
        # 自动 discovery（只执行一次）
        if not cls._discovered:
            cls._auto_discover()

        # 检查 key 是否存在
        if key not in cls._declarations_cache:
            raise ValueError(f"未发现的 contract: {key}")

        # 获取 declaration
        declaration = cls._declarations_cache[key]

        # 创建 contract instance
        contract = cls._create_contract_from_declaration_static(declaration)

        # 合并 runtime 参数（entity_ids + params）
        full_runtime = runtime or {}
        if entity_ids:
            full_runtime["entity_ids"] = entity_ids

        # 自动加载数据（如果 fill_in_data=True）
        if fill_in_data:
            contract.fill_in_data(runtime=full_runtime)

        return contract

    @classmethod
    def is_global(cls, key: str) -> bool:
        """判断contract是否为global scope。
        
        Args:
            key: Contract key
            
        Returns:
            True if global scope, False otherwise
            
        使用：
        - 不需要创建contract instance
        - 自动discovery（首次调用时）
        - 从declaration cache中判断scope
        """
        # 自动discovery（只执行一次）
        if not cls._discovered:
            cls._auto_discover()
        
        # 检查key是否存在
        if key not in cls._declarations_cache:
            logger.warning(f"未发现的 contract: {key}")
            return False
        
        # 获取declaration
        declaration = cls._declarations_cache[key]
        meta = declaration.get("meta", {})
        
        # 判断scope
        return meta.get("scope") == "global"

    @classmethod
    def get_list_data_key(cls, data_key: str) -> str:
        """读取 per_entity contract 的 ``meta.list_data_key``。

        Args:
            data_key: 如 ``stock.kline.daily`` / ``index.kline.daily``

        Returns:
            GLOBAL list 的 data_key（如 ``stock.list``）

        Raises:
            ValueError: key 未发现，或不是 per_entity / 缺少 list_data_key
        """
        if not cls._discovered:
            cls._auto_discover()

        key = str(data_key or "").strip()
        if key not in cls._declarations_cache:
            raise ValueError(f"未发现的 contract: {key}")

        meta = cls._declarations_cache[key].get("meta") or {}
        if not isinstance(meta, dict):
            raise ValueError(f"contract {key} 缺少 meta")

        scope = str(meta.get("scope") or "").strip().lower()
        if scope != "per_entity":
            raise ValueError(
                f"contract {key} 的 scope={scope!r}，仅 per_entity 有 list_data_key"
            )

        list_key = str(meta.get("list_data_key") or "").strip()
        if not list_key:
            raise ValueError(f"per_entity contract {key} 缺少 meta.list_data_key")
        return list_key

    @classmethod
    def _auto_discover(cls) -> None:
        """自动 discovery（只执行一次）。

        内部方法：
        - 创建临时 instance
        - 调用 discover()
        - 缓存 declarations 到类属性
        """
        # 创建临时 instance
        issuer = ContractIssuer()
        
        # 调用 discover()（系统 contract）
        issuer.discover()
        
        # 缓存到类属性
        cls._declarations_cache = issuer._declarations
        cls._discovered = True
        
        logger.info(f"Auto-discovery 完成：发现 {len(cls._declarations_cache)} 个 contract")

    @classmethod
    def _create_contract_from_declaration_static(
        cls,
        declaration: Dict[str, Any],
    ) -> BaseDataContract:
        """从 declaration 创建 contract instance（静态方法版本）。

        Args:
            declaration: declaration 字典

        Returns:
            BaseDataContract: Contract 实例

        设计：
        - 根据 declaration 中的 contract_class 或 type 选择基类
        - 创建 contract instance
        - 设置 is_customized
        """
        # 使用 contract_class（如果指定）或根据 type 选择基类
        meta = declaration.get("meta", {})
        contract_class = meta.get("contract_class")

        # 如果用户没有指定 contract_class，根据 type 选择基类
        if contract_class is None:
            contract_type = meta.get("type", "time_series")
            if contract_type == "time_series":
                contract_class = BaseTimeSeriesContract
            else:
                contract_class = BaseNonTimeSeriesContract

        # 创建 Contract
        contract = contract_class(declaration)

        # 设置 is_customized（从 declaration 顶层读取）
        contract.is_customized = declaration.get("_is_customized", False)

        return contract

    @classmethod
    def get_all_keys(cls) -> List[str]:
        """获取所有已发现的 key（静态方法）。

        Returns:
            List[str]: 所有 key 列表

        使用示例：
            keys = ContractIssuer.get_all_keys()
            print(keys)  # ["stock.list", "stock.kline.daily", ...]
        """
        if not cls._discovered:
            cls._auto_discover()

        return list(cls._declarations_cache.keys())

    @staticmethod
    def system_registry_source_path():
        """系统契约注册指纹源文件（``data_keys``）；供仿真缓存 fingerprint，勿 deep-import core。"""
        import inspect
        from pathlib import Path

        from core.modules.data_contract.core.data_contracts import data_keys as mod

        src = inspect.getsourcefile(mod)
        return Path(src) if src else None


__all__ = ['ContractIssuer']