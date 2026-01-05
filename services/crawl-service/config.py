"""
config.py
Configuration cho Crawler Service
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Load .env file nếu có
try:
    from dotenv import load_dotenv
    
    # Tìm file .env
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Thử tìm ở thư mục cha
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
except ImportError:
    # python-dotenv chưa cài, skip
    pass


@dataclass
class Config:
    """Crawler Service Configuration"""
    
    # TikTok Settings
    TIKTOK_USERNAME: str = os.getenv("TIKTOK_USERNAME", "username")
    
    # Queue Settings - RabbitMQ only
    QUEUE_HOST: str = os.getenv("QUEUE_HOST", "localhost")
    QUEUE_PORT: int = int(os.getenv("QUEUE_PORT", "5672"))
    QUEUE_NAME: str = os.getenv("QUEUE_NAME", "tiktok_comments")
    
    # RabbitMQ Authentication
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # Logging
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.TIKTOK_USERNAME or self.TIKTOK_USERNAME == "username":
            raise ValueError("TIKTOK_USERNAME must be set in environment or .env file")
    
    def get_rabbitmq_url(self) -> str:
        """Get RabbitMQ connection URL"""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.QUEUE_HOST}:{self.QUEUE_PORT}{self.RABBITMQ_VHOST}"
        )