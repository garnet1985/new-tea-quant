"""File Utils - 文件操作工具（原子操作）"""
from typing import Union, Optional, Dict, Any
from pathlib import Path
import json
import logging


logger = logging.getLogger(__name__)


class FileUtils:
    """文件操作工具类（静态方法集合）"""

    @staticmethod
    def find_file(
        start_dir: Path,
        filename: str,
        *,
        search_parents: bool = False,
        max_depth: int = 10
    ) -> Optional[Path]:
        """查找单个文件（向上搜索或向下搜索）"""
        if not start_dir.exists():
            logger.debug(f"起始目录不存在: {start_dir}")
            return None

        if search_parents:
            # 向上搜索父目录
            return FileUtils._find_in_parents(start_dir, filename, max_depth)
        else:
            # 向下搜索子目录
            return FileUtils._find_in_children(start_dir, filename, max_depth)

    @staticmethod
    def _find_in_parents(start_dir: Path, filename: str, max_depth: int) -> Optional[Path]:
        """向上搜索父目录"""
        current_dir = start_dir
        depth = 0

        while depth < max_depth:
            file_path = current_dir / filename
            if file_path.exists() and file_path.is_file():
                logger.debug(f"找到文件: {file_path}")
                return file_path

            # 移动到父目录
            parent = current_dir.parent
            if parent == current_dir:  # 已到达根目录
                break
            current_dir = parent
            depth += 1

        logger.debug(f"向上搜索未找到文件: {filename}")
        return None

    @staticmethod
    def _find_in_children(start_dir: Path, filename: str, max_depth: int) -> Optional[Path]:
        """向下搜索子目录（使用os.walk，兼容Python 3.9）"""
        import os
        depth = 0

        for root, dirs, files in os.walk(start_dir):
            # 检查深度
            current_depth = len(Path(root).relative_to(start_dir).parts)
            if current_depth > max_depth:
                continue

            if filename in files:
                file_path = Path(root) / filename
                logger.debug(f"找到文件: {file_path}")
                return file_path

        logger.debug(f"向下搜索未找到文件: {filename}")
        return None

    @staticmethod
    def load_file_content(
        file_path: Path,
        *,
        encoding: str = 'utf-8',
        auto_detect_format: bool = True
    ) -> Union[str, Dict[str, Any], bytes, None]:
        """加载单个文件内容（自动识别JSON/YAML/文本）"""
        if not file_path.exists():
            logger.debug(f"文件不存在: {file_path}")
            return None

        if not file_path.is_file():
            logger.warning(f"路径不是文件: {file_path}")
            return None

        if auto_detect_format:
            # 根据文件扩展名自动识别格式
            suffix = file_path.suffix.lower()
            if suffix == '.json':
                return FileUtils.load_json(file_path)
            elif suffix in ['.yaml', '.yml']:
                return FileUtils.load_yaml(file_path)
            else:
                # 默认作为文本文件加载
                return FileUtils.load_text(file_path, encoding=encoding)
        else:
            # 直接作为文本加载
            return FileUtils.load_text(file_path, encoding=encoding)

    @staticmethod
    def load_text(file_path: Path, *, encoding: str = 'utf-8') -> Optional[str]:
        """加载文本文件"""
        try:
            content = file_path.read_text(encoding=encoding)
            logger.debug(f"成功加载文本文件: {file_path}")
            return content
        except UnicodeDecodeError as e:
            logger.warning(f"文本编码错误: {file_path}, {e}")
            return None
        except Exception as e:
            logger.error(f"加载文本文件失败: {file_path}, {e}")
            return None

    @staticmethod
    def load_json(file_path: Path) -> Optional[Dict[str, Any]]:
        """加载JSON文件"""
        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"成功加载JSON文件: {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"JSON格式错误: {file_path}, {e}")
            return None
        except Exception as e:
            logger.error(f"加载JSON文件失败: {file_path}, {e}")
            return None

    @staticmethod
    def load_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
        """加载YAML文件（需要安装 pyyaml）"""
        try:
            import yaml
            with file_path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            logger.debug(f"成功加载YAML文件: {file_path}")
            return data
        except ImportError:
            logger.warning(f"未安装pyyaml，无法加载YAML文件: {file_path}")
            return None
        except yaml.YAMLError as e:
            logger.warning(f"YAML格式错误: {file_path}, {e}")
            return None
        except Exception as e:
            logger.error(f"加载YAML文件失败: {file_path}, {e}")
            return None

    @staticmethod
    def save_file_content(
        file_path: Path,
        content: Union[str, Dict[str, Any], bytes],
        *,
        encoding: str = 'utf-8',
        ensure_parent_exists: bool = True
    ) -> bool:
        """保存文件内容（自动识别JSON/YAML/文本）"""
        try:
            # 确保父目录存在
            if ensure_parent_exists and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # 根据内容类型和文件扩展名保存
            if isinstance(content, bytes):
                # 二进制数据直接写入
                file_path.write_bytes(content)
            elif isinstance(content, dict):
                # 字典数据，根据文件扩展名选择格式
                suffix = file_path.suffix.lower()
                if suffix == '.json':
                    FileUtils.save_json(file_path, content)
                elif suffix in ['.yaml', '.yml']:
                    FileUtils.save_yaml(file_path, content)
                else:
                    # 默认保存为JSON
                    FileUtils.save_json(file_path, content)
            elif isinstance(content, str):
                # 文本数据直接写入
                file_path.write_text(content, encoding=encoding)
            else:
                logger.warning(f"不支持的内容类型: {type(content)}")
                return False

            logger.debug(f"成功保存文件: {file_path}")
            return True

        except Exception as e:
            logger.error(f"保存文件失败: {file_path}, {e}")
            return False

    @staticmethod
    def save_json(file_path: Path, data: Dict[str, Any], *, encoding: str = 'utf-8') -> bool:
        """保存JSON文件"""
        try:
            with file_path.open('w', encoding=encoding) as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"成功保存JSON文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存JSON文件失败: {file_path}, {e}")
            return False

    @staticmethod
    def save_yaml(file_path: Path, data: Dict[str, Any], *, encoding: str = 'utf-8') -> bool:
        """保存YAML文件（需要安装 pyyaml）"""
        try:
            import yaml
            with file_path.open('w', encoding=encoding) as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
            logger.debug(f"成功保存YAML文件: {file_path}")
            return True
        except ImportError:
            logger.warning(f"未安装pyyaml，无法保存YAML文件: {file_path}")
            return False
        except Exception as e:
            logger.error(f"保存YAML文件失败: {file_path}, {e}")
            return False

    @staticmethod
    def load_python_config(file_path: Path, var_name: str = "settings") -> Optional[Dict[str, Any]]:
        """加载Python配置文件并提取指定变量"""
        if not file_path.exists():
            logger.debug(f"Python配置文件不存在: {file_path}")
            return None

        if not file_path.is_file():
            logger.warning(f"路径不是文件: {file_path}")
            return None

        try:
            # 读取文件内容
            content = file_path.read_text(encoding='utf-8')

            # 创建执行环境
            exec_globals = {
                '__file__': str(file_path),
                '__name__': '__main__',
            }

            # 执行Python代码
            exec(content, exec_globals)

            # 提取指定变量
            if var_name in exec_globals:
                config = exec_globals[var_name]
                logger.debug(f"成功加载Python配置文件: {file_path}, 提取变量: {var_name}")
                return config
            else:
                logger.warning(f"Python文件 {file_path} 未定义变量: {var_name}")
                return None

        except Exception as e:
            logger.error(f"加载Python配置文件失败: {file_path}, {e}")
            return None


