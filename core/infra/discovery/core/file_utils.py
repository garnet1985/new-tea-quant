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
    def find_in_tree(
        base_dir: Path,
        key: str,
        filename: str,
    ) -> Optional[Path]:
        """在目录树中按「目录名 = key」定位 ``{key}/{filename}``。

        顺序：
        1. ``{base_dir}/{key}/{filename}``（直达）
        2. 递归匹配 ``**/{key}/{filename}``（嵌套分组目录）

        ``key`` 须为单段目录名（禁止 ``/``、``\\``、``..``）。
        """
        key_name = str(key or "").strip()
        file_name = str(filename or "").strip()
        if not key_name or not file_name:
            raise ValueError("find_in_tree 要求非空 key 与 filename")
        if (
            "/" in key_name
            or "\\" in key_name
            or key_name == ".."
            or ".." in key_name.split("/")
        ):
            raise ValueError(f"非法 find_in_tree key: {key!r}")
        if "/" in file_name or "\\" in file_name:
            raise ValueError(f"非法 find_in_tree filename: {filename!r}")

        if not base_dir.exists() or not base_dir.is_dir():
            logger.debug("find_in_tree 基础目录不存在: %s", base_dir)
            return None

        direct = base_dir / key_name / file_name
        if direct.is_file():
            return direct.resolve()

        matches = sorted(
            p.resolve()
            for p in base_dir.rglob(f"{key_name}/{file_name}")
            if p.is_file()
        )
        if matches:
            logger.debug("find_in_tree 命中: %s", matches[0])
            return matches[0]

        logger.debug(
            "find_in_tree 未找到 %s/%s under %s", key_name, file_name, base_dir
        )
        return None

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
        """向下搜索子目录（``os.walk`` + 深度限制）。"""
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
        """加载 YAML 文件。需要已安装 ``pyyaml``；缺失时抛出 ``RuntimeError``。"""
        try:
            import yaml
        except ImportError as e:
            raise RuntimeError(
                "加载 YAML 需要安装 pyyaml（pip install pyyaml）"
            ) from e
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            logger.debug("成功加载YAML文件: %s", file_path)
            return data
        except yaml.YAMLError as e:
            logger.warning("YAML格式错误: %s, %s", file_path, e)
            return None
        except Exception as e:
            logger.error("加载YAML文件失败: %s, %s", file_path, e)
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
    def save_yaml(file_path: Path, data: Dict[str, Any], *, encoding: str = "utf-8") -> bool:
        """保存 YAML 文件。需要已安装 ``pyyaml``；缺失时抛出 ``RuntimeError``。"""
        try:
            import yaml
        except ImportError as e:
            raise RuntimeError(
                "保存 YAML 需要安装 pyyaml（pip install pyyaml）"
            ) from e
        try:
            with file_path.open("w", encoding=encoding) as f:
                yaml.safe_dump(
                    data, f, default_flow_style=False, allow_unicode=True
                )
            logger.debug("成功保存YAML文件: %s", file_path)
            return True
        except Exception as e:
            logger.error("保存YAML文件失败: %s, %s", file_path, e)
            return False

    @staticmethod
    def load_python_config(
        file_path: Path, var_name: str = "settings"
    ) -> Optional[Dict[str, Any]]:
        """加载受信 Python 配置文件并提取指定变量。

        使用 ``exec`` 执行文件内容；**仅用于项目内可信配置**（如 userspace
        settings.py），不要对不可信输入调用。
        """
        if not file_path.exists():
            logger.debug("Python配置文件不存在: %s", file_path)
            return None

        if not file_path.is_file():
            logger.warning("路径不是文件: %s", file_path)
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            exec_globals = {
                "__file__": str(file_path),
                "__name__": "__main__",
            }
            exec(content, exec_globals)

            if var_name in exec_globals:
                config = exec_globals[var_name]
                logger.debug(
                    "成功加载Python配置文件: %s, 提取变量: %s", file_path, var_name
                )
                return config
            logger.warning("Python文件 %s 未定义变量: %s", file_path, var_name)
            return None

        except Exception as e:
            logger.error("加载Python配置文件失败: %s, %s", file_path, e)
            return None
