"""Config Manager - 配置管理器"""

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
    """配置管理器 - 处理默认配置和用户配置的加载与合并"""
    
    @staticmethod
    def load_with_defaults(
        default_path: Path,
        user_path: Path,
        *,
        deep_merge_fields: Optional[Set[str]] = None,
        override_fields: Optional[Set[str]] = None,
        file_type: str = "json"
    ) -> Dict[str, Any]:
        """
        加载配置（用户配置覆盖默认配置）

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
                # 3. 使用内部合并逻辑
                return ConfigManager.deep_merge_config(
                    defaults,
                    user_config,
                    deep_merge_fields=deep_merge_fields,
                    override_fields=override_fields,
                )
        
        return defaults

    @staticmethod
    def deep_merge_config(
        defaults: Dict[str, Any],
        custom: Dict[str, Any],
        deep_merge_fields: Optional[Set[str]] = None,
        override_fields: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        合并默认配置与用户配置片段。

        合并规则：
        1. 对于 deep_merge_fields 中的字段，进行嵌套 dict 合并；
        2. 对于 override_fields 中的字段，custom 完全覆盖 defaults；
        3. 其他字段：浅层合并，custom 覆盖 defaults。
        """
        deep_merge_fields = deep_merge_fields or set()
        override_fields = override_fields or set()

        # 先进行浅层合并（custom 覆盖 defaults）
        merged = {**defaults, **custom}

        # 对于需要深度合并的字段，进行递归 dict 合并
        for field in deep_merge_fields:
            if field in defaults and field in custom:
                if isinstance(defaults[field], dict) and isinstance(custom[field], dict):
                    merged[field] = ConfigManager._deep_merge_dict(
                        defaults[field], custom[field]
                    )
                else:
                    merged[field] = custom[field]

        # override_fields 已在浅层合并中处理，这里不需要额外逻辑
        return merged

    @staticmethod
    def merge_mapping_configs(
        defaults: Dict[str, Any],
        custom: Dict[str, Any],
        deep_merge_fields: Optional[Set[str]] = None,
        override_fields: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        合并「名称 -> 配置 dict」映射（如 data_sources 各 handler 配置）。

        对每个键分别调用 ``deep_merge_config``；仅出现在一侧的键保留该侧配置。
        """
        all_keys = set(defaults.keys()) | set(custom.keys())
        out: Dict[str, Any] = {}
        for key in all_keys:
            if key in defaults and key in custom:
                out[key] = ConfigManager.deep_merge_config(
                    defaults[key],
                    custom[key],
                    deep_merge_fields=deep_merge_fields,
                    override_fields=override_fields,
                )
            elif key in custom:
                out[key] = custom[key]
            else:
                out[key] = defaults[key]
        return out

    @staticmethod
    def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归合并嵌套 dict（override 覆盖 base 同键叶子值）

        Args:
            base: 基础字典
            override: 覆盖字典

        Returns:
            合并后的字典
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def load_json_file(path: Path) -> Dict[str, Any]:
        """
        加载 JSON 配置文件

        Args:
            path: JSON 文件路径

        Returns:
            配置字典，如果文件不存在或加载失败返回空字典
        """
        return ConfigManager._load_file(path, "json") or {}

    @staticmethod
    def parse_python_config(path: Path, var_name: str = "settings") -> Dict[str, Any]:
        """
        解析 Python 配置文件（涉及动态导入，是复杂解析）

        Args:
            path: Python 文件路径
            var_name: 配置变量名（默认为 "settings"）

        Returns:
            配置字典，如果文件不存在或加载失败返回空字典

        Example:
            # settings.py 中定义：
            # settings = {"name": "example", "params": {...}}

            config = ConfigManager.parse_python_config(
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
        from core.infra.project_context.contracts import OverridableConfigNotFoundError
        from .discovery_manager import DiscoveryManager

        try:
            return DiscoveryManager.load_overridable_config(
                "",
                config_name,
                deep_merge_fields=deep_merge_fields,
                override_fields=override_fields,
                file_type="json",
            )
        except OverridableConfigNotFoundError:
            # 可选 core 配置：缺文件不阻断调用方（与 load_overridable_config 强失败区分）
            return {}

    # =========================
    # 业务级便捷访问方法
    # =========================
    
    @staticmethod
    def load_benchmark_stock_index_list() -> List[Dict[str, Any]]:
        """
        获取全局基准股票指数列表（benchmark_stock_index_list）。

        - 默认值来自 core/default_config/data.json；
        - 用户可以在 userspace/config/data.json 中覆盖或扩展该列表，
          合并逻辑由 ConfigManager.load_core_config 负责。
        """
        config = ConfigManager.load_data_config()
        index_list = config.get("benchmark_stock_index_list") or []
        if not isinstance(index_list, list):
            logger.warning("benchmark_stock_index_list 不是列表类型，已返回空列表")
            return []
        return index_list
    
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
            database_type: 数据库类型（'postgresql', 'mysql'）
                          如果为 None，从配置文件中获取
        
        Returns:
            合并后的数据库配置字典，格式：
            {
                'database_type': 'postgresql',
                'postgresql': {...},  # 或 'mysql': {...}
                'batch_write': {...}
            }
        """
        from .path_manager import PathManager
        
        # 1. 加载公用配置（默认）- 包含 database_type
        common_default_path = PathManager.get_default_config_root() / "database" / "common.json"
        common_default = ConfigManager.load_json_file(common_default_path) or {}
        
        # 2. 确定数据库类型（优先级：参数 > 用户 common > 默认 common > 默认值）
        if database_type is None:
            # 先检查用户配置
            common_user_path = PathManager.get_user_config_root() / "database" / "common.json"
            common_user = ConfigManager.load_json_file(common_user_path) or {}
            database_type = (
                common_user.get('database_type') or 
                common_default.get('database_type') or 
                'postgresql'
            ).lower()
        
        # 3. 加载数据库专用配置（默认）
        db_default_path = PathManager.get_default_config_root() / "database" / f"{database_type}.json"
        db_default = ConfigManager.load_json_file(db_default_path) or {}
        
        # 4. 合并默认配置
        # 将 _advanced 字段展开到顶层
        db_config = ConfigManager._expand_advanced_fields(db_default)
        
        default_config = {
            'database_type': database_type,
            database_type: db_config,
            'batch_write': common_default.get('batch_write', {})
        }
        
        # 5. 加载用户公用配置（如果存在）
        common_user_path = PathManager.get_user_config_root() / "database" / "common.json"
        common_user = ConfigManager.load_json_file(common_user_path) or {}
        
        # 6. 加载用户数据库专用配置（如果存在）
        db_user_path = PathManager.get_user_config_root() / "database" / f"{database_type}.json"
        db_user_raw = ConfigManager.load_json_file(db_user_path) or {}
        # 支持两种格式：
        #  - 扁平：{ "user": "...", "password": "..." }
        #  - wrapper：{ "postgresql": { "user": "...", "password": "..." } }
        db_user = (
            db_user_raw.get(database_type)
            if isinstance(db_user_raw, dict)
            and database_type in db_user_raw
            and isinstance(db_user_raw.get(database_type), dict)
            else db_user_raw
        )
        
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
            merged_config = ConfigManager.deep_merge_config(
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
    def load_data_config() -> Dict[str, Any]:
        """
        加载数据配置（合并后的完整配置）
        
        Returns:
            数据配置字典，包含 default_start_date, decimal_places 等
        """
        return ConfigManager.load_core_config(
            'data',
            deep_merge_fields={'decimal_places'},
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
        data_config = ConfigManager.load_data_config()
        return data_config.get('default_start_date')

    @staticmethod
    def get_default_market_profile_key() -> str:
        """``data.json`` → ``default_market_profile_key``（全系统默认市场 profile）。"""
        data_config = ConfigManager.load_data_config()
        key = str(data_config.get("default_market_profile_key") or "china_a_stock").strip()
        return key or "china_a_stock"

    @staticmethod
    def get_as_of_latest_completed_trading_date() -> Optional[str]:
        """
        data.json ``as_of_latest_completed_trading_date``（全系统 as-of 权威）。

        配置后 ``CalendarService.get_latest_completed_trading_date`` 直接返回该值。
        """
        data_config = ConfigManager.load_data_config()
        raw = data_config.get("as_of_latest_completed_trading_date")
        if raw is None:
            return None
        s = str(raw).strip().replace("-", "")[:8]
        if len(s) == 8 and s.isdigit():
            return s
        return None

    @staticmethod
    def get_use_sample_stock_list() -> Optional[int]:
        """
        开发样本股票池规模（``core/modules/data_source/dev/stock_pool/stratified_N.csv``）。

        - 正整数 ``N`` → 使用 ``stratified_N.csv``
        - 未配置 / 空 / 非正数 → 全市场
        """
        data_config = ConfigManager.load_data_config()
        raw = data_config.get("use_sample_stock_list")
        if raw is None:
            return None
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            return raw if raw > 0 else None
        if isinstance(raw, str):
            s = raw.strip()
            if s.isdigit():
                n = int(s)
                return n if n > 0 else None
        return None
    
    @staticmethod
    def _decimal_places_block() -> Dict[str, Any]:
        """``data.json`` → ``decimal_places`` 块（兼容历史顶层 int）。"""
        data_config = ConfigManager.load_data_config()
        raw = data_config.get("decimal_places", 2)
        if isinstance(raw, int):
            return {"default": raw}
        if isinstance(raw, dict):
            return raw
        return {"default": 2}

    @staticmethod
    def get_decimal_places() -> int:
        """
        获取默认小数位数（``decimal_places.default``）。
        
        Returns:
            小数位数（默认 2）
        """
        block = ConfigManager._decimal_places_block()
        try:
            return max(0, int(block.get("default", 2)))
        except (TypeError, ValueError):
            return 2

    @staticmethod
    def get_adj_factor_event_decimal_places() -> Dict[str, int]:
        """
        adj_factor_event 爬取舍入精度（``decimal_places.adj_factor_event``）。

        Returns:
            ``factor_places`` / ``price_places`` / ``diff_places``
        """
        block = ConfigManager._decimal_places_block()
        adj = block.get("adj_factor_event")
        if isinstance(adj, dict) and adj:
            try:
                factor = max(0, int(adj.get("factor_places", 4)))
                price = max(0, int(adj.get("price_places", 3)))
                diff = max(0, int(adj.get("diff_places", 4)))
            except (TypeError, ValueError):
                factor, price, diff = 4, 3, 4
        else:
            dp = ConfigManager.get_decimal_places()
            factor, price, diff = 4, max(2, dp), 4
        return {
            "factor_places": factor,
            "price_places": price,
            "diff_places": diff,
        }
    
    @staticmethod
    def get_database_type() -> str:
        """
        获取当前使用的数据库类型
        
        Returns:
            数据库类型（'postgresql', 'mysql'）
        """
        db_config = ConfigManager.load_database_config()
        return db_config.get('database_type', 'postgresql')
