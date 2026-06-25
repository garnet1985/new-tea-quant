import logging
import sys


logger = logging.getLogger(__name__)


class IconService:
    """跨平台图标服务：macOS/Linux 用 emoji，Windows GBK 用 ASCII 文本"""

    # 每个 icon 对应多个 value：emoji (macOS/Linux) + ascii (Windows GBK)
    ICONS: dict[str, dict[str, str]] = {
        # 结论类
        'info': {'emoji': 'ℹ️', 'ascii': '[INFO]'},
        'warning': {'emoji': '⚠️', 'ascii': '[WARN]'},
        'error': {'emoji': '❌', 'ascii': '[FAIL]'},
        'success': {'emoji': '✅', 'ascii': '[OK]'},
        'ongoing': {'emoji': '🔄', 'ascii': '[...]'},
        
        # 功能类
        'search': {'emoji': '🔍', 'ascii': '[SEARCH]'},
        'calendar': {'emoji': '📅', 'ascii': '[DATE]'},
        'bar_chart': {'emoji': '📊', 'ascii': '[CHART]'},
        'line_chart': {'emoji': '📈', 'ascii': '[UP]'},
        'downward_trend': {'emoji': '📉', 'ascii': '[DOWN]'},
        'money': {'emoji': '💰', 'ascii': '[MONEY]'},
        'rocket': {'emoji': '🚀', 'ascii': '[START]'},
        'gear': {'emoji': '🔧', 'ascii': '[CONFIG]'},
        'clock': {'emoji': '🕙', 'ascii': '[TIME]'},
        'target': {'emoji': '🎯', 'ascii': '[TARGET]'},
        
        # 状态点
        'green_dot': {'emoji': '🟢', 'ascii': '[ON]'},
        'red_dot': {'emoji': '🔴', 'ascii': '[OFF]'},
        'orange_dot': {'emoji': '🟠', 'ascii': '[WARN]'},
        'yellow_dot': {'emoji': '🟡', 'ascii': '[WAIT]'},
        'blue_dot': {'emoji': '🔵', 'ascii': '[INFO]'},
        'purple_dot': {'emoji': '🟣', 'ascii': '[INFO]'},
        'white_dot': {'emoji': '⚪', 'ascii': '[INFO]'},
        'black_dot': {'emoji': '⚫', 'ascii': '[INFO]'},
        'brown_dot': {'emoji': '🟤', 'ascii': '[INFO]'},
    }

    # 别名映射：一个 icon 有多个名字
    ALIASES: dict[str, str] = {
        'information': 'info',
        'exclamation': 'warning',
        'failed': 'error',
        'err': 'error',
        'cross': 'error',
        'check': 'success',
        'pass': 'success',
        'ok': 'success',
        'done': 'success',
        'chart': 'bar_chart',
        'upward_trend': 'line_chart',
        'increase': 'line_chart',
        'decrease': 'downward_trend',
        'stock': 'money',
        'dot': 'green_dot',
    }

    def __init__(self):
        pass

    @staticmethod
    def _supports_emoji() -> bool:
        """检测当前系统是否支持 emoji 输出"""
        # Windows cmd.exe 默认 GBK 编码，不支持 emoji
        if sys.platform == "win32":
            # 如果 stdout 已经设置为 UTF-8，则支持 emoji
            if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding == 'utf-8':
                return True
            return False
        # macOS/Linux 默认 UTF-8，支持 emoji
        return True

    @staticmethod
    def get(icon_name: str) -> str:
        """
        获取图标字符串（自动适配系统）
        
        Args:
            icon_name: 图标名称（支持别名，大小写不敏感）
            
        Returns:
            str: emoji（macOS/Linux）或 ASCII 文本（Windows GBK）
        """
        icon_name = icon_name.lower()
        
        # 处理别名
        icon_key = IconService.ALIASES.get(icon_name, icon_name)
        
        # 获取 icon 定义
        icon_def = IconService.ICONS.get(icon_key)
        if not icon_def:
            logger.error(f"Unknown icon name: {icon_name}")
            return ''
        
        # 根据系统返回对应的 value
        if IconService._supports_emoji():
            return icon_def['emoji']
        else:
            return icon_def['ascii']


# 简化的图标获取函数
def i(icon_name: str) -> str:
    """
    简化的图标获取函数
    
    Usage:
        from core.utils import i
        icon = i("green_dot")  # macOS/Linux: "🟢", Windows GBK: "[ON]"
    
    Args:
        icon_name: 图标名称
        
    Returns:
        str: 图标字符串（自动适配系统）
    """
    return IconService.get(icon_name)