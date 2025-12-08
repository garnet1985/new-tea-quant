import time
import threading


class RateLimiter:
    
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.tokens = max_per_minute
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, count: int = 1):
        pass

