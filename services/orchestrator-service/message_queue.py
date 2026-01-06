"""
message_queue.py
RabbitMQ Consumer & Publisher cho Orchestrator Service
"""

import json
import aio_pika
from typing import Optional, Callable, Any


class MessageQueueConsumer:
    """RabbitMQ Consumer - Nhận từ NLP service"""
    
    def __init__(self, config):
        self.config = config
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
    
    async def connect(self):
        """Kết nối tới RabbitMQ"""
        url = self.config.get_rabbitmq_url()
        self.connection = await aio_pika.connect_robust(url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)
        self.queue = await self.channel.declare_queue(
            self.config.INPUT_QUEUE,
            durable=True
        )
        print(f"[INFO] Connected to queue: {self.config.INPUT_QUEUE}")
    
    async def disconnect(self):
        """Ngắt kết nối"""
        if self.connection:
            await self.connection.close()
            print("[INFO] Disconnected from RabbitMQ")
    
    async def consume(self, callback: Callable[[dict], Any]):
        """
        Consume messages từ queue
        
        Args:
            callback: Async function xử lý message
        """
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    body = message.body.decode('utf-8')
                    data = json.loads(body)
                    await callback(data)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON decode error: {e}")
                except Exception as e:
                    print(f"[ERROR] Processing error: {e}")
        
        await self.queue.consume(process_message)
        print(f"[INFO] Started consuming from {self.config.INPUT_QUEUE}")


class MessageQueuePublisher:
    """RabbitMQ Publisher - Đẩy sang Chat service"""
    
    def __init__(self, config):
        self.config = config
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
    
    async def connect(self):
        """Kết nối tới RabbitMQ"""
        url = self.config.get_rabbitmq_url()
        self.connection = await aio_pika.connect_robust(url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(
            self.config.OUTPUT_QUEUE,
            durable=True
        )
        print(f"[INFO] Publisher ready for queue: {self.config.OUTPUT_QUEUE}")
    
    async def disconnect(self):
        """Ngắt kết nối"""
        if self.connection:
            await self.connection.close()
    
    async def publish(self, data: dict):
        """
        Publish message tới queue
        
        Args:
            data: Dictionary chứa thông tin cần xử lý
        """
        if not self.channel:
            raise ConnectionError("Not connected to RabbitMQ")
        
        message_json = json.dumps(data, ensure_ascii=False)
        message = aio_pika.Message(
            body=message_json.encode('utf-8'),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        await self.channel.default_exchange.publish(
            message,
            routing_key=self.config.OUTPUT_QUEUE
        )
