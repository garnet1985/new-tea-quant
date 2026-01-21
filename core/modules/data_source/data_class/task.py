class DataSourceTask:
    """
    DataSource Task class
    """
    def __init__(self, task_name: str, task_params: Dict[str, Any]):
        self.task_name = task_name
        self.task_params = task_params

    def execute(self):
        pass