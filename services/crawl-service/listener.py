"""
listener.py
TikTok Live Comment Crawler
Nhiệm vụ: Lắng nghe comment từ TikTok Live và đẩy vào queue
"""

import asyncio
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
import json

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    DisconnectEvent,
)

from config import Config
from queue import MessageQueue


@dataclass
class Comment:
    """Cấu trúc dữ liệu comment"""
    user_id: str
    username: str
    nickname: str
    content: str
    timestamp: float
    profile_picture: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class TikTokLiveCrawler:
    """
    TikTok Live Crawler Service
    Crawl comments và đẩy vào queue để AI xử lý
    """
    
    def __init__(self, config: Config):
        """
        Khởi tạo crawler
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.username = config.TIKTOK_USERNAME
        self.client = TikTokLiveClient(unique_id=self.username)
        self.queue = MessageQueue(config)
        
        self.is_connected = False
        self.comment_count = 0
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup event handlers"""
        
        @self.client.on("connect")
        async def on_connect(event: ConnectEvent):
            """Khi kết nối thành công"""
            self.is_connected = True
            self._log(f"✅ Connected to @{self.username}")
            self._log(f"👥 Viewers: {event.viewer_count}")
        
        @self.client.on("disconnect")
        async def on_disconnect(event: DisconnectEvent):
            """Khi ngắt kết nối"""
            self.is_connected = False
            self._log("⚠️ Disconnected")
        
        @self.client.on("comment")
        async def on_comment(event: CommentEvent):
            """
            Khi có comment mới
            Đẩy vào queue để AI xử lý
            """
            self.comment_count += 1
            
            # Tạo comment object
            comment = Comment(
                user_id=str(event.user.user_id),
                username=event.user.unique_id,
                nickname=event.user.nickname,
                content=event.comment,
                timestamp=datetime.now().timestamp(),
                profile_picture=self._get_avatar_url(event)
            )
            
            # Log
            self._log(f"💬 {comment.nickname}: {comment.content}")
            
            # Đẩy vào queue
            try:
                await self.queue.publish(comment)
                self._log(f"  ✓ Pushed to queue (#{self.comment_count})", level="DEBUG")
            except Exception as e:
                self._log(f"  ✗ Queue error: {e}", level="ERROR")
    
    def _get_avatar_url(self, event: CommentEvent) -> Optional[str]:
        """Lấy URL avatar của user"""
        try:
            if event.user.profile_picture:
                return event.user.profile_picture.avatar_thumb.url_list[0]
        except:
            pass
        return None
    
    async def start(self):
        """
        Bắt đầu crawl
        (Async - chạy cho đến khi disconnect)
        """
        try:
            self._log(f"🔄 Connecting to @{self.username}...")
            
            # Connect đến queue
            await self.queue.connect()
            
            # Connect đến TikTok Live
            await self.client.start()
            
        except Exception as e:
            self._log(f"❌ Error: {e}", level="ERROR")
            self.is_connected = False
        finally:
            # Cleanup
            await self.queue.disconnect()
    
    def run(self):
        """
        Run crawler (blocking)
        Wrapper cho asyncio.run()
        """
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            self._log("\n⏹️ Stopping crawler...")
    
    def _log(self, message: str, level: str = "INFO"):
        """
        Log message với timestamp
        
        Args:
            message: Message to log
            level: Log level (INFO, DEBUG, ERROR)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "DEBUG" and not self.config.DEBUG:
            return
        
        prefix = {
            "INFO": "",
            "DEBUG": "[DEBUG] ",
            "ERROR": "[ERROR] "
        }.get(level, "")
        
        print(f"[{timestamp}] {prefix}{message}")


def main():
    """Main function"""
    from config import Config
    
    config = Config()
    crawler = TikTokLiveCrawler(config)
    
    print("=" * 60)
    print("  TIKTOK LIVE CRAWLER SERVICE")
    print("=" * 60)
    print(f"  Target: @{config.TIKTOK_USERNAME}")
    print(f"  Queue: {config.QUEUE_TYPE}")
    print("=" * 60)
    print("\n⚠️  Press Ctrl+C to stop\n")
    
    crawler.run()


if __name__ == "__main__":
    main()