"""
config.py
Configuration cho Avatar Service (2D Vtuber)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


@dataclass
class Config:
    """Avatar Service Configuration"""
    
    # RabbitMQ Settings
    QUEUE_HOST: str = os.getenv("QUEUE_HOST", "localhost")
    QUEUE_PORT: int = int(os.getenv("QUEUE_PORT", "5672"))
    INPUT_QUEUE: str = os.getenv("INPUT_QUEUE", "tts_audio")
    OUTPUT_QUEUE: str = os.getenv("OUTPUT_QUEUE", "avatar_video")
    
    # Avatar Mode: "2d" (Vtuber) or "3d" (Talking Head)
    AVATAR_MODE: str = os.getenv("AVATAR_MODE", "2d")
    
    # 3D Talking Head Settings
    TALKING_HEAD_ENGINE: str = os.getenv("TALKING_HEAD_ENGINE", "sadtalker")  # sadtalker, wav2lip, liveportrait, did
    SOURCE_FACE_IMAGE: str = os.getenv("SOURCE_FACE_IMAGE", "./models/face.png")
    SADTALKER_PATH: str = os.getenv("SADTALKER_PATH", "./engines/SadTalker")
    WAV2LIP_PATH: str = os.getenv("WAV2LIP_PATH", "./engines/Wav2Lip")
    DID_API_KEY: str = os.getenv("DID_API_KEY", "")
    
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "admin123")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # Avatar Settings
    AVATAR_MODEL_PATH: str = os.getenv("AVATAR_MODEL_PATH", "./models/avatar")
    AVATAR_WIDTH: int = int(os.getenv("AVATAR_WIDTH", "512"))
    AVATAR_HEIGHT: int = int(os.getenv("AVATAR_HEIGHT", "512"))
    AVATAR_FPS: int = int(os.getenv("AVATAR_FPS", "30"))
    
    # Sprite Sheet Settings (2D Vtuber)
    SPRITE_IDLE: str = os.getenv("SPRITE_IDLE", "idle.png")
    SPRITE_TALK: str = os.getenv("SPRITE_TALK", "talk.png")
    SPRITE_BLINK: str = os.getenv("SPRITE_BLINK", "blink.png")
    
    # Animation Settings
    BLINK_INTERVAL: float = float(os.getenv("BLINK_INTERVAL", "3.0"))  # seconds
    BLINK_DURATION: float = float(os.getenv("BLINK_DURATION", "0.15"))  # seconds
    MOUTH_SMOOTHING: float = float(os.getenv("MOUTH_SMOOTHING", "0.3"))
    IDLE_SWAY_AMOUNT: float = float(os.getenv("IDLE_SWAY_AMOUNT", "2.0"))  # pixels
    IDLE_SWAY_SPEED: float = float(os.getenv("IDLE_SWAY_SPEED", "1.5"))  # Hz
    
    # Lip Sync Settings
    LIPSYNC_THRESHOLD: float = float(os.getenv("LIPSYNC_THRESHOLD", "0.02"))
    LIPSYNC_SENSITIVITY: float = float(os.getenv("LIPSYNC_SENSITIVITY", "1.5"))
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "22050"))
    
    # Expression Mapping (intent -> expression)
    EXPRESSION_MAP: Dict[str, str] = field(default_factory=lambda: {
        "greeting": "happy",
        "question": "thinking",
        "thanks": "happy",
        "complaint": "sad",
        "request": "neutral",
        "chitchat": "happy",
        "unknown": "neutral"
    })
    
    # Output Settings
    OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "webm")  # webm, mp4, gif
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")
    ENABLE_TRANSPARENCY: bool = os.getenv("ENABLE_TRANSPARENCY", "true").lower() == "true"
    
    # WebSocket for real-time streaming (optional)
    WEBSOCKET_ENABLED: bool = os.getenv("WEBSOCKET_ENABLED", "false").lower() == "true"
    WEBSOCKET_HOST: str = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
    WEBSOCKET_PORT: int = int(os.getenv("WEBSOCKET_PORT", "8765"))
    
    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def get_rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.QUEUE_HOST}:{self.QUEUE_PORT}{self.RABBITMQ_VHOST}"
        )
    
    def get_model_path(self) -> Path:
        return Path(self.AVATAR_MODEL_PATH)
    
    def get_output_path(self) -> Path:
        path = Path(self.OUTPUT_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path
