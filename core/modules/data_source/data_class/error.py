class DataSourceError(Exception):
    """
    DataSource Error class
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ProviderError(Exception):
    """Provider 统一错误类"""
    
    def __init__(self, provider: str, api: str, original_error: Exception):
        self.provider = provider
        self.api = api
        self.original_error = original_error
        super().__init__(f"[{provider}.{api}] {original_error}")