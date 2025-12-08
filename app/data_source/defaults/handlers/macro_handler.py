from app.data_source.base_handler import BaseHandler
from typing import Dict, Any


class GDPHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class CPIHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class PPIHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class PMIHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class ShiborHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class LPRHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass


class MoneySupplyHandler(BaseHandler):
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        pass

