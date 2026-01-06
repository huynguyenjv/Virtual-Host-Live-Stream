"""
main.py
NLP Service Entry Point
Nhận comment từ RabbitMQ → Xử lý NLP → Đẩy sang chat-service
"""

import sys
import asyncio
import argparse
from datetime import datetime

from config import Config
from message_queue import MessageQueueConsumer, MessageQueuePublisher
from preprocess import TextPreprocessor
from filter import CommentFilter
from intent_detector import IntentDetector


class NLPService:
    """
    NLP Service
    Pipeline: Preprocess → Filter → Intent Detection → Publish
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        # remove_emoji=True vì output là lời nói (TTS không đọc được emoji)
        self.preprocessor = TextPreprocessor(remove_emoji=True)
        self.filter = CommentFilter(config)
        self.intent_detector = IntentDetector()
        
        # Message queues
        self.consumer = MessageQueueConsumer(config)
        self.publisher = MessageQueuePublisher(config)
        
        # Stats
        self.processed_count = 0
        self.filtered_count = 0
        self.published_count = 0
    
    async def process_comment(self, data: dict):
        """
        Xử lý 1 comment
        
        Args:
            data: {user_id, username, nickname, content, timestamp}
        """
        self.processed_count += 1
        
        # Extract content
        content = data.get('content', '')
        username = data.get('username', 'unknown')
        nickname = data.get('nickname', username)
        
        self._log(f"📥 [{nickname}]: {content}")
        
        # 1. Preprocess (bao gồm remove emoji, tính emoji_ratio)
        preprocessed = self.preprocessor.process(content)
        cleaned_text = preprocessed['cleaned']
        emoji_ratio = preprocessed.get('emoji_ratio', 0.0)
        is_emoji_only = preprocessed.get('is_emoji_only', False)
        
        # 2. Filter (truyền emoji data để detect spam)
        filter_result = self.filter.filter(
            cleaned_text,
            emoji_ratio=emoji_ratio,
            is_emoji_only=is_emoji_only
        )
        
        if not filter_result.should_respond:
            self.filtered_count += 1
            self._log(f"   ⏭️ Filtered: {filter_result.reason}", level="DEBUG")
            return
        
        # 3. Intent Detection
        intent_result = self.intent_detector.detect_with_details(cleaned_text)
        
        # 4. Build output message
        output = {
            # Original data
            "user_id": data.get('user_id'),
            "username": username,
            "nickname": nickname,
            "original_content": content,
            
            # Processed data
            "content": cleaned_text,
            "mentions": preprocessed['mentions'],
            
            # NLP results
            "intent": intent_result['intent'],
            "intent_confidence": intent_result['confidence'],
            "priority": filter_result.priority,
            
            # Metadata
            "timestamp": data.get('timestamp'),
            "processed_at": datetime.now().timestamp()
        }
        
        # 5. Publish to chat-service
        try:
            await self.publisher.publish(output)
            self.published_count += 1
            self._log(
                f"   ✅ Intent: {intent_result['intent']} | "
                f"Priority: {filter_result.priority} | "
                f"→ Published",
                level="DEBUG"
            )
        except Exception as e:
            self._log(f"   ❌ Publish error: {e}", level="ERROR")
    
    async def start(self):
        """Start NLP service"""
        self._log("🚀 Starting NLP Service...")
        
        # Connect to queues
        try:
            await self.consumer.connect()
            self._log(f"✅ Connected to input queue: {self.config.INPUT_QUEUE}")
        except Exception as e:
            self._log(f"❌ Failed to connect consumer: {e}", level="ERROR")
            raise
        
        try:
            await self.publisher.connect()
            self._log(f"✅ Connected to output queue: {self.config.OUTPUT_QUEUE}")
        except Exception as e:
            self._log(f"❌ Failed to connect publisher: {e}", level="ERROR")
            raise
        
        self._log("👂 Listening for comments...")
        self._log("-" * 50)
        
        # Start consuming
        await self.consumer.consume(self.process_comment)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    
    async def stop(self):
        """Stop NLP service"""
        self._log("\n⏹️ Stopping NLP Service...")
        self._log(f"📊 Stats: Processed={self.processed_count}, "
                  f"Filtered={self.filtered_count}, "
                  f"Published={self.published_count}")
        
        await self.consumer.disconnect()
        await self.publisher.disconnect()
    
    def _log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "DEBUG" and not self.config.DEBUG:
            return
        
        prefix = {
            "INFO": "",
            "DEBUG": "[DEBUG] ",
            "ERROR": "[ERROR] "
        }.get(level, "")
        
        print(f"[{timestamp}] {prefix}{message}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="NLP Service")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


async def main():
    """Main async function"""
    args = parse_args()
    
    # Load config
    config = Config()
    
    if args.debug:
        config.DEBUG = True
    
    # Banner
    print("\n" + "=" * 60)
    print("  NLP SERVICE - Comment Processing Pipeline")
    print("=" * 60)
    print(f"  Input Queue : {config.INPUT_QUEUE}")
    print(f"  Output Queue: {config.OUTPUT_QUEUE}")
    print(f"  RabbitMQ    : {config.QUEUE_HOST}:{config.QUEUE_PORT}")
    print(f"  Debug       : {config.DEBUG}")
    print("=" * 60)
    print("\n⚠️  Press Ctrl+C to stop\n")
    
    # Create and run service
    service = NLPService(config)
    
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
        print("\n✅ NLP Service stopped")
        sys.exit(0)
