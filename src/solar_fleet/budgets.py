"""Shared conservative call budgets; these are local limits, not vendor quotas."""

import asyncio
import time
from collections import defaultdict, deque

from .domain import VendorError


class Budgets:
    """Local conservative budgets, NOT claims about vendor quota. Shared across adapters in one controller."""

    def __init__(self, vendor_per_minute=60, account_per_minute=30, device_per_minute=12):
        self.limits = (vendor_per_minute, account_per_minute, device_per_minute)
        if any(n < 1 for n in self.limits):
            raise ValueError("rate limits must be positive")
        self.events = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def acquire(self, account: str, devices: list[str]):
        keys = [("vendor", self.limits[0]), (f"account:{account}", self.limits[1])]
        keys.extend((f"device:{device}", self.limits[2]) for device in set(devices))
        async with self.lock:
            now = time.monotonic()
            for key, limit in keys:
                queue = self.events[key]
                while queue and queue[0] <= now - 60:
                    queue.popleft()
                if len(queue) >= limit:
                    raise VendorError("local_rate_budget_exhausted")
            for key, _ in keys:
                self.events[key].append(now)
