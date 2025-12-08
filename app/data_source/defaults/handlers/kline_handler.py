from app.data_source.base_handler import BaseHandler
from typing import Dict, Any


class TushareDailyKlineHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class TushareWeeklyKlineHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class TushareMonthlyKlineHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass

