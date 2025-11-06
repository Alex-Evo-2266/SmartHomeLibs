import pytest
import asyncio
from unittest.mock import AsyncMock

from queue_lib.types import QueueItem
from queue_lib.universal_queue import UniversalQueue


# --- Вспомогательные классы ----------------------------------------------------

class MyItem(QueueItem):
    type: str = "my_item"
    data: str


class ErrorItem(QueueItem):
    type: str = "error_item"
    data: str


# --- Тесты --------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_and_add_success(caplog):
    """Проверяем регистрацию и добавление элемента"""
    caplog.set_level("INFO")
    handler = AsyncMock()
    queue = UniversalQueue()
    queue.register("my_item", MyItem, handler)

    queue.add("my_item", data="ok")

    assert len(queue.queue) == 1
    assert isinstance(queue.queue[0], MyItem)
    assert queue.queue[0].data == "ok"
    assert "Registered queue type" in caplog.text


@pytest.mark.asyncio
async def test_start_processes_all_items():
    """Проверяем, что обработчики вызываются и очередь очищается"""
    called = []

    async def handler(item: MyItem):
        called.append(item.data)

    queue = UniversalQueue({"my_item": (MyItem, handler)})
    queue.add("my_item", data="one")
    queue.add("my_item", data="two")

    result = await queue.start()

    assert result is True
    assert called == ["one", "two"]
    assert len(queue.queue) == 0  # все обработано успешно


@pytest.mark.asyncio
async def test_start_with_unknown_type_logs_error(caplog):
    """Проверяем поведение при неизвестном типе"""
    queue = UniversalQueue()
    with pytest.raises(ValueError, match="Unknown queue type"):
        queue.add("unknown", data="test")


@pytest.mark.asyncio
async def test_start_with_handler_error(caplog):
    """Проверяем, что ошибка в обработчике не останавливает очередь полностью"""
    caplog.set_level("INFO")
    processed = []

    async def handler_ok(item: MyItem):
        processed.append(item.data)

    async def handler_fail(item: ErrorItem):
        raise RuntimeError("fail")

    queue = UniversalQueue({
        "my_item": (MyItem, handler_ok),
        "error_item": (ErrorItem, handler_fail),
    })

    queue.add("my_item", data="1")
    queue.add("error_item", data="2", try_start=2)
    queue.add("my_item", data="3")

    result = await queue.start()

    assert result is False  # потому что были ошибки
    assert processed == ["1", "3"]
    assert "Error processing item" in caplog.text
    # ошибканый элемент должен остаться для следующего запуска
    assert len(queue.queue) == 1
    assert queue.queue[0].data == "2"
    assert queue.queue[0].try_start == 1


@pytest.mark.asyncio
async def test_empty_queue(caplog):
    """Проверяем поведение при пустой очереди"""
    caplog.set_level("INFO")
    queue = UniversalQueue()
    result = await queue.start()
    assert result is True
    assert "Queue is empty" in caplog.text


@pytest.mark.asyncio
async def test_partial_processing():
    """Если ошибка в середине — оставшиеся элементы остаются на следующий запуск"""
    processed = []

    async def handler(item: MyItem):
        if item.data == "bad":
            raise ValueError("boom")
        processed.append(item.data)

    queue = UniversalQueue({"my_item": (MyItem, handler)})
    queue.add("my_item", data="good1")
    queue.add("my_item", data="bad", try_start=2)
    queue.add("my_item", data="good2")

    result = await queue.start()

    assert result is False
    assert processed == ["good1", "good2"]
    # "bad" остается для следующего запуска
    assert len(queue.queue) == 1
    assert queue.queue[0].data == "bad"
    assert queue.queue[0].try_start == 1

@pytest.mark.asyncio
async def test_retry_failed_item():
    """Проверяем повторный запуск элемента с ошибкой"""
    processed = []

    async def handler(item: MyItem):
        if item.data == "fail" and item.try_start == 2:
            raise ValueError("boom")
        processed.append(item.data)

    queue = UniversalQueue({"my_item": (MyItem, handler)})
    # Добавляем элемент, который "провалится" один раз
    queue.add("my_item", data="fail", try_start=2)
    queue.add("my_item", data="ok")

    # Первый запуск
    result1 = await queue.start()
    assert result1 is False
    # "fail" остался для повторного запуска, "ok" обработан
    assert processed == ["ok"]
    assert len(queue.queue) == 1
    assert queue.queue[0].data == "fail"
    assert queue.queue[0].try_start == 1

    # Второй запуск (повторный)
    result2 = await queue.start()
    assert result2 is True  # теперь все прошло успешно
    # "fail" должен обработаться
    assert processed == ["ok", "fail"]
    assert len(queue.queue) == 0