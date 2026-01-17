import asyncio
from typing import Any, Dict, List


class EventBroadcaster:
    def __init__(self, queue_size: int = 100) -> None:
        self._queue_size = max(10, queue_size)
        self._queues: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._queues.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            if queue in self._queues:
                self._queues.remove(queue)

    async def publish(self, event: Dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._queues)
        for queue in queues:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await queue.put(event)
