"""
listener.py
TikTok Live Comment Crawler
Nhiệm vụ: Lắng nghe comment từ TikTok Live và đẩy vào queue
"""

import ssl
import asyncio
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
import json
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    DisconnectEvent,
)

from config import Config
from message_queue import MessageQueue


@dataclass
class Comment:
    """Cấu trúc dữ liệu comment"""
    username: str
    nickname: str
    content: str
    timestamp: float

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
        # Configure SSL for TikTok connections
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        except Exception as e:
            self._log(f"SSL setup warning: {e}", level="DEBUG")
        
        self.config = config
        self.username = config.TIKTOK_USERNAME
        
        # Initialize TikTok client with custom settings
        try:
            self.client = TikTokLiveClient(unique_id=self.username)
            self._log(f"✓ TikTok client initialized for @{self.username}", level="DEBUG")
        except Exception as e:
            self._log(f"TikTok client init error: {e}", level="ERROR")
            raise
            
        self.queue = MessageQueue(config)
        
        self.is_connected = False
        self.comment_count = 0
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup event handlers"""
        
        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            """Khi kết nối thành công"""
            self.is_connected = True
            self._log(f"✅ Connected to @{self.username}")
            # Viewer count có thể không có trong một số phiên bản TikTokLive
            try:
                viewer_count = getattr(event, 'viewer_count', None) or getattr(event, 'viewerCount', None)
                if viewer_count is not None:
                    self._log(f"👥 Viewers: {viewer_count}")
            except Exception:
                pass
        
        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            """Khi ngắt kết nối"""
            self.is_connected = False
            self._log("⚠️ Disconnected")
        
        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            """
            Khi có comment mới
            Đẩy vào queue để AI xử lý
            """
            self.comment_count += 1
            
            # Lấy user info trực tiếp từ event.user_info để tránh lỗi ExtendedUser
            try:
                user_info = event.user_info
                username = user_info.username if hasattr(user_info, 'username') else "unknown"
                nickname = user_info.nick_name if hasattr(user_info, 'nickname') else username
                profile_picture = self._get_avatar_url_safe(user_info)
            except Exception:
                user_id = "unknown"
                username = "unknown"
                nickname = "unknown"
                profile_picture = None
            
            # Tạo comment object
            comment = Comment(
                username=username,
                nickname=nickname,
                content=event.comment,
                timestamp=datetime.now().timestamp()
            )
            
            # Log
            self._log(f"💬 {comment.nickname}: {comment.content}")
            
            # Đẩy vào queue
            try:
                await self.queue.publish(comment)
                self._log(f"  ✓ Pushed to queue (#{self.comment_count})", level="DEBUG")
            except Exception as e:
                self._log(f"  ✗ Queue error: {e}", level="ERROR")
    
    def _get_avatar_url_safe(self, user_info) -> Optional[str]:
        """Lấy URL avatar của user (safe version)"""
        try:
            if hasattr(user_info, 'avatar_thumb') and user_info.avatar_thumb:
                if hasattr(user_info.avatar_thumb, 'url_list') and user_info.avatar_thumb.url_list:
                    return user_info.avatar_thumb.url_list[0]
        except:
            pass
        return None
    
    def _get_avatar_url(self, event: CommentEvent) -> Optional[str]:
        """Lấy URL avatar của user"""
        try:
            if event.user.profile_picture:
                return event.user.profile_picture.avatar_thumb.url_list[0]
        except:
            pass
        return None
    
    async def start(self, retry_on_disconnect: bool = True, retry_interval: int = 30):
        """
        Bắt đầu crawl với auto-reconnect
        
        Args:
            retry_on_disconnect: Tự động reconnect khi bị ngắt
            retry_interval: Thời gian chờ giữa các lần retry (giây)
        """
        # Connect đến queue một lần
        try:
            await self.queue.connect()
            self._log("✓ Queue connected", level="DEBUG")
        except Exception as queue_error:
            self._log(f"⚠️ Queue connection failed: {queue_error}", level="ERROR")
            self._log("Continuing without queue (comments won't be saved)...", level="DEBUG")
        
        while True:
            try:
                self._log(f"🔄 Connecting to @{self.username}...")
                self._log(f"📡 Checking TikTok user @{self.username}...", level="DEBUG")
                
                # Reinitialize client for each connection attempt
                self.client = TikTokLiveClient(unique_id=self.username)
                self._setup_handlers()
                
                # Connect đến TikTok Live
                self._log("📺 Connecting to TikTok Live...", level="DEBUG")
                await self.client.start()
                
                # Nếu start() return (không còn live), chờ và retry
                if retry_on_disconnect:
                    self._log(f"📴 Stream ended. Waiting {retry_interval}s before retry...", level="INFO")
                    await asyncio.sleep(retry_interval)
                else:
                    break
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                if "certificate verify failed" in error_msg:
                    self._log("❌ SSL Certificate Error - TikTok connection blocked", level="ERROR")
                    self._log("💡 Try: pip install --upgrade certifi", level="INFO")
                    if not retry_on_disconnect:
                        break
                        
                elif "user not found" in error_msg or "user_not_found" in error_msg:
                    self._log(f"❌ TikTok user @{self.username} not found", level="ERROR")
                    break  # Không retry nếu user không tồn tại
                    
                elif "not live" in error_msg or "offline" in error_msg or "not hosting" in error_msg:
                    self._log(f"⏳ User @{self.username} is not live. Waiting {retry_interval}s...", level="INFO")
                    if retry_on_disconnect:
                        await asyncio.sleep(retry_interval)
                    else:
                        break
                else:
                    self._log(f"❌ Connection Error: {e}", level="ERROR")
                    if retry_on_disconnect:
                        self._log(f"🔄 Retrying in {retry_interval}s...", level="INFO")
                        await asyncio.sleep(retry_interval)
                    else:
                        break
                
                self.is_connected = False
        
        # Cleanup
        try:
            await self.queue.disconnect()
        except:
            pass
    
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