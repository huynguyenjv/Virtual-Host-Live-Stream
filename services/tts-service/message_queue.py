"""
message_queue.py
RabbitMQ Consumer & Publisher cho TTS Service
"""

import json
import aio_pika
from typing import Optional, Callable, Any


class MessageQueueConsumer:
    """RabbitMQ Consumer - Nhận từ chat-service"""
    
    def __init__(self, config):
        self.config = config
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
    
    async def connect(self):
        url = self.config.get_rabbitmq_url()
        self.connection = await aio_pika.connect_robust(url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)
        self.queue = await self.channel.declare_queue(
            self.config.INPUT_QUEUE,
            durable=True
        )
    
    async def disconnect(self):
        if self.connection:
            await self.connection.close()
    
    async def consume(self, callback: Callable[[dict], Any]):
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    body = message.body.decode('utf-8')
                    data = json.loads(body)
                    await callback(data)
                except Exception as e:
                    print(f"[ERROR] Processing error: {e}")
        
        await self.queue.consume(process_message)


class MessageQueuePublisher:
    """RabbitMQ Publisher - Đẩy sang avatar-service"""
    
    def __init__(self, config):
        self.config = config
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
    
    async def connect(self):
        url = self.config.get_rabbitmq_url()
        self.connection = await aio_pika.connect_robust(url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(
            self.config.OUTPUT_QUEUE,
            durable=True
        )
    
    async def disconnect(self):
        if self.connection:
            await self.connection.close()
    
    async def publish(self, data: dict):
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
