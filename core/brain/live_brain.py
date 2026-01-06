"""
live_brain.py
LIVE BRAIN - Central Decision Engine
Quyết định duy nhất: Live có nói hay không?
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime


class Action(Enum):
    """Các action có thể thực hiện"""
    SPEAK = "SPEAK"      # Nói
    SKIP = "SKIP"        # Bỏ qua comment này
    WAIT = "WAIT"        # Chờ thêm
    QUEUE = "QUEUE"      # Đưa vào queue chờ


class Reason(Enum):
    """Lý do quyết định"""
    # Speak reasons
    GREETING = "GREETING"
    PRICE_QUESTION = "PRICE_QUESTION"
    PRODUCT_QUESTION = "PRODUCT_QUESTION"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    SALE_CTA = "SALE_CTA"
    ENGAGEMENT = "ENGAGEMENT"
    
    # Skip reasons
    SPAM = "SPAM"
    DUPLICATE = "DUPLICATE"
    LOW_PRIORITY = "LOW_PRIORITY"
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"
    
    # Wait reasons
    TOO_FAST = "TOO_FAST"
    QUEUE_FULL = "QUEUE_FULL"
    STATE_TRANSITION = "STATE_TRANSITION"


@dataclass
class Decision:
    """Output của Live Brain"""
    action: Action
    reason: Reason
    cooldown: float = 0.0          # Seconds to wait before next speak
    priority: int = 5              # 1-10, 10 = highest
    confidence: float = 1.0        # 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "reason": self.reason.value,
            "cooldown": self.cooldown,
            "priority": self.priority,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class BrainInput:
    """Input cho Live Brain"""
    # Comment info
    comment_id: str
    username: str
    comment_text: str
    intent: str
    
    # Context
    viewer_count: int = 0
    time_since_last_speak: float = 0.0  # seconds
    
    # Sale state
    sale_state: str = "IDLE"
    
    # Optional
    is_follower: bool = False
    is_subscriber: bool = False
    gift_value: float = 0.0
    
    # Metadata
    timestamp: float = field(default_factory=time.time)


class LiveBrain:
    """
    🧠 LIVE BRAIN - Central Decision Engine
    
    Tất cả service khác phải phục tùng quyết định của Brain.
    
    Decision Flow:
    1. Check cooldown
    2. Check spam/duplicate
    3. Evaluate priority based on intent + context
    4. Match with current sale state
    5. Return decision
    """
    
    def __init__(self, config: dict = None):
        self.config = config or self._default_config()
        
        # State
        self.last_speak_time: float = 0.0
        self.speak_count: int = 0
        self.recent_comments: List[str] = []  # For duplicate detection
        self.queue: List[BrainInput] = []
        
        # Metrics callback
        self.on_decision = None  # Callback for observability
    
    def _default_config(self) -> dict:
        return {
            # Timing
            "min_speak_interval": 3.0,      # Minimum seconds between speaks
            "max_speak_interval": 15.0,     # Force speak if silent too long
            "default_cooldown": 4.0,        # Default cooldown after speak
            
            # Priority thresholds
            "high_priority_threshold": 7,
            "auto_speak_priority": 9,
            
            # Queue
            "max_queue_size": 10,
            "queue_timeout": 30.0,          # Remove from queue after N seconds
            
            # Duplicate detection
            "duplicate_window": 10,         # Check last N comments
            "duplicate_similarity": 0.8,    # Similarity threshold
            
            # Intent priorities (base)
            "intent_priority": {
                "greeting": 6,
                "price_question": 9,
                "product_question": 8,
                "purchase_intent": 10,
                "thanks": 5,
                "complaint": 7,
                "request": 6,
                "chitchat": 4,
                "spam": 1,
                "unknown": 3
            },
            
            # State modifiers (multiply priority)
            "state_modifiers": {
                "IDLE": {"greeting": 1.5, "chitchat": 1.2},
                "WARM_UP": {"product_question": 1.3},
                "INTEREST": {"price_question": 1.5},
                "PRICE": {"purchase_intent": 2.0},
                "CTA": {"purchase_intent": 1.5},
                "COOLDOWN": {}  # No modifiers during cooldown
            },
            
            # Viewer count modifiers
            "viewer_modifiers": {
                "low": {"threshold": 50, "multiplier": 1.2},   # More responsive when few viewers
                "high": {"threshold": 500, "multiplier": 0.8}  # More selective when many viewers
            }
        }
    
    def decide(self, input_data: BrainInput) -> Decision:
        """
        Main decision method
        
        Args:
            input_data: BrainInput with all context
            
        Returns:
            Decision object
        """
        now = time.time()
        time_since_speak = now - self.last_speak_time
        input_data.time_since_last_speak = time_since_speak
        
        # 1. Check cooldown
        min_interval = self.config["min_speak_interval"]
        if time_since_speak < min_interval:
            return Decision(
                action=Action.WAIT,
                reason=Reason.TOO_FAST,
                cooldown=min_interval - time_since_speak,
                priority=0,
                metadata={"wait_time": min_interval - time_since_speak}
            )
        
        # 2. Check duplicate/spam
        if self._is_duplicate(input_data.comment_text):
            return Decision(
                action=Action.SKIP,
                reason=Reason.DUPLICATE,
                priority=0
            )
        
        if input_data.intent == "spam":
            return Decision(
                action=Action.SKIP,
                reason=Reason.SPAM,
                priority=0
            )
        
        # 3. Calculate priority
        priority = self._calculate_priority(input_data)
        
        # 4. Force speak if silent too long
        max_interval = self.config["max_speak_interval"]
        if time_since_speak > max_interval:
            priority = max(priority, self.config["auto_speak_priority"])
        
        # 5. Make decision based on priority
        if priority >= self.config["auto_speak_priority"]:
            decision = self._create_speak_decision(input_data, priority)
        elif priority >= self.config["high_priority_threshold"]:
            # High priority but not auto - check queue
            if len(self.queue) < self.config["max_queue_size"]:
                decision = self._create_speak_decision(input_data, priority)
            else:
                decision = Decision(
                    action=Action.QUEUE,
                    reason=Reason.QUEUE_FULL,
                    priority=priority
                )
        else:
            # Low priority - skip or queue
            decision = Decision(
                action=Action.SKIP,
                reason=Reason.LOW_PRIORITY,
                priority=priority
            )
        
        # Track for duplicate detection
        self._track_comment(input_data.comment_text)
        
        # Callback for observability
        if self.on_decision:
            self.on_decision(input_data, decision)
        
        return decision
    
    def _calculate_priority(self, input_data: BrainInput) -> int:
        """Calculate priority score 1-10"""
        
        # Base priority from intent
        intent = input_data.intent.lower()
        base_priority = self.config["intent_priority"].get(intent, 3)
        
        # State modifier
        state = input_data.sale_state
        state_mods = self.config["state_modifiers"].get(state, {})
        state_multiplier = state_mods.get(intent, 1.0)
        
        # Viewer modifier
        viewer_count = input_data.viewer_count
        viewer_multiplier = 1.0
        
        if viewer_count < self.config["viewer_modifiers"]["low"]["threshold"]:
            viewer_multiplier = self.config["viewer_modifiers"]["low"]["multiplier"]
        elif viewer_count > self.config["viewer_modifiers"]["high"]["threshold"]:
            viewer_multiplier = self.config["viewer_modifiers"]["high"]["multiplier"]
        
        # Bonus for followers/subscribers
        bonus = 0
        if input_data.is_subscriber:
            bonus += 2
        elif input_data.is_follower:
            bonus += 1
        
        # Gift bonus
        if input_data.gift_value > 0:
            bonus += min(3, int(input_data.gift_value / 100))
        
        # Calculate final
        priority = base_priority * state_multiplier * viewer_multiplier + bonus
        
        return max(1, min(10, int(priority)))
    
    def _create_speak_decision(self, input_data: BrainInput, priority: int) -> Decision:
        """Create a SPEAK decision"""
        
        # Map intent to reason
        intent_to_reason = {
            "greeting": Reason.GREETING,
            "price_question": Reason.PRICE_QUESTION,
            "product_question": Reason.PRODUCT_QUESTION,
            "purchase_intent": Reason.SALE_CTA,
            "thanks": Reason.ENGAGEMENT,
            "chitchat": Reason.ENGAGEMENT,
        }
        
        reason = intent_to_reason.get(
            input_data.intent.lower(), 
            Reason.HIGH_PRIORITY
        )
        
        # Calculate cooldown based on priority
        base_cooldown = self.config["default_cooldown"]
        cooldown = base_cooldown * (1 - (priority - 5) * 0.1)  # Higher priority = shorter cooldown
        cooldown = max(2.0, min(8.0, cooldown))
        
        return Decision(
            action=Action.SPEAK,
            reason=reason,
            cooldown=cooldown,
            priority=priority,
            confidence=0.8 + (priority / 50),  # Higher priority = higher confidence
            metadata={
                "intent": input_data.intent,
                "sale_state": input_data.sale_state,
                "viewer_count": input_data.viewer_count
            }
        )
    
    def _is_duplicate(self, text: str) -> bool:
        """Check if comment is duplicate"""
        text_lower = text.lower().strip()
        
        for recent in self.recent_comments:
            if self._similarity(text_lower, recent) > self.config["duplicate_similarity"]:
                return True
        
        return False
    
    def _similarity(self, a: str, b: str) -> float:
        """Simple similarity check"""
        if a == b:
            return 1.0
        
        # Simple word overlap
        words_a = set(a.split())
        words_b = set(b.split())
        
        if not words_a or not words_b:
            return 0.0
        
        overlap = len(words_a & words_b)
        total = len(words_a | words_b)
        
        return overlap / total if total > 0 else 0.0
    
    def _track_comment(self, text: str):
        """Track comment for duplicate detection"""
        self.recent_comments.append(text.lower().strip())
        
        # Keep only last N
        window = self.config["duplicate_window"]
        if len(self.recent_comments) > window:
            self.recent_comments = self.recent_comments[-window:]
    
    def mark_spoken(self):
        """Mark that we just spoke (call after TTS plays)"""
        self.last_speak_time = time.time()
        self.speak_count += 1
    
    def get_stats(self) -> dict:
        """Get brain statistics"""
        return {
            "speak_count": self.speak_count,
            "last_speak_time": self.last_speak_time,
            "time_since_speak": time.time() - self.last_speak_time,
            "queue_size": len(self.queue),
            "recent_comments_count": len(self.recent_comments)
        }


# Singleton instance
_brain_instance: Optional[LiveBrain] = None


def get_brain(config: dict = None) -> LiveBrain:
    """Get singleton Brain instance"""
    global _brain_instance
    
    if _brain_instance is None:
        _brain_instance = LiveBrain(config)
    
    return _brain_instance