# ========== 便捷函数 ==========

def find_file(
    start_dir: Path,
    filename: str,
    *,
    search_parents: bool = False
) -> Optional[Path]:
    """便捷函数：查找单个文件"""
    return FileUtils.find_file(start_dir, filename, search_parents=search_parents)

def load_json(file_path: Path) -> Optional[Dict[str, Any]]:
    """便捷函数：加载JSON文件"""
    return FileUtils.load_json(file_path)

def load_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
    """便捷函数：加载YAML文件"""
    return FileUtils.load_yaml(file_path)

def load_file_content(file_path: Path, *, encoding: str = 'utf-8', auto_detect_format: bool = True) -> Optional[Union[str, Dict[str, Any], bytes]]:
    """便捷函数：加载文件内容（自动识别JSON/YAML/文本）"""
    return FileUtils.load_file_content(file_path, encoding=encoding, auto_detect_format=auto_detect_format)

def save_file_content(file_path: Path, content: Union[str, Dict[str, Any], bytes], *, encoding: str = 'utf-8', ensure_parent_exists: bool = True) -> bool:
    """便捷函数：保存文件内容（自动识别JSON/YAML/文本）"""
    return FileUtils.save_file_content(file_path, content, encoding=encoding, ensure_parent_exists=ensure_parent_exists)

def load_python_config(file_path: Path, var_name: str = "settings") -> Optional[Dict[str, Any]]:
    """便捷函数：加载Python配置文件"""
    return FileUtils.load_python_config(file_path, var_name)