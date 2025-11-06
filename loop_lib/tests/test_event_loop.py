import pytest
import asyncio
from datetime import datetime
from loop_lib.loop import EventLoopItem, EventLoop


@pytest.mark.asyncio
async def test_register_and_unregister():
    loop = EventLoop()
    called = False

    def test_func():
        nonlocal called
        called = True

    loop.register("job1", test_func, interval=2)
    assert "job1" in loop.functions
    assert isinstance(loop.functions["job1"], EventLoopItem)

    loop.unregister("job1")
    assert "job1" not in loop.functions
    assert "job1" not in loop.tasks


@pytest.mark.asyncio
async def test_run_single_function():
    """Функция выполняется один раз и удаляется при interval=0"""
    counter = 0

    def inc():
        nonlocal counter
        counter += 1

    loop = EventLoop()
    loop.register("job", inc, interval=0)

    task = asyncio.create_task(loop.run())
    await asyncio.sleep(0.5)
    loop.stop()
    await asyncio.sleep(0.1)
    task.cancel()

    assert counter == 1
    assert not "job" in loop.functions



@pytest.mark.asyncio
async def test_run_repeated_function():
    """Функция вызывается несколько раз при interval > 0"""
    counter = 0

    def inc():
        nonlocal counter
        counter += 1

    loop = EventLoop()
    loop.register("repeat", inc, interval=1)

    task = asyncio.create_task(loop.run())
    await asyncio.sleep(2.5)  # должно сработать минимум 2 раза
    loop.stop()
    await asyncio.sleep(0.1)
    task.cancel()

    assert counter >= 2


@pytest.mark.asyncio
async def test_task_cancellation():
    """Активные задачи отменяются при stop()"""
    started = asyncio.Event()
    cancelled = False

    async def long_task():
        nonlocal cancelled
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled = True
            raise

    loop = EventLoop()
    loop.register("long", long_task, interval=5)
    task = asyncio.create_task(loop.run())
    await started.wait()
    loop.stop()
    await asyncio.sleep(0.1)
    task.cancel()

    assert cancelled


@pytest.mark.asyncio
async def test_error_handling(caplog):
    """Ошибка в задаче логируется"""
    def fail_func():
        raise ValueError("test error")

    loop = EventLoop()
    loop.register("fail", fail_func, interval=0)
    task = asyncio.create_task(loop.run())

    await asyncio.sleep(0.5)  # дождаться выполнения функции
    loop.stop()
    await asyncio.sleep(0.1)
    task.cancel()

    assert any("Ошибка выполнения функции fail" in msg for msg in caplog.messages)
