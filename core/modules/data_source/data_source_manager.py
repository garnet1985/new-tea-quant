from typing import Dict, Any
from loguru import logger

from core.infra.discovery import ModuleDiscovery


class DataSourceManager:
    """
    DataSource Manager class
    """
    def __init__(self):
        self.data_sources = []
        self.mappings = self._discover_mappings()
        self.handlers = self._resolve_all_handlers(self.mappings)

    def execute(self):
        self._refresh_handlers()
        for handler in self.handlers:
            handler.execute()

    def _refresh_handlers(self):
        self.mappings = self._discover_mappings()
        self.handlers = self._discover_handlers()


    def _discover_mappings(self):
        mapping_path = PathManager.get_mapping_root()
        self.mappings = ConfigManager.load_json(mapping_path)


    def _discover_handlers(self) -> Dict[str, Any]:
        for data_source_map in self.mappings.items():
            if data_source_map.get("is_enabled"):
                data_source_name = data_source_map.get("name")
                
                schema = self._discover_schema(data_source_name)
                if not schema:
                    logger.error(f"Schema for data source {data_source_name} not found, skip")
                    continue
                config = self._discover_config(data_source_name)
                if not config:
                    logger.error(f"Config for data source {data_source_name} not found, skip")
                    continue
                handler = self._discover_handler(data_source_name)
                if not handler:
                    logger.error(f"Handler for data source {data_source_name} not found, skip")
                    continue
                self.handlers.append(handler)
            else:
                logger.info(f"Data source {data_source_name} is disabled, skip")


    def _discover_schema(self, data_source_name: str) -> Any:
        # 1. find schema file
        # 2. new Schema DataClass
        # 3. call is valid method of Schema DataClass
        # 4. return Schema DataClass
        pass
    


    def _discover_config(self, data_source_name: str) -> Any:
        # 1. find config file
        # 2. new Config DataClass
        # 3. call is valid method of Config DataClass
        # 4. return Config DataClass
        pass


    def _discover_handler(self, data_source_name: str) -> Any:
        # 1. find handler from mapping info
        # 2. feed schema and config to handler
        # 3. return handler instance
        pass

 