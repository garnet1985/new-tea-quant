"""
Module Discovery - 模块自动发现工具

提供通用的模块自动发现功能，支持：
1. 扫描包下的所有模块
2. 从模块中提取特定对象（如 SCHEMA, CONFIG）
3. 支持约定命名
"""
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from loguru import logger
import importlib
import pkgutil


class ModuleDiscovery:
    """
    模块自动发现工具
    
    使用示例：
        # 发现所有 schema 模块
        discovery = ModuleDiscovery()
        schemas = discovery.discover_objects(
            base_module_path="userspace.data_source.handlers",
            object_name="SCHEMA",
            module_pattern="{base_module}.{name}.schema"
        )
        # schemas = {"kline": KlineSchema, "stock_list": StockListSchema}
    """
    
    @staticmethod
    def discover_objects(
        base_module_path: str,
        object_name: str,
        module_pattern: str = "{base_module}.{name}",
        skip_modules: set = None
    ) -> Dict[str, Any]:
        """
        发现所有模块中的特定对象
        
        Args:
            base_module_path: 基础模块路径（如 "userspace.data_source.handlers"）
            object_name: 对象名（如 "SCHEMA", "CONFIG"）
            module_pattern: 模块路径模式（如 "{base_module}.{name}.schema"）
            skip_modules: 跳过的模块名集合
        
        Returns:
            {key: object} 字典（key 通常是模块名）
        """
        if skip_modules is None:
            skip_modules = {"__pycache__", "__init__"}
        
        objects = {}
        
        try:
            base_package = importlib.import_module(base_module_path)
            package_paths = base_package.__path__
            
            # 扫描所有子包
            for importer, modname, ispkg in pkgutil.iter_modules(package_paths):
                if modname in skip_modules or modname.startswith('_'):
                    continue
                
                # 构建模块路径
                module_path = module_pattern.format(
                    base_module=base_module_path,
                    name=modname
                )
                
                try:
                    module = importlib.import_module(module_path)
                    
                    # 获取对象
                    if hasattr(module, object_name):
                        obj = getattr(module, object_name)
                        objects[modname] = obj
                    else:
                        logger.debug(f"模块 {module_path} 没有定义 {object_name}")
                        
                except ImportError:
                    # 模块不存在，跳过
                    continue
                except Exception as e:
                    logger.warning(f"加载模块失败 {module_path}: {e}")
                    continue
            
            logger.debug(f"✅ 发现 {len(objects)} 个 {object_name} 对象")
            
        except ImportError:
            logger.debug(f"包不存在，跳过: {base_module_path}")
        except Exception as e:
            logger.error(f"❌ 发现对象失败 {base_module_path}: {e}")
        
        return objects
    
    @staticmethod
    def discover_modules_by_path(
        base_path: Path,
        module_pattern: str,
        object_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        通过文件路径发现模块（不依赖包结构）
        
        Args:
            base_path: 基础路径（如 PathManager.data_source_handlers()）
            module_pattern: 模块路径模式（如 "userspace.data_source.handlers.{name}.schema"）
            object_name: 要提取的对象名（可选）
        
        Returns:
            {key: module_or_object} 字典
        """
        if not base_path.exists():
            logger.debug(f"路径不存在: {base_path}")
            return {}
        
        modules = {}
        
        # 遍历所有子目录
        for item in base_path.iterdir():
            if not item.is_dir() or item.name.startswith('_'):
                continue
            
            # 构建模块路径
            module_path = module_pattern.format(name=item.name)
            
            try:
                module = importlib.import_module(module_path)
                
                if object_name:
                    # 提取特定对象
                    if hasattr(module, object_name):
                        modules[item.name] = getattr(module, object_name)
                else:
                    # 返回整个模块
                    modules[item.name] = module
                    
            except ImportError:
                continue
            except Exception as e:
                logger.warning(f"加载模块失败 {module_path}: {e}")
                continue
        
        return modules
