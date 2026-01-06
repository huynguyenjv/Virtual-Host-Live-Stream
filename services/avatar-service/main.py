"""
main.py
Avatar Service Entry Point (2D Vtuber)
Nhận audio từ TTS → Render Avatar với Lip Sync → Đẩy sang OBS
"""

import sys
import asyncio
import argparse
import signal
from datetime import datetime
from pathlib import Path

from config import Config
from message_queue import MessageQueueConsumer, MessageQueuePublisher
from lipsync import LipSyncAnalyzer
from renderer import VtuberRenderer, Expression, WebSocketStreamer


class AvatarService:
    """
    Avatar Service - 2D Vtuber
    Pipeline: TTS Audio → Lip Sync Analysis → Render → OBS
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        self.lipsync_analyzer = LipSyncAnalyzer(config)
        self.renderer = VtuberRenderer(config)
        self.ws_streamer = WebSocketStreamer(config, self.renderer) if config.WEBSOCKET_ENABLED else None
        
        # Message queues
        self.consumer = MessageQueueConsumer(config)
        self.publisher = MessageQueuePublisher(config)
        
        # Stats
        self.processed_count = 0
        self.success_count = 0
        self.start_time = None
        
        # Control
        self.running = False
    
    def _log(self, message: str, level: str = "INFO"):
        """Logging helper"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "DEBUG" and not self.config.DEBUG:
            return
        
        prefix = {
            "INFO": "ℹ️",
            "DEBUG": "🔍",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }.get(level, "")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    async def process_audio(self, data: dict):
        """
        Xử lý audio từ TTS service
        
        Args:
            data: {
                audio_path, audio_duration, response,
                nickname, intent, priority, ...
            }
        """
        self.processed_count += 1
        
        # Extract data
        audio_path = data.get('audio_path', '')
        audio_duration = data.get('audio_duration', 0)
        nickname = data.get('nickname', 'Unknown')
        intent = data.get('intent', 'unknown')
        response = data.get('response', '')[:50]
        
        if not audio_path:
            self._log("Empty audio path, skipping", level="DEBUG")
            return
        
        self._log(f"📥 [{nickname}] {response}..." if len(response) >= 50 else f"📥 [{nickname}] {response}")
        
        # 1. Analyze lip sync
        self._log(f"   🔊 Analyzing audio ({audio_duration:.1f}s)...", level="DEBUG")
        lip_sync_frames = await self.lipsync_analyzer.analyze(
            audio_path, 
            fps=self.config.AVATAR_FPS
        )
        
        if not lip_sync_frames:
            self._log("   Failed to analyze lip sync", level="ERROR")
            return
        
        self._log(f"   📊 Generated {len(lip_sync_frames)} frames", level="DEBUG")
        
        # 2. Map intent to expression
        expression = self._get_expression_for_intent(intent)
        self._log(f"   🎭 Expression: {expression.value} (intent: {intent})", level="DEBUG")
        
        # 3. Render animation
        frames = await self.renderer.render_animation(
            lip_sync_frames,
            expression=expression,
            duration=audio_duration
        )
        
        if not frames:
            self._log("   Failed to render frames", level="ERROR")
            return
        
        # 4. Export video
        output_path = self._generate_output_path()
        export_success = await self.renderer.export_video(
            frames,
            output_path,
            audio_path=audio_path
        )
        
        if not export_success:
            self._log("   Failed to export video", level="ERROR")
            return
        
        self.success_count += 1
        
        # 5. Build output for OBS service
        output = {
            # Original data
            "user_id": data.get('user_id'),
            "username": data.get('username'),
            "nickname": nickname,
            "original_comment": data.get('original_comment'),
            
            # Response
            "response": data.get('response'),
            "intent": intent,
            "priority": data.get('priority'),
            
            # Audio
            "audio_path": audio_path,
            "audio_duration": audio_duration,
            
            # Video
            "video_path": output_path,
            "video_duration": audio_duration,
            "frame_count": len(frames),
            "fps": self.config.AVATAR_FPS,
            
            # Metadata
            "processed_at": datetime.now().timestamp()
        }
        
        # 6. Publish to OBS service
        try:
            await self.publisher.publish(output)
            self._log(f"   ✅ → OBS ({len(frames)} frames, {audio_duration:.1f}s)")
        except Exception as e:
            self._log(f"   Failed to publish: {e}", level="ERROR")
    
    def _get_expression_for_intent(self, intent: str) -> Expression:
        """Map intent sang Expression"""
        expr_name = self.config.EXPRESSION_MAP.get(intent, "neutral")
        
        try:
            return Expression(expr_name)
        except ValueError:
            return Expression.NEUTRAL
    
    def _generate_output_path(self) -> str:
        """Generate unique output path"""
        output_dir = self.config.get_output_path()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        extension = self.config.OUTPUT_FORMAT
        
        return str(output_dir / f"avatar_{timestamp}.{extension}")
    
    async def run(self):
        """Run avatar service"""
        self.running = True
        self.start_time = datetime.now()
        
        print("=" * 50)
        print("🎭 AVATAR SERVICE (2D Vtuber)")
        print("=" * 50)
        print(f"📊 Resolution: {self.config.AVATAR_WIDTH}x{self.config.AVATAR_HEIGHT}")
        print(f"🎬 FPS: {self.config.AVATAR_FPS}")
        print(f"📂 Output: {self.config.OUTPUT_FORMAT.upper()}")
        print(f"📥 Input Queue: {self.config.INPUT_QUEUE}")
        print(f"📤 Output Queue: {self.config.OUTPUT_QUEUE}")
        print("=" * 50)
        
        try:
            # Connect to queues
            self._log("Connecting to RabbitMQ...")
            await self.consumer.connect()
            await self.publisher.connect()
            self._log("Connected!", level="SUCCESS")
            
            # Start WebSocket streamer (if enabled)
            if self.ws_streamer:
                asyncio.create_task(self.ws_streamer.start())
            
            # Start consuming
            self._log("Waiting for audio from TTS service...")
            await self.consumer.consume(self.process_audio)
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self._log("Shutting down...")
        except Exception as e:
            self._log(f"Service error: {e}", level="ERROR")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        
        if self.ws_streamer:
            self.ws_streamer.stop()
        
        await self.consumer.disconnect()
        await self.publisher.disconnect()
        
        # Print stats
        runtime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        print("\n" + "=" * 50)
        print("📊 SESSION STATS")
        print("=" * 50)
        print(f"⏱️  Runtime: {runtime:.1f}s")
        print(f"📥 Processed: {self.processed_count}")
        print(f"✅ Success: {self.success_count}")
        if self.processed_count > 0:
            success_rate = (self.success_count / self.processed_count) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
        print("=" * 50)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Avatar Service - 2D Vtuber")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--width", type=int, default=512, help="Avatar width")
    parser.add_argument("--height", type=int, default=512, help="Avatar height")
    parser.add_argument("--fps", type=int, default=30, help="Animation FPS")
    parser.add_argument("--model", type=str, help="Path to avatar model")
    parser.add_argument("--websocket", action="store_true", help="Enable WebSocket streaming")
    
    args = parser.parse_args()
    
    # Create config
    config = Config()
    
    # Override from args
    if args.debug:
        config.DEBUG = True
    if args.width:
        config.AVATAR_WIDTH = args.width
    if args.height:
        config.AVATAR_HEIGHT = args.height
    if args.fps:
        config.AVATAR_FPS = args.fps
    if args.model:
        config.AVATAR_MODEL_PATH = args.model
    if args.websocket:
        config.WEBSOCKET_ENABLED = True
    
    # Create and run service
    service = AvatarService(config)
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(service.shutdown())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBye! 👋")
    except Exception as e:
        print(f"[FATAL] {e}")
        sys.exit(1)
