"""
main.py
TTS Service Entry Point
Nhận từ Chat → Convert to Speech → Đẩy sang Avatar
"""

import sys
import asyncio
import argparse
from datetime import datetime

from config import Config
from message_queue import MessageQueueConsumer, MessageQueuePublisher
from tts_engine import TTSEngine
from audio_utils import AudioUtils


class TTSService:
    """
    TTS Service
    Pipeline: Chat Response → TTS → Audio File → Avatar
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        self.tts_engine = TTSEngine(config)
        self.audio_utils = AudioUtils()
        
        # Message queues
        self.consumer = MessageQueueConsumer(config)
        self.publisher = MessageQueuePublisher(config)
        
        # Stats
        self.processed_count = 0
        self.success_count = 0
    
    async def process_response(self, data: dict):
        """
        Xử lý response từ chat service
        
        Args:
            data: {
                response, username, nickname, original_comment,
                intent, priority, ...
            }
        """
        self.processed_count += 1
        
        # Extract data
        response = data.get('response', '')
        nickname = data.get('nickname', 'Unknown')
        
        if not response:
            self._log(f"⚠️ Empty response, skipping", level="DEBUG")
            return
        
        self._log(f"📥 [{nickname}] → \"{response[:50]}...\"" if len(response) > 50 else f"📥 [{nickname}] → \"{response}\"")
        
        # 1. Synthesize speech
        audio_path = await self.tts_engine.synthesize(response)
        
        if not audio_path:
            self._log("   ❌ TTS failed", level="ERROR")
            return
        
        self.success_count += 1
        
        # 2. Get audio duration
        duration = await self.audio_utils.get_duration(audio_path)
        duration_str = f"{duration:.1f}s" if duration else "unknown"
        
        self._log(f"   🔊 Generated: {audio_path} ({duration_str})", level="DEBUG")
        
        # 3. Build output for Avatar service
        output = {
            # Original data
            "user_id": data.get('user_id'),
            "username": data.get('username'),
            "nickname": nickname,
            "original_comment": data.get('original_comment'),
            
            # Response
            "response": response,
            "intent": data.get('intent'),
            "priority": data.get('priority'),
            
            # Audio
            "audio_path": audio_path,
            "audio_duration": duration,
            
            # Metadata
            "processed_at": datetime.now().timestamp()
        }
        
        # 4. Publish to Avatar service
        try:
            await self.publisher.publish(output)
            self._log(f"   ✅ → Avatar ({duration_str})")
        except Exception as e:
            self._log(f"   ❌ Publish error: {e}", level="ERROR")
    
    async def start(self):
        """Start TTS service"""
        self._log("🚀 Starting TTS Service...")
        
        # Connect queues
        try:
            await self.consumer.connect()
            self._log(f"✅ Connected to input: {self.config.INPUT_QUEUE}")
        except Exception as e:
            self._log(f"❌ Consumer connect failed: {e}", level="ERROR")
            raise
        
        try:
            await self.publisher.connect()
            self._log(f"✅ Connected to output: {self.config.OUTPUT_QUEUE}")
        except Exception as e:
            self._log(f"❌ Publisher connect failed: {e}", level="ERROR")
            raise
        
        self._log(f"🎤 TTS Engine: {self.config.TTS_ENGINE}")
        self._log(f"🗣️ Voice: {self.config.TTS_VOICE}")
        self._log("👂 Listening for responses...")
        self._log("-" * 50)
        
        # Start consuming
        await self.consumer.consume(self.process_response)
        
        # Periodic cleanup
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            cleanup_task.cancel()
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old audio files"""
        while True:
            await asyncio.sleep(3600)  # Every hour
            self.audio_utils.cleanup_old_files(
                self.config.AUDIO_OUTPUT_DIR,
                max_age_hours=1
            )
            self._log("🧹 Cleaned up old audio files", level="DEBUG")
    
    async def stop(self):
        """Stop TTS service"""
        self._log("\n⏹️ Stopping TTS Service...")
        self._log(f"📊 Stats: Processed={self.processed_count}, Success={self.success_count}")
        
        await self.consumer.disconnect()
        await self.publisher.disconnect()
    
    def _log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "DEBUG" and not self.config.DEBUG:
            return
        
        prefix = {"INFO": "", "DEBUG": "[DEBUG] ", "ERROR": "[ERROR] "}.get(level, "")
        print(f"[{timestamp}] {prefix}{message}")


def parse_args():
    parser = argparse.ArgumentParser(description="TTS Service")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


async def main():
    args = parse_args()
    config = Config()
    
    if args.debug:
        config.DEBUG = True
    
    print("\n" + "=" * 60)
    print("  TTS SERVICE - Text to Speech")
    print("=" * 60)
    print(f"  Input Queue : {config.INPUT_QUEUE}")
    print(f"  Output Queue: {config.OUTPUT_QUEUE}")
    print(f"  TTS Engine  : {config.TTS_ENGINE}")
    print(f"  Voice       : {config.TTS_VOICE}")
    print(f"  Output Dir  : {config.AUDIO_OUTPUT_DIR}")
    print(f"  Debug       : {config.DEBUG}")
    print("=" * 60)
    print("\n⚠️  Press Ctrl+C to stop\n")
    
    service = TTSService(config)
    
    try:
        await service.start()
    except KeyboardInterrupt:
        pass
    finally:
        await service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ TTS Service stopped")
        sys.exit(0)
