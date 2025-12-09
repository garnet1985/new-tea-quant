from app.data_source.data_source_handler import BaseDataSourceHandler
from typing import Dict, Any


class KlineHandler(BaseDataSourceHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class WeeklyKlineHandler(BaseDataSourceHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class MonthlyKlineHandler(BaseDataSourceHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass

