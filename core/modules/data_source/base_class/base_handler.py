class BaseHandler:
    """
    Base Handler class
    """
    def __init__(self, data_source_name: str, schema: DataSourceSchema, config: DataSourceConfig):
        self.context = {
            "data_source_name": data_source_name,
            "schema": schema,
            "config": config,
        }
        self.apis = self._resolve_apis(self.context)
        self.fetch_tasks = self._resolve_tasks(self.context, self.apis)
        self.fetched_data = None
        self.normalized_data = None


    def _resolve_apis(self, context: Dict[str, Any]):
        # wrapper API into ApiJob
        pass

    def _resolve_tasks(self, context: Dict[str, Any], apis: List[ApiJob]):
        # tuple sort for ApiJob instances based on dependencies
        # resolve rate limit for each step
        pass

    def _reset(self):
        self.fetched_data = None
        self.normalized_data = None

    def execute(self):
        self._reset()
        self.fetch_tasks = self.before_fetch(self.context, self.apis, self.fetch_tasks)
        self.fetched_data = self.fetch(self.context, self.fetch_tasks)
        self.fetched_data = self.after_fetch(self.context, self.fetched_data, self.fetch_tasks)
        self.fetched_data = self.before_normalize(self.context, self.fetched_data, self.fetch_tasks)
        self.normalized_data = self.normalize(self.context, self.fetched_data)
        self.normalized_data = self.after_normalize(self.context,self.normalized_data)

    def before_fetch(self, context: Dict[str, Any], apis: List[ApiJob], fetch_tasks: List[DataSourceTask]):
        # 可重写，有默认行为
        return self.fetch_tasks

    def fetch(self, context: Dict[str, Any], fetch_tasks: List[DataSourceTask]):
        # execute tasks
        fetched_data = {}
        for task in fetch_tasks:
            result = task.execute()
            fetched_data = {
                **fetched_data,
                **result,
            }
        return fetched_data

    def after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], fetch_tasks: List[DataSourceTask]):
        # 可重写，有默认行为
        return fetched_data

    def before_normalize(self, context: Dict[str, Any], fetched_data: Dict[str, Any], fetch_tasks: List[DataSourceTask]):
        # 可重写，有默认行为
        pass

    def normalize(self, context: Dict[str, Any], fetched_data: Dict[str, Any]):
        # normalize data
        self._map_data_by_schema(fetched_data, self.context)
        pass

    def after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]):
        # 可重写，有默认行为
        pass

    def _map_data_by_schema(self, context: Dict[str, Any], fetched_data: Dict[str, Any]):
        # map data by schema
        pass