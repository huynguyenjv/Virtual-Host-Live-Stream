"""
config.py
Configuration cho Crawler Service
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Crawler Service Configuration"""
    
    # TikTok Settings
    TIKTOK_USERNAME: str = os.getenv("TIKTOK_USERNAME", "username")
    
    # Queue Settings
    QUEUE_TYPE: str = os.getenv("QUEUE_TYPE", "redis")  # redis, rabbitmq, memory
    QUEUE_HOST: str = os.getenv("QUEUE_HOST", "localhost")
    QUEUE_PORT: int = int(os.getenv("QUEUE_PORT", "6379"))
    QUEUE_NAME: str = os.getenv("QUEUE_NAME", "tiktok_comments")
    
    # Redis specific
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # RabbitMQ specific
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # Logging
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.TIKTOK_USERNAME or self.TIKTOK_USERNAME == "username":
            raise ValueError("TIKTOK_USERNAME must be set in environment or .env file")
        
        if self.QUEUE_TYPE not in ["redis", "rabbitmq", "memory"]:
            raise ValueError(f"Invalid QUEUE_TYPE: {self.QUEUE_TYPE}")