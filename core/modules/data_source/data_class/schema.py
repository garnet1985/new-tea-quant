class DataSourceSchema:
    """
    DataSource Schema class
    """
    def __init__(self, data_source_name: str):
        self.data_source_name = data_source_name

    def _discover_schema(self):
        pass

    def _is_schema_valid(self):
        pass

    def _parse_schema(self):
        pass