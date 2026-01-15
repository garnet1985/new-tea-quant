"""
Tag 系统全局配置

包含 Tag 系统的全局配置常量。
"""

from pathlib import Path
from core.infra.project_context import PathManager

# ========================================================================
# Scenarios 根目录配置
# ========================================================================

# Scenarios 根目录（使用 PathManager 获取）
def get_scenarios_root() -> Path:
    """获取标签场景根目录"""
    return PathManager.userspace() / "tags"

# 保持向后兼容（返回字符串路径）
DEFAULT_SCENARIOS_ROOT = "app/userspace/tags"  # 已废弃，使用 get_scenarios_root()