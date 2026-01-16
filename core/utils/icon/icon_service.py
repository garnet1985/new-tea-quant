from loguru import logger


class IconService:
    def __init__(self):
        pass

    @staticmethod
    def get(icon_name: str) -> str:
        icon_name = icon_name.lower()

        # for conclusion
        
        if (icon_name == 'info' 
            or icon_name == 'information'
            ):
            return 'ℹ️'
        elif (icon_name == 'warning' 
            or icon_name == 'exclamation'
            ):
            return '⚠️'
        elif (icon_name == 'error' 
            or icon_name == 'failed'
            or icon_name == 'err'
            or icon_name == 'cross'
            ):
            return '❌'
        elif (icon_name == 'success' 
            or icon_name == 'check'
            or icon_name == 'pass'
            or icon_name == 'ok'
            or icon_name == 'done'
            ):
            return '✅'

        # for info
        elif icon_name == 'search':
            return '🔍'
        elif icon_name == 'calendar':
            return '📅'
        elif (icon_name == 'bar_chart' 
            or icon_name == 'chart'
            ):
            return '📊'
        elif (icon_name == 'line_chart' 
            or icon_name == 'upward_trend'
            or icon_name == 'increase'
            ):
            return '📈'
        elif (icon_name == 'downward_trend'
            or icon_name == 'decrease'
            ):
            return '📉'
        elif (icon_name == 'money' 
            or icon_name == 'stock'
            ):
            return '💰'
        elif icon_name == 'rocket':
            return '🚀'
        elif icon_name == 'gear':
            return '🔧'
        elif icon_name == 'clock':
            return '🕙'
        elif icon_name == 'target':
            return '🎯'
        elif icon_name == 'ongoing':
            return '🔄'

        # for dot
        elif (icon_name == 'green_dot' 
            or icon_name == 'dot'
            ):
            return '🟢'
        elif icon_name == 'red_dot':
            return '🔴'
        elif icon_name == 'orange_dot':
            return '🟠'
        elif icon_name == 'yellow_dot':
            return '🟡'
        elif icon_name == 'blue_dot':
            return '🔵'
        elif icon_name == 'purple_dot':
            return '🟣'
        elif icon_name == 'white_dot':
            return '⚪'
        elif icon_name == 'black_dot':
            return '⚫'
        elif icon_name == 'brown_dot':
            return '🟤'

        else:
            logger.error(f"Unknown icon name: {icon_name}")
            return ''  # 返回空字符串而不是 None


# 简化的图标获取函数
def i(icon_name: str) -> str:
    """
    简化的图标获取函数
    
    Usage:
        from core.utils import i
        icon = i("green_dot")  # 返回 "🟢"
    
    Args:
        icon_name: 图标名称
        
    Returns:
        str: 图标 emoji 字符串
    """
    return IconService.get(icon_name)