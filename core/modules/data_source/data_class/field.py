@dataclass
class DataSourceField:
    """
    字段定义
    
    用于定义数据源中的字段类型、是否必需等信息。
    """
    
    def __init__(self, type: Type, required: bool = True, description: str = "", default: Any = None):
        self.type = type
        self.required = required
        self.description = description
        self.default = default