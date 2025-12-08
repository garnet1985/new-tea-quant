import json
from typing import Dict, Any, Optional
from loguru import logger


class DataSourceManager:
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self._schemas: Dict[str, Any] = {}
        self._handlers: Dict[str, Any] = {}
        
        self._load_schemas()
        self._load_mapping()
    
    def _load_schemas(self):
        pass
    
    def _load_mapping(self):
        pass
    
    def _load_handler(self, ds_name: str, handler_path: str):
        pass
    
    async def renew(
        self, 
        ds_name: str, 
        context: Dict[str, Any],
        save: bool = True
    ) -> Dict:
        pass
    
    def list_data_sources(self) -> list:
        pass
    
    def get_schema(self, ds_name: str):
        pass
