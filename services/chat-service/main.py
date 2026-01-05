"""
main.py
Chat Service Entry Point
Nhận từ NLP → Generate response → Đẩy sang TTS
"""

import sys
import asyncio
import argparse
from datetime import datetime

from config import Config
from message_queue import MessageQueueConsumer, MessageQueuePublisher
from prompt_template import PromptTemplate
from rag_pipeline import RAGPipeline
from response_generator import ResponseGenerator


class ChatService:
    """
    Chat Service
    Pipeline: NLP Output → RAG → LLM → Response
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        self.prompt_template = PromptTemplate(config)
        self.rag = RAGPipeline(config)
        self.generator = ResponseGenerator(config)
        
        # Message queues
        self.consumer = MessageQueueConsumer(config)
        self.publisher = MessageQueuePublisher(config)
        
        # Stats
        self.processed_count = 0
        self.response_count = 0
    
    async def process_comment(self, data: dict):
        """
        Xử lý comment từ NLP service
        
        Args:
            data: {
                user_id, username, nickname, content,
                intent, intent_confidence, priority, ...
            }
        """
        self.processed_count += 1
        
        # Extract data
        username = data.get('nickname', data.get('username', 'bạn'))
        content = data.get('content', '')
        intent = data.get('intent', 'unknown')
        priority = data.get('priority', 1)
        
        self._log(f"📥 [{username}]: {content}")
        self._log(f"   Intent: {intent} | Priority: {priority}", level="DEBUG")
        
        # 1. RAG - Retrieve context
        context = self.rag.retrieve(content, intent)
        if context:
            self._log(f"   📚 Context: {context[:50]}...", level="DEBUG")
        
        # 2. Build prompt
        messages = self.prompt_template.build_messages(
            comment=content,
            username=username,
            intent=intent,
            context=context
        )
        
        # 3. Generate response
        response = await self.generator.generate(
            messages=messages,
            timeout=self.config.RESPONSE_TIMEOUT
        )
        
        if not response:
            self._log("   ⚠️ No response generated", level="DEBUG")
            return
        
        self.response_count += 1
        self._log(f"💬 Response: {response}")
        
        # 4. Build output for TTS
        output = {
            # Original data
            "user_id": data.get('user_id'),
            "username": data.get('username'),
            "nickname": username,
            "original_comment": data.get('original_content', content),
            
            # Response
            "response": response,
            "intent": intent,
            "priority": priority,
            
            # Metadata
            "processed_at": datetime.now().timestamp()
        }
        
        # 5. Publish to TTS
        try:
            await self.publisher.publish(output)
            self._log("   ✅ → TTS", level="DEBUG")
        except Exception as e:
            self._log(f"   ❌ Publish error: {e}", level="ERROR")
    
    async def start(self):
        """Start Chat service"""
        self._log("🚀 Starting Chat Service...")
        
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
        
        self._log(f"🤖 LLM: {self.config.LLM_PROVIDER}/{self.config.LLM_MODEL}")
        self._log("👂 Listening for comments...")
        self._log("-" * 50)
        
        # Start consuming
        await self.consumer.consume(self.process_comment)
        
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    
    async def stop(self):
        """Stop Chat service"""
        self._log("\n⏹️ Stopping Chat Service...")
        self._log(f"📊 Stats: Processed={self.processed_count}, Responses={self.response_count}")
        
        await self.consumer.disconnect()
        await self.publisher.disconnect()
    
    def _log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "DEBUG" and not self.config.DEBUG:
            return
        
        prefix = {"INFO": "", "DEBUG": "[DEBUG] ", "ERROR": "[ERROR] "}.get(level, "")
        print(f"[{timestamp}] {prefix}{message}")


def parse_args():
    parser = argparse.ArgumentParser(description="Chat Service")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


async def main():
    args = parse_args()
    config = Config()
    
    if args.debug:
        config.DEBUG = True
    
    print("\n" + "=" * 60)
    print("  CHAT SERVICE - AI Response Generator")
    print("=" * 60)
    print(f"  Input Queue : {config.INPUT_QUEUE}")
    print(f"  Output Queue: {config.OUTPUT_QUEUE}")
    print(f"  LLM Provider: {config.LLM_PROVIDER}")
    print(f"  LLM Model   : {config.LLM_MODEL}")
    print(f"  Persona     : {config.PERSONA_NAME}")
    print(f"  Debug       : {config.DEBUG}")
    print("=" * 60)
    print("\n⚠️  Press Ctrl+C to stop\n")
    
    service = ChatService(config)
    
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
        print("\n✅ Chat Service stopped")
        sys.exit(0)
