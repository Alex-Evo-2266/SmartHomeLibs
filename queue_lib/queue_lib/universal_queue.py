# universal_queue.py
from typing import List, Dict, Type, Callable, Awaitable, Optional, Any
import asyncio, logging
from contextlib import suppress
from .types import QueueItem

class UniversalQueue:
    def __init__(self, registrations=None, logger: Any | None = None):
        self.queue: List[QueueItem] = []
        self.pending: List[QueueItem] = []  # буфер для новых элементов
        self.handlers: Dict[str, Callable[[QueueItem], Awaitable[None]]] = {}
        self.schemas: Dict[str, Type[QueueItem]] = {}
        self.logger = logger or logging.getLogger(__name__)
        self._lock = asyncio.Lock()  # защита от одновременного add + start

        if registrations:
            for type_name, (schema, handler) in registrations.items():
                self.register(type_name, schema, handler)

    def register(self, type_name: str, schema: Type[QueueItem], handler: Callable[[QueueItem], Awaitable[None]]):
        self.schemas[type_name] = schema
        self.handlers[type_name] = handler
        self.logger.info(f"[Queue] Registered queue type '{type_name}' with model {schema.__name__}")

    def add(self, type_name: str, **kwargs) -> None:
        try:
            self.logger.debug(f"[Queue] Adding item. Type: {type_name}, Data: {kwargs}")
            schema = self.schemas.get(type_name)
            if not schema:
                raise ValueError(f"Unknown queue type: {type_name}")
            item = schema(**kwargs)
            self.pending.append(item)  # добавляем в буфер
            self.logger.info(f"[Queue] Item added to pending: {item}")
        except Exception as e:
            self.logger.error(f"[Queue] Failed to add item: {e}", exc_info=True)
            raise

    async def start(self) -> bool:
        async with self._lock:
            # переносим pending в queue
            self.queue.extend(self.pending)
            self.pending.clear()

            self.logger.debug(f"[Queue] Starting. Items: {self.queue} {self.pending}")
            self.logger.info(f"[Queue] Starting. Items: {len(self.queue)}")
            if not self.queue:
                self.logger.info("[Queue] Queue is empty.")
                return True

            success = True
            restart: List[QueueItem] = []

            for idx, item in enumerate(list(self.queue)):
                try:
                    self.logger.debug(f"[Queue] Processing item {idx + 1}: {item}")
                    handler = self.handlers.get(item.type)
                    if not handler:
                        raise ValueError(f"No handler registered for type: {item.type}")
                    await handler(item)
                except asyncio.CancelledError:
                    self.logger.warning("[Queue] Processing cancelled.")
                    success = False
                    raise
                except Exception as e:
                    self.logger.error(f"[Queue] Error processing item {idx + 1}: {e}", exc_info=True)
                    success = False
                    if item.try_start > 1:
                        item.try_start -= 1
                        restart.append(item)
                    continue

            # сохраняем необработанные элементы и добавляем новые из pending
            self.logger.debug(f"[Queue] end iter: {self.queue} {self.pending} {restart}")

            self.queue = restart + self.pending
            self.pending.clear()
            self.logger.debug(f"[Queue] end clear : {self.queue} {self.pending} {restart}")

            if not self.queue:
                self.logger.info("[Queue] Cleared successfully.")

            self.logger.info(f"[Queue] Finished. Success: {success}. Remaining items: {len(self.queue)}")
            return success
