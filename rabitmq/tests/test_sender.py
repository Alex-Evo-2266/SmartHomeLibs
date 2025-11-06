import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from rabitmq.sender import BaseSender, QueueSender, FanoutSender

@pytest.mark.asyncio
async def test_base_sender_send_with_data_provider():
    log = Mock()
    data_provider = AsyncMock(return_value="test_data")
    publisher = Mock()
    
    class TestSender(BaseSender):
        def create_publisher(self, *args, **kwargs):
            return publisher

    sender = TestSender(logger=log, data_provider=data_provider)
    sender.connect()
    
    await sender.send()
    
    data_provider.assert_awaited_once()
    publisher.publish.assert_called_once_with("test_data")
    log.info.assert_any_call(f"send {sender.__class__.__name__}")

@pytest.mark.asyncio
async def test_base_sender_send_with_direct_data():
    log = Mock()
    publisher = Mock()
    
    class TestSender(BaseSender):
        def create_publisher(self, *args, **kwargs):
            return publisher

    sender = TestSender(logger=log)
    sender.connect()
    
    await sender.send(data="direct_data")
    
    publisher.publish.assert_called_once_with("direct_data")

@pytest.mark.asyncio
async def test_base_sender_send_without_data_raises():
    log = Mock()
    
    class TestSender(BaseSender):
        def create_publisher(self, *args, **kwargs):
            return Mock()

    sender = TestSender(logger=log)
    sender.connect()
    
    with pytest.raises(ValueError, match="No data_provider and no 'data' in kwargs"):
        await sender.send()

def test_base_sender_connect_and_disconnect():
    log = Mock()
    publisher = Mock()
    
    class TestSender(BaseSender):
        def create_publisher(self, *args, **kwargs):
            return publisher

    sender = TestSender(logger=log)
    sender.connect()
    publisher.connect.assert_called_once()
    
    sender.disconnect()
    publisher.close.assert_called_once()

def test_queue_sender_create_publisher():
    log = Mock()
    with patch("rabitmq.sender.RabbitMQProducer") as MockProducer:
        sender = QueueSender(logger=log)
        pub = sender.create_publisher(queue_name="q1", host="localhost")
        MockProducer.assert_called_once_with(host="localhost", queue_name="q1")
        assert pub == MockProducer.return_value

def test_fanout_sender_create_publisher():
    log = Mock()
    with patch("rabitmq.sender.RabbitMQProducerFanout") as MockProducer:
        sender = FanoutSender(logger=log)
        pub = sender.create_publisher(exchange_name="ex1", host="localhost")
        MockProducer.assert_called_once_with(host="localhost", exchange_name="ex1")
        assert pub == MockProducer.return_value
