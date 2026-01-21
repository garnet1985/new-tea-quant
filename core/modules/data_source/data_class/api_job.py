class ApiJob:
    """
    Api Job class
    """
    def __init__(self, api_name: str, api_params: Dict[str, Any]):
        self.api_name = api_name
        self.api_params = api_params
        self.depends_on = depends_on
        self.rate_limit = rate_limit

    def execute(self):
        pass