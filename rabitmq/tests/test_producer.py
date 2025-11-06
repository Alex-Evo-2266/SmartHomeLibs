import pytest
from unittest.mock import Mock, patch
import json
import pika

from rabitmq.producer import BaseRabbitMQProducer, RabbitMQProducer, RabbitMQProducerFanout

# -------------------------------
# BaseRabbitMQProducer
# -------------------------------
def test_base_producer_connect_and_close():
    log = Mock()
    producer = BaseRabbitMQProducer(host="localhost", port=5672, logger=log)

    with patch("pika.BlockingConnection") as MockConn:
        mock_conn_instance = MockConn.return_value
        mock_conn_instance.is_open = True
        mock_conn_instance.channel.return_value = Mock()

        producer.connect()
        MockConn.assert_called_once()
        assert producer.connection == mock_conn_instance
        assert producer.channel is not None

        producer.close()
        mock_conn_instance.close.assert_called_once()
        log.info.assert_any_call("RabbitMQ connection closed")


# -------------------------------
# RabbitMQProducer
# -------------------------------
def test_rabbitmq_producer_connect_and_publish():
    log = Mock()
    producer = RabbitMQProducer(host="localhost", queue_name="my_queue", logger=log)

    with patch("pika.BlockingConnection") as MockConn, patch("pika.BasicProperties") as MockProps:
        mock_conn_instance = MockConn.return_value
        mock_channel = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_conn_instance.is_closed = False

        # Connect
        producer.connect()
        MockConn.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="my_queue", durable=False)
        log.info.assert_any_call("Queue 'my_queue' declared")

        # Publish
        msg = {"foo": "bar"}
        producer.publish(msg)
        mock_channel.basic_publish.assert_called_once()
        args, kwargs = mock_channel.basic_publish.call_args
        assert kwargs["exchange"] == ''
        assert kwargs["routing_key"] == "my_queue"
        assert json.loads(kwargs["body"]) == msg

        # Проверка properties через мок
        MockProps.assert_called_once_with(delivery_mode=2)
        assert kwargs["properties"] == MockProps.return_value



# -------------------------------
# RabbitMQProducerFanout
# -------------------------------
def test_rabbitmq_producer_fanout_connect_and_publish():
    log = Mock()
    producer = RabbitMQProducerFanout(host="localhost", exchange_name="broadcast", logger=log)

    with patch("pika.BlockingConnection") as MockConn, patch("pika.BasicProperties") as MockProps:
        mock_conn_instance = MockConn.return_value
        mock_channel = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_conn_instance.is_closed = False

        # Connect
        producer.connect()
        mock_channel.exchange_declare.assert_called_once_with(exchange="broadcast", exchange_type="fanout")
        log.info.assert_any_call("Fanout exchange 'broadcast' declared")

        # Publish
        msg = {"hello": "world"}
        producer.publish(msg)
        mock_channel.basic_publish.assert_called_once()
        args, kwargs = mock_channel.basic_publish.call_args

        # Проверяем аргументы публикации
        assert kwargs["exchange"] == 'broadcast'
        assert kwargs["routing_key"] == ''
        assert json.loads(kwargs["body"]) == msg

        # Проверка, что BasicProperties был вызван и передан
        MockProps.assert_called_once_with(delivery_mode=2)
        assert kwargs["properties"] == MockProps.return_value