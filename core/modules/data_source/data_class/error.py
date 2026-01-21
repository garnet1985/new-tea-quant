class DataSourceError(Exception):
    """
    DataSource Error class
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)