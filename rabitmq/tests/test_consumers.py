import pytest
import json
import pika
from unittest.mock import MagicMock, patch, Mock
from rabitmq.consumer import BaseRabbitMQConsumer, QueueConsumer, FanoutConsumer 
# ===============================
# BaseRabbitMQConsumer
# ===============================
class TestBaseRabbitMQConsumer:

    def test_base_consumer_stop_closes_connection(self):
        consumer = BaseRabbitMQConsumer()
        mock_conn = MagicMock()
        mock_conn.is_open = True
        consumer.connection = mock_conn

        consumer.stop()

        mock_conn.close.assert_called_once()
        assert consumer._is_interrupted is True


    def test_base_consumer_connect_creates_connection(self):
        with patch("pika.BlockingConnection") as MockConn:
            mock_conn = MagicMock()
            mock_channel = MagicMock()
            mock_conn.channel.return_value = mock_channel
            MockConn.return_value = mock_conn

            consumer = BaseRabbitMQConsumer(host="127.0.0.1", port=5672)
            consumer._connect()

            MockConn.assert_called_once()
            assert consumer.channel == mock_channel


    def test_base_consumer_run_not_implemented(self):
        consumer = BaseRabbitMQConsumer()
        with pytest.raises(NotImplementedError):
            consumer.run()


# ===============================
# QueueConsumer
# ===============================

class TestQueueConsumer:
    @patch("pika.BlockingConnection")
    def test_queue_consumer_consumes_messages(self, MockConn):
        mock_channel = MagicMock()
        mock_conn = MagicMock()
        mock_conn.channel.return_value = mock_channel
        MockConn.return_value = mock_conn

        mock_callback = MagicMock()
        consumer = QueueConsumer(queue="test_q", callback=mock_callback)

        # подготавливаем одно сообщение
        message = (MagicMock(), MagicMock(), json.dumps({"a": 1}).encode())
        mock_channel.consume.side_effect = [
            [message, (None, None, None)],
        ]

        consumer._connect = MagicMock()
        consumer._connect.side_effect = lambda: setattr(consumer, "channel", mock_channel)

        # чтобы цикл не завис
        def stop_after_first(*args, **kwargs):
            consumer._is_interrupted = True
        mock_callback.side_effect = stop_after_first

        consumer.run()
        mock_callback.assert_called_once()

    def test_queue_consumer_handles_invalid_json(self):
        consumer = QueueConsumer(queue="test_queue", logger=Mock())

        # Мокаем методы, чтобы не подключаться к RabbitMQ
        consumer._connect = Mock()
        consumer.connection = Mock()
        consumer.channel = Mock()

        # Подделываем поведение consume
        consumer.channel.consume.return_value = [
            (Mock(), Mock(), b"{invalid json"),  # некорректный JSON
            (None, None, None),                  # inactivity_timeout
        ]

        consumer._is_interrupted = False

        # Запускаем поток и ждём короткое время
        def stop_soon():
            import time
            time.sleep(0.1)
            consumer.stop()

        import threading
        threading.Thread(target=stop_soon).start()

        consumer.run()

        consumer.logger.exception.assert_any_call("Invalid JSON in message")


# ===============================
# FanoutConsumer
# ===============================

class TestFanoutConsumer:
    def test_fanout_consumer_message_processing(self):
        mock_logger = Mock()
        mock_callback = Mock()

        consumer = FanoutConsumer(exchange="test_ex", callback=mock_callback, logger=mock_logger)
        consumer._connect = Mock()
        consumer.connection = Mock()
        consumer.channel = Mock()
        consumer.channel.queue_declare.return_value.method.queue = "temp_queue"
        consumer.channel.queue_bind = Mock()

        captured = {}

        def basic_consume(queue, on_message_callback, auto_ack):
            captured["cb"] = on_message_callback

        consumer.channel.basic_consume = basic_consume

        def fake_start_consuming():
            body = json.dumps({"msg": "hi"}).encode()
            captured["cb"](consumer.channel, Mock(), Mock(), body)
            consumer._is_interrupted = True  # остановим цикл после первого вызова

        consumer.channel.start_consuming = fake_start_consuming

        consumer.run()

        mock_callback.assert_called_once()


    def test_fanout_consumer_error_handling(self):
        mock_logger = Mock()
        mock_callback = Mock(side_effect=ValueError("oops"))

        consumer = FanoutConsumer(exchange="err_ex", callback=mock_callback, logger=mock_logger)
        consumer._connect = Mock()
        consumer.connection = Mock()
        consumer.channel = Mock()
        consumer.channel.queue_declare.return_value.method.queue = "tmp_queue"
        consumer.channel.queue_bind = Mock()

        captured = {}

        def basic_consume(queue, on_message_callback, auto_ack):
            captured["cb"] = on_message_callback

        consumer.channel.basic_consume = basic_consume

        def fake_start_consuming():
            body = json.dumps({"bad": "data"}).encode()
            captured["cb"](consumer.channel, Mock(), Mock(), body)
            consumer._is_interrupted = True

        consumer.channel.start_consuming = fake_start_consuming

        consumer.run()

        mock_logger.exception.assert_any_call("Error processing fanout message")
