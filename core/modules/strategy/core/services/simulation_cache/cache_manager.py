class SimulationCacheManager:
    """模拟缓存管理器。"""

    @staticmethod
    def get_cache(key: str) -> Dict[str, Any]:
        """获取模拟缓存。"""
        return SimulationCacheManager.cache.get(key)

    @staticmethod
    def set_cache(key: str, value: Dict[str, Any]) -> None:
        """设置模拟缓存。"""
        SimulationCacheManager.cache[key] = value
