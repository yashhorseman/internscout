"""At most `limit` events per key in any `seconds`. Kept in memory: one server process."""
import time
from collections import deque
from threading import Lock


class SlidingWindow:
    def __init__(self, limit: int, seconds: float, clock=time.monotonic):
        self.limit, self.seconds, self.clock = limit, seconds, clock
        self.events: dict[str, deque] = {}
        self.lock = Lock()

    def allow(self, *keys: str) -> bool:
        """Count one event against every key, unless any of them is already full."""
        with self.lock:
            now = self.clock()
            for key in list(self.events):  # forget old events and idle keys
                queue = self.events[key]
                while queue and now - queue[0] >= self.seconds:
                    queue.popleft()
                if not queue:
                    del self.events[key]
            if any(len(self.events.get(key, ())) >= self.limit for key in keys):
                return False
            for key in keys:
                self.events.setdefault(key, deque()).append(now)
            return True
