"""
message_queue.py
RabbitMQ Consumer & Publisher cho NLP Service
"""

import json
import asyncio
import aio_pika
from typing import Optional, Callable, Any
from datetime import datetime


class MessageQueueConsumer:
    """
    RabbitMQ Consumer
    Nhận comments từ crawl-service
    """
    
    def __init__(self, config):
        self.config = config
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self._callback: Optional[Callable] = None
    
    async def connect(self):
        """Connect to RabbitMQ"""
        url = self.config.get_rabbitmq_url()
        
        self.connection = await aio_pika.connect_robust(url)
        self.channel = await self.connection.channel()
        
        # Set QoS - xử lý 1 message tại 1 thời điểm
        await self.channel.set_qos(prefetch_count=1)
        
        # Declare input queue
        self.queue = await self.channel.declare_queue(
            self.config.INPUT_QUEUE,
            durable=True
        )
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
    
    async def consume(self, callback: Callable[[dict], Any]):
        """
        Start consuming messages
        
        Args:
            callback: Async function to process each message
        """
        self._callback = callback
        
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    # Decode message
                    body = message.body.decode('utf-8')
                    data = json.loads(body)
                    
                    # Call callback
                    await callback(data)
                    
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Invalid JSON: {e}")
                except Exception as e:
                    print(f"[ERROR] Processing error: {e}")
        
        # Start consuming
        await self.queue.consume(process_message)


class MessageQueuePublisher:
    """
    RabbitMQ Publisher
    Đẩy processed comments sang chat-service
    """
    
    def __init__(self, config):
        self.config = config
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
    
    async def connect(self):
        """Connect to RabbitMQ"""
        url = self.config.get_rabbitmq_url()
        
        self.connection = await aio_pika.connect_robust(url)
        self.channel = await self.connection.channel()
        
        # Declare output queue
        await self.channel.declare_queue(
            self.config.OUTPUT_QUEUE,
            durable=True
        )
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
    
    async def publish(self, data: dict):
        """
        Publish processed comment to output queue
        
        Args:
            data: Processed comment data
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
