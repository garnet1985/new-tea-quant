"""
Config Manager - 配置管理器

职责：处理默认配置和用户配置的加载与合并。

设计原则：
- 配置合并逻辑复用 utils/util.py 的 deep_merge_config
- 支持 JSON 和 Python 两种文件格式
- Python 文件支持动态导入（importlib）
- 提供静态方法，无状态
"""

from pathlib import Path
from typing import Dict, Any, Set, Optional, List
import json
import importlib
import importlib.util
import sys
import logging
import os

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 处理默认配置和用户配置的合并"""
    
    @staticmethod
    def load_with_defaults(
        default_path: Path,
        user_path: Path,
        deep_merge_fields: Set[str] = None,
        override_fields: Set[str] = None,
        file_type: str = "json"
    ) -> Dict[str, Any]:
        """
        加载配置（用户配置覆盖默认配置）
        
        内部调用 utils/util.py 的 deep_merge_config
        
        Args:
            default_path: 默认配置文件路径
            user_path: 用户配置文件路径（可选，如果不存在则只返回默认配置）
            deep_merge_fields: 需要深度合并的字段名集合
            override_fields: 需要完全覆盖的字段名集合
            file_type: 文件类型（"json" 或 "py"）
        
        Returns:
            合并后的配置字典
        
        Example:
            default_settings = Path("core/modules/strategy/default_settings.json")
            user_settings = Path("userspace/strategies/example/settings.py")
            settings = ConfigManager.load_with_defaults(
                default_settings,
                user_settings,
                deep_merge_fields={"params"},
                file_type="py"
            )
        """
        # 1. 加载默认配置
        defaults = ConfigManager._load_file(default_path, file_type)
        if not defaults:
            defaults = {}
        
        # 2. 加载用户配置（如果存在）
        if user_path.exists():
            user_config = ConfigManager._load_file(user_path, file_type)
            if user_config:
                # 3. 调用 utils/util.py 的合并逻辑
                try:
                    from core.utils.util import deep_merge_config
                    return deep_merge_config(
                        defaults,
                        user_config,
                        deep_merge_fields=deep_merge_fields,
                        override_fields=override_fields
                    )
                except ImportError:
                    logger.warning(
                        f"无法导入 utils.util.deep_merge_config，使用浅层合并"
                    )
                    # Fallback: 浅层合并
                    return {**defaults, **user_config}
        
        return defaults
    
    @staticmethod
    def load_json(path: Path) -> Dict[str, Any]:
        """
        加载 JSON 配置文件
        
        Args:
            path: JSON 文件路径
        
        Returns:
            配置字典，如果文件不存在或加载失败返回空字典
        """
        return ConfigManager._load_file(path, "json") or {}
    
    @staticmethod
    def load_python(path: Path, var_name: str = "settings") -> Dict[str, Any]:
        """
        加载 Python 配置文件（如 settings.py）
        
        Args:
            path: Python 文件路径
            var_name: 配置变量名（默认为 "settings"）
        
        Returns:
            配置字典，如果文件不存在或加载失败返回空字典
        
        Example:
            # settings.py 中定义：
            # settings = {"name": "example", "params": {...}}
            
            config = ConfigManager.load_python(
                Path("userspace/strategies/example/settings.py"),
                var_name="settings"
            )
        """
        result = ConfigManager._load_file(path, "py", var_name=var_name)
        return result if isinstance(result, dict) else {}
    
    @staticmethod
    def _load_file(
        path: Path,
        file_type: str,
        var_name: str = "settings"
    ) -> Optional[Any]:
        """
        内部方法：加载文件
        
        Args:
            path: 文件路径
            file_type: 文件类型（"json" 或 "py"）
            var_name: Python 文件的变量名（仅用于 "py" 类型）
        
        Returns:
            加载的内容，失败返回 None
        """
        if not path.exists():
            return None
        
        try:
            if file_type == "json":
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            elif file_type == "py":
                # 转换为绝对路径
                if not path.is_absolute():
                    path = path.resolve()
                
                # 动态导入 Python 文件
                module_name = f"_config_module_{path.stem}_{id(path)}"
                
                # 使用 importlib.util 加载模块
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    logger.warning(f"无法加载 Python 配置文件: {path}")
                    return None
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # 获取配置变量
                if hasattr(module, var_name):
                    config = getattr(module, var_name)
                    # 确保返回字典
                    if isinstance(config, dict):
                        return config
                    else:
                        logger.warning(
                            f"Python 配置文件中的 {var_name} 不是字典类型: {path}"
                        )
                        return None
                else:
                    logger.warning(
                        f"Python 配置文件中没有找到变量 {var_name}: {path}"
                    )
                    return None
            
            else:
                logger.warning(f"不支持的文件类型: {file_type}")
                return None
        
        except Exception as e:
            logger.warning(f"加载配置文件失败: {path}, error={e}")
            return None
    
    @staticmethod
    def load_core_config(
        config_name: str,
        deep_merge_fields: Set[str] = None,
        override_fields: Set[str] = None
    ) -> Dict[str, Any]:
        """
        加载核心配置（自动合并 userspace 配置）
        
        加载流程：
        1. 加载 core/default_config/{config_name}.json（默认配置）
        2. 加载 userspace/config/{config_name}.json（用户配置，如果存在）
        3. 深度合并：用户配置覆盖默认配置
        
        Args:
            config_name: 配置文件名（不含 .json 后缀）
            deep_merge_fields: 需要深度合并的字段名集合
            override_fields: 需要完全覆盖的字段名集合
        
        Returns:
            合并后的配置字典
        """
        from .path_manager import PathManager
        
        # 1. 默认配置路径
        default_path = PathManager.default_config() / f"{config_name}.json"
        
        # 2. 用户配置路径
        user_path = PathManager.user_config() / f"{config_name}.json"
        
        # 3. 使用现有的 load_with_defaults 方法
        return ConfigManager.load_with_defaults(
            default_path=default_path,
            user_path=user_path,
            deep_merge_fields=deep_merge_fields,
            override_fields=override_fields,
            file_type="json"
        )
    
    @staticmethod
    def load_database_config(database_type: str = None) -> Dict[str, Any]:
        """
        加载数据库配置（自动合并 userspace 配置）
        
        加载流程：
        1. 加载 core/default_config/database/common.json（公用配置，包含 database_type）
        2. 加载 core/default_config/database/{database_type}.json（数据库专用配置）
        3. 合并：database_type 配置覆盖 common 配置
        4. 加载 userspace/config/database/common.json（用户公用配置，如果存在）
        5. 加载 userspace/config/database/{database_type}.json（用户数据库配置，如果存在）
        6. 深度合并：用户配置覆盖默认配置
        7. 环境变量覆盖（最高优先级）
        
        Args:
            database_type: 数据库类型（'postgresql', 'mysql', 'sqlite'）
                          如果为 None，从配置文件中获取
        
        Returns:
            合并后的数据库配置字典，格式：
            {
                'database_type': 'postgresql',
                'postgresql': {...},  # 或 'mysql': {...}, 'sqlite': {...}
                'batch_write': {...}
            }
        """
        from .path_manager import PathManager
        
        # 1. 加载公用配置（默认）- 包含 database_type
        common_default_path = PathManager.default_config() / "database" / "common.json"
        common_default = ConfigManager.load_json(common_default_path) or {}
        
        # 2. 确定数据库类型（优先级：参数 > 用户 common > 默认 common > 默认值）
        if database_type is None:
            # 先检查用户配置
            common_user_path = PathManager.userspace() / "config" / "database" / "common.json"
            common_user = ConfigManager.load_json(common_user_path) or {}
            database_type = (
                common_user.get('database_type') or 
                common_default.get('database_type') or 
                'postgresql'
            ).lower()
        
        # 3. 加载数据库专用配置（默认）
        db_default_path = PathManager.default_config() / "database" / f"{database_type}.json"
        db_default = ConfigManager.load_json(db_default_path) or {}
        
        # 4. 合并默认配置
        # 将 _advanced 字段展开到顶层
        db_config = ConfigManager._expand_advanced_fields(db_default)
        
        default_config = {
            'database_type': database_type,
            database_type: db_config,
            'batch_write': common_default.get('batch_write', {})
        }
        
        # 5. 加载用户公用配置（如果存在）
        common_user_path = PathManager.userspace() / "config" / "database" / "common.json"
        common_user = ConfigManager.load_json(common_user_path) or {}
        
        # 6. 加载用户数据库专用配置（如果存在）
        db_user_path = PathManager.userspace() / "config" / "database" / f"{database_type}.json"
        db_user = ConfigManager.load_json(db_user_path) or {}
        
        # 7. 合并用户配置
        user_config = {}
        if common_user:
            # 用户可能只配置了 database_type
            if 'database_type' in common_user:
                user_config['database_type'] = common_user['database_type']
            if 'batch_write' in common_user:
                user_config['batch_write'] = common_user['batch_write']
        
        if db_user:
            # 用户配置的数据库连接信息（简化：只需用户名和密码）
            # 合并到对应的数据库配置中
            if database_type not in user_config:
                user_config[database_type] = {}
            user_config[database_type].update(db_user)
        
        # 8. 深度合并（用户配置覆盖默认配置）
        if user_config:
            from core.utils.util import deep_merge_config
            merged_config = deep_merge_config(
                default_config,
                user_config,
                deep_merge_fields={'batch_write', database_type},
                override_fields=set()
            )
        else:
            merged_config = default_config
        
        # 9. 环境变量覆盖（最高优先级）
        merged_config = ConfigManager.load_with_env_vars(
            merged_config,
            ConfigManager._get_database_env_mapping(database_type)
        )
        
        return merged_config
    
    @staticmethod
    def load_with_env_vars(
        config: Dict[str, Any],
        env_var_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        从环境变量覆盖配置值
        
        Args:
            config: 配置字典
            env_var_mapping: 环境变量映射 {配置键路径: 环境变量名}
                            配置键路径支持嵌套，如 'postgresql.password'
        
        Returns:
            更新后的配置字典
        """
        updated_config = config.copy()
        
        for config_path, env_var_name in env_var_mapping.items():
            env_value = os.getenv(env_var_name)
            if env_value:
                # 支持嵌套键（如 'postgresql.password'）
                keys = config_path.split('.')
                target = updated_config
                for key in keys[:-1]:
                    if key not in target:
                        target[key] = {}
                    elif not isinstance(target[key], dict):
                        # 如果中间键不是字典，创建新字典
                        target[key] = {}
                    target = target[key]
                
                # 设置值（支持类型转换）
                final_key = keys[-1]
                original_value = target.get(final_key, '')
                if isinstance(original_value, int):
                    try:
                        target[final_key] = int(env_value)
                    except ValueError:
                        target[final_key] = env_value
                elif isinstance(original_value, bool):
                    target[final_key] = env_value.lower() in ('true', '1', 'yes', 'on')
                else:
                    target[final_key] = env_value
        
        return updated_config
    
    @staticmethod
    def _expand_advanced_fields(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        展开 _advanced 字段到顶层
        
        将 _advanced 字段中的高级配置展开到配置字典的顶层，
        方便用户配置时分离基础配置和高级配置。
        
        Args:
            config: 配置字典
        
        Returns:
            展开后的配置字典
        """
        expanded = config.copy()
        
        if '_advanced' in expanded:
            advanced = expanded.pop('_advanced')
            if isinstance(advanced, dict):
                expanded.update(advanced)
        
        # 递归处理嵌套字典
        for key, value in expanded.items():
            if isinstance(value, dict):
                expanded[key] = ConfigManager._expand_advanced_fields(value)
        
        return expanded
    
    @staticmethod
    def _get_database_env_mapping(database_type: str) -> Dict[str, str]:
        """
        获取数据库配置的环境变量映射
        
        Args:
            database_type: 数据库类型
        
        Returns:
            环境变量映射字典
        """
        db_type_upper = database_type.upper()
        return {
            f'{database_type}.user': f'DB_{db_type_upper}_USER',
            f'{database_type}.password': f'DB_{db_type_upper}_PASSWORD',
            f'{database_type}.host': f'DB_{db_type_upper}_HOST',
            f'{database_type}.port': f'DB_{db_type_upper}_PORT',
            f'{database_type}.database': f'DB_{db_type_upper}_DATABASE',
        }
    
    # ==================== 配置加载接口 ====================
    
    @staticmethod
    def get_data_config() -> Dict[str, Any]:
        """
        获取数据配置（合并后的完整配置）
        
        Returns:
            数据配置字典，包含 default_start_date, decimal_places, stock_list_filter 等
        """
        return ConfigManager.load_core_config(
            'data',
            deep_merge_fields={'stock_list_filter'},
            override_fields=set()
        )
    
    @staticmethod
    def get_database_config(database_type: str = None) -> Dict[str, Any]:
        """
        获取数据库配置（合并后的完整配置）
        
        Args:
            database_type: 数据库类型（可选）
        
        Returns:
            数据库配置字典
        """
        return ConfigManager.load_database_config(database_type)
    
    @staticmethod
    def get_market_config() -> Dict[str, Any]:
        """
        获取市场配置（合并后的完整配置）
        
        Returns:
            市场配置字典
        """
        return ConfigManager.load_core_config(
            'market',
            deep_merge_fields=set(),
            override_fields=set()
        )
    
    @staticmethod
    def get_worker_config() -> Dict[str, Any]:
        """
        获取 Worker 配置（合并后的完整配置）
        
        Returns:
            Worker 配置字典
        """
        return ConfigManager.load_core_config(
            'worker',
            deep_merge_fields=set(),
            override_fields=set()
        )
    
    @staticmethod
    def get_system_config() -> Dict[str, Any]:
        """
        获取系统配置（合并后的完整配置）
        
        Returns:
            系统配置字典
        """
        return ConfigManager.load_core_config(
            'system',
            deep_merge_fields=set(),
            override_fields=set()
        )
    
    # ==================== 便捷访问接口（频繁使用的配置）====================
    
    @staticmethod
    def get_default_start_date() -> str:
        """
        获取默认开始日期
        
        Returns:
            默认开始日期字符串（格式：YYYYMMDD）
        """
        data_config = ConfigManager.get_data_config()
        return data_config.get('default_start_date', '20080101')
    
    @staticmethod
    def get_decimal_places() -> int:
        """
        获取默认小数位数
        
        Returns:
            小数位数（默认 2）
        """
        data_config = ConfigManager.get_data_config()
        return data_config.get('decimal_places', 2)
    
    @staticmethod
    def get_stock_list_filter() -> Dict[str, Any]:
        """
        获取股票清单过滤配置
        
        Returns:
            股票过滤配置字典，包含 enable 和 exclude_patterns
        """
        data_config = ConfigManager.get_data_config()
        return data_config.get('stock_list_filter', {
            'enable': True,
            'exclude_patterns': {
                'start_with': {'id': ['688'], 'name': ['*ST', 'ST', '退']},
                'contains': {}
            }
        })
    
    @staticmethod
    def get_database_type() -> str:
        """
        获取当前使用的数据库类型
        
        Returns:
            数据库类型（'postgresql', 'mysql', 'sqlite'）
        """
        db_config = ConfigManager.get_database_config()
        return db_config.get('database_type', 'postgresql')
    
    @staticmethod
    def get_module_config(module_name: str) -> Dict[str, Any]:
        """
        获取模块的任务配置（用于 Worker）
        
        Args:
            module_name: 模块名称（如 'OpportunityEnumerator', 'Simulator' 等）
        
        Returns:
            配置字典 {'task_type': TaskType, 'reserve_cores': int}
        """
        worker_config = ConfigManager.get_worker_config()
        
        module_task_config = worker_config.get('module_task_config', {})
        default_task_config = worker_config.get('default_task_config', {
            'task_type': 'MIXED',
            'reserve_cores': 2
        })
        
        # 获取模块配置或使用默认配置
        module_config = module_task_config.get(module_name, default_task_config)
        
        # 转换 task_type 字符串为枚举
        from core.infra.worker.multi_process.task_type import TaskType
        task_type_map = {
            'CPU_INTENSIVE': TaskType.CPU_INTENSIVE,
            'IO_INTENSIVE': TaskType.IO_INTENSIVE,
            'MIXED': TaskType.MIXED,
        }
        task_type_str = module_config.get('task_type', 'MIXED')
        task_type = task_type_map.get(task_type_str.upper(), TaskType.MIXED)
        
        return {
            'task_type': task_type,
            'reserve_cores': module_config.get('reserve_cores', 2)
        }