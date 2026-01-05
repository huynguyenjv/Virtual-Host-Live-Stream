"""
queue.py
RabbitMQ Message Queue Handler
"""

import json
import aio_pika
from typing import Optional


class MessageQueue:
    """
    RabbitMQ Message Queue
    Đẩy comments vào queue để AI xử lý
    """
    
    def __init__(self, config):
        self.config = config
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
    
    async def connect(self):
        """Connect to RabbitMQ"""
        url = self.config.get_rabbitmq_url()
        
        # Connect with robust connection (auto-reconnect)
        self.connection = await aio_pika.connect_robust(url)
        
        # Create channel
        self.channel = await self.connection.channel()
        
        # Declare queue (durable = persistent)
        self.queue = await self.channel.declare_queue(
            self.config.QUEUE_NAME,
            durable=True
        )
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
    
    async def publish(self, comment):
        """
        Publish comment to queue
        
        Args:
            comment: Comment object with to_dict() method
        """
        if not self.channel:
            raise ConnectionError("Not connected to RabbitMQ")
        
        # Convert to dict then JSON
        message_dict = comment.to_dict()
        message_json = json.dumps(message_dict, ensure_ascii=False)
        
        # Create message with persistent delivery
        message = aio_pika.Message(
            body=message_json.encode('utf-8'),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        # Publish to default exchange with routing key = queue name
        await self.channel.default_exchange.publish(
            message,
            routing_key=self.config.QUEUE_NAME
        )