"""
config.py
Configuration cho NLP Service
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Load .env file nếu có
try:
    from dotenv import load_dotenv
    
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
except ImportError:
    pass


@dataclass
class Config:
    """NLP Service Configuration"""
    
    # RabbitMQ Settings - Input Queue (from crawl-service)
    QUEUE_HOST: str = os.getenv("QUEUE_HOST", "localhost")
    QUEUE_PORT: int = int(os.getenv("QUEUE_PORT", "5672"))
    INPUT_QUEUE: str = os.getenv("INPUT_QUEUE", "tiktok_comments")
    OUTPUT_QUEUE: str = os.getenv("OUTPUT_QUEUE", "processed_comments")
    
    # RabbitMQ Authentication
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "admin123")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # NLP Settings
    MIN_COMMENT_LENGTH: int = int(os.getenv("MIN_COMMENT_LENGTH", "2"))
    MAX_COMMENT_LENGTH: int = int(os.getenv("MAX_COMMENT_LENGTH", "500"))
    
    # Logging
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def get_rabbitmq_url(self) -> str:
        """Get RabbitMQ connection URL"""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.QUEUE_HOST}:{self.QUEUE_PORT}{self.RABBITMQ_VHOST}"
        )
