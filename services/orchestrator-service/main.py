"""
main.py
Orchestrator Service Entry Point
🧠 Central Brain - Quyết định comment nào được respond

Pipeline: NLP Results → Brain Decision → Chat Service (or Skip)
"""

import sys
import asyncio
import argparse
import signal
from datetime import datetime
from pathlib import Path

# Add project root to path for core module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from message_queue import MessageQueueConsumer, MessageQueuePublisher

from core.brain import LiveBrain, BrainInput, Action, get_brain
from core.state_machine import SaleStateMachine, SaleState, get_state_machine
from core.observability import MetricsCollector, StructuredLogger, get_metrics, get_logger


class OrchestratorService:
    """
    🧠 ORCHESTRATOR SERVICE
    
    Central controller cho toàn bộ pipeline:
    - Nhận NLP results (intent, entities)
    - Brain quyết định: SPEAK / SKIP / QUEUE
    - State Machine quản lý sale flow
    - Observability track tất cả metrics
    
    Pipeline:
    Crawl → NLP → [ORCHESTRATOR] → Chat → TTS → Avatar → OBS
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Core components
        self.brain = LiveBrain(config.get_brain_config())
        self.state_machine = SaleStateMachine()
        self.metrics = MetricsCollector()
        self.logger = StructuredLogger(
            service_name="orchestrator",
            log_dir=config.LOG_DIR
        )
        
        # Message queues
        self.consumer = MessageQueueConsumer(config)
        self.publisher = MessageQueuePublisher(config)
        
        # Stats
        self.processed_count = 0
        self.speak_count = 0
        self.skip_count = 0
        self.start_time = None
        
        # Viewer tracking
        self.current_viewer_count = 0
        
        # Control
        self.running = False
        
        # Wire up callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Setup callbacks giữa các components"""
        
        # Brain decision → Metrics
        self.brain.on_decision = lambda inp, dec: self.metrics.log_decision(dec)
        
        # State transition → Logger
        self.state_machine.on_transition = lambda f, t, tr: self.logger.log_state_transition(
            f.value, t.value, tr
        )
    
    async def process_nlp_result(self, data: dict):
        """
        Xử lý kết quả từ NLP service
        
        Input format:
        {
            "user_id": "123",
            "username": "user123",
            "nickname": "User",
            "original_comment": "Giá bao nhiêu?",
            "intent": "price_question",
            "entities": [...],
            "confidence": 0.95,
            "priority": 5,
            "timestamp": 1704067200.0
        }
        """
        self.processed_count += 1
        
        # Extract data
        user_id = data.get('user_id', '')
        username = data.get('username', 'unknown')
        nickname = data.get('nickname', username)
        comment = data.get('original_comment', '')
        intent = data.get('intent', 'unknown')
        priority = data.get('priority', 5)
        
        # Log incoming comment
        self.logger.log_comment_received(username, comment, intent)
        comment_event = self.metrics.log_comment(username, comment, intent)
        
        # Check state timeout
        if self.config.AUTO_STATE_TRANSITION:
            self.state_machine.check_timeout()
        
        # Build brain input
        brain_input = BrainInput(
            comment_id=data.get('comment_id', f"cmt_{self.processed_count}"),
            username=username,
            comment_text=comment,
            intent=intent,
            viewer_count=self.current_viewer_count,
            sale_state=self.state_machine.current_state_name,
            is_follower=data.get('is_follower', False),
            is_subscriber=data.get('is_subscriber', False),
            gift_value=data.get('gift_value', 0.0)
        )
        
        # 🧠 GET DECISION FROM BRAIN
        decision = self.brain.decide(brain_input)
        
        # Log decision
        self.logger.log_decision(
            decision.action.value,
            decision.reason.value,
            decision.priority,
            intent=intent,
            state=self.state_machine.current_state_name
        )
        
        # Act on decision
        if decision.action == Action.SPEAK:
            await self._handle_speak(data, decision, comment_event)
        elif decision.action == Action.QUEUE:
            await self._handle_queue(data, decision)
        else:  # SKIP or WAIT
            await self._handle_skip(data, decision)
    
    async def _handle_speak(self, data: dict, decision, comment_event):
        """Handle SPEAK decision - forward to Chat service"""
        self.speak_count += 1
        
        # Add orchestrator metadata
        output = {
            **data,
            
            # Brain decision
            "brain_decision": {
                "action": decision.action.value,
                "reason": decision.reason.value,
                "priority": decision.priority,
                "cooldown": decision.cooldown,
                "confidence": decision.confidence,
            },
            
            # State info
            "sale_state": self.state_machine.current_state_name,
            "response_style": self.state_machine.get_response_style(),
            
            # Timing
            "orchestrator_timestamp": datetime.now().timestamp(),
        }
        
        # Publish to Chat service
        try:
            await self.publisher.publish(output)
            
            # Mark as responded
            self.metrics.log_response(comment_event, 0.0)  # Response time will be updated by chat
            
            # Update brain
            self.brain.mark_spoken()
            self.state_machine.notify_speak()
            
            # Auto state transition based on intent
            if self.config.AUTO_STATE_TRANSITION:
                self._auto_transition(data.get('intent', ''))
            
            self._log(f"✅ SPEAK → Chat | reason={decision.reason.value} priority={decision.priority}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish to Chat: {e}")
    
    async def _handle_queue(self, data: dict, decision):
        """Handle QUEUE decision - add to priority queue"""
        # TODO: Implement priority queue for later processing
        self._log(f"📥 QUEUE | reason={decision.reason.value} priority={decision.priority}", level="DEBUG")
    
    async def _handle_skip(self, data: dict, decision):
        """Handle SKIP/WAIT decision"""
        self.skip_count += 1
        self._log(f"⏭️ SKIP | reason={decision.reason.value}", level="DEBUG")
    
    def _auto_transition(self, intent: str):
        """Auto transition state based on intent"""
        
        intent_triggers = {
            "greeting": "greeting_received",
            "product_question": "product_mention",
            "price_question": "price_question",
            "purchase_intent": "purchase_intent",
            "complaint": "complaint_received",
        }
        
        trigger = intent_triggers.get(intent)
        if trigger:
            self.state_machine.transition(trigger)
    
    def update_viewer_count(self, count: int):
        """Update viewer count (called from external source)"""
        old_count = self.current_viewer_count
        self.current_viewer_count = count
        
        self.metrics.log_viewer_count(count)
        self.state_machine.update_viewer_count(count)
        
        if old_count > 0:
            delta = count - old_count
            if abs(delta) > old_count * 0.1:  # > 10% change
                self.logger.log_viewer_update(count, delta)
    
    def _log(self, message: str, level: str = "INFO"):
        """Simple logging helper"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "DEBUG" and not self.config.DEBUG:
            return
        
        print(f"[{timestamp}] {message}")
    
    async def run(self):
        """Run orchestrator service"""
        self.running = True
        self.start_time = datetime.now()
        
        print("=" * 60)
        print("🧠 ORCHESTRATOR SERVICE")
        print("   Central Brain - Decision Engine")
        print("=" * 60)
        print(f"📥 Input:  {self.config.INPUT_QUEUE} (from NLP)")
        print(f"📤 Output: {self.config.OUTPUT_QUEUE} (to Chat)")
        print(f"⚙️  State Machine: {'ON' if self.config.ENABLE_STATE_MACHINE else 'OFF'}")
        print("=" * 60)
        
        self.logger.log_session_start(
            input_queue=self.config.INPUT_QUEUE,
            output_queue=self.config.OUTPUT_QUEUE
        )
        
        try:
            # Connect to queues
            self._log("Connecting to RabbitMQ...")
            await self.consumer.connect()
            await self.publisher.connect()
            self._log("✅ Connected!")
            
            # Start metrics export task
            asyncio.create_task(self._metrics_export_loop())
            
            # Start consuming
            self._log("Waiting for NLP results...")
            await self.consumer.consume(self.process_nlp_result)
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self._log("Shutting down...")
        except Exception as e:
            self.logger.error(f"Service error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _metrics_export_loop(self):
        """Periodically export metrics"""
        while self.running:
            await asyncio.sleep(self.config.METRICS_EXPORT_INTERVAL)
            
            if self.running:
                filepath = f"{self.config.METRICS_EXPORT_PATH}/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                Path(self.config.METRICS_EXPORT_PATH).mkdir(parents=True, exist_ok=True)
                self.metrics.export_to_json(filepath)
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        
        await self.consumer.disconnect()
        await self.publisher.disconnect()
        
        # Calculate stats
        runtime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        stats = {
            "runtime": f"{runtime:.1f}s",
            "processed": self.processed_count,
            "speak": self.speak_count,
            "skip": self.skip_count,
            "speak_rate": f"{self.speak_count / self.processed_count * 100:.1f}%" if self.processed_count > 0 else "0%"
        }
        
        self.logger.log_session_end(runtime, stats)
        
        # Print stats
        print("\n" + "=" * 60)
        print("📊 SESSION STATS")
        print("=" * 60)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Print metrics summary
        summary = self.metrics.get_summary()
        print(f"\n  Response Rate: {summary.response_rate:.1%}")
        print(f"  Avg Speak Interval: {summary.avg_speak_interval:.1f}s")
        print(f"  State Transitions: {self.state_machine.get_stats()['transition_count']}")
        print("=" * 60)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Orchestrator Service - Central Brain")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-state-machine", action="store_true", help="Disable state machine")
    
    args = parser.parse_args()
    
    # Create config
    config = Config()
    
    if args.debug:
        config.DEBUG = True
    if args.no_state_machine:
        config.ENABLE_STATE_MACHINE = False
    
    # Create and run service
    service = OrchestratorService(config)
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(service.shutdown())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
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
