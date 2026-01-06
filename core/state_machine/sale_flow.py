"""
sale_flow.py
Sale Flow State Machine Controller
"""

import time
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime

from .states import SaleState, StateConfig, StateSnapshot, STATE_CONFIGS


@dataclass
class TransitionRule:
    """Rule cho state transition"""
    from_state: SaleState
    to_state: SaleState
    trigger: str                    # Event trigger
    condition: Optional[Callable] = None  # Optional condition function
    priority: int = 5               # Higher = checked first


class SaleStateMachine:
    """
    🔄 SALE FLOW STATE MACHINE
    
    Quản lý flow bán hàng trong livestream:
    IDLE → WARM_UP → INTEREST → PRICE → CTA → COOLDOWN → IDLE
    
    Có thể interrupt bất cứ lúc nào để HANDLING_QUESTION hoặc CRISIS
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Current state
        self._current_state = SaleState.IDLE
        self._state_entered_at = time.time()
        self._previous_state: Optional[SaleState] = None
        
        # History
        self._transition_count = 0
        self._state_history: List[StateSnapshot] = []
        
        # Metrics per state
        self._state_metrics: Dict[SaleState, Dict] = {
            state: {"speak_count": 0, "duration": 0.0}
            for state in SaleState
        }
        
        # Viewer tracking
        self._viewer_count_at_enter = 0
        self._current_viewer_count = 0
        
        # Callbacks
        self.on_transition: Optional[Callable] = None
        self.on_state_timeout: Optional[Callable] = None
        
        # Build transition rules
        self._rules = self._build_default_rules()
    
    def _build_default_rules(self) -> List[TransitionRule]:
        """Build default transition rules"""
        
        rules = [
            # Normal flow
            TransitionRule(SaleState.IDLE, SaleState.WARM_UP, "start_warmup"),
            TransitionRule(SaleState.IDLE, SaleState.WARM_UP, "greeting_received"),
            TransitionRule(SaleState.IDLE, SaleState.WARM_UP, "timeout"),
            
            TransitionRule(SaleState.WARM_UP, SaleState.INTEREST, "product_mention"),
            TransitionRule(SaleState.WARM_UP, SaleState.INTEREST, "product_question"),
            TransitionRule(SaleState.WARM_UP, SaleState.INTEREST, "timeout"),
            
            TransitionRule(SaleState.INTEREST, SaleState.PRICE, "price_question"),
            TransitionRule(SaleState.INTEREST, SaleState.PRICE, "reveal_price"),
            TransitionRule(SaleState.INTEREST, SaleState.PRICE, "timeout"),
            
            TransitionRule(SaleState.PRICE, SaleState.CTA, "start_cta"),
            TransitionRule(SaleState.PRICE, SaleState.CTA, "purchase_intent"),
            TransitionRule(SaleState.PRICE, SaleState.CTA, "timeout"),
            
            TransitionRule(SaleState.CTA, SaleState.COOLDOWN, "cta_complete"),
            TransitionRule(SaleState.CTA, SaleState.COOLDOWN, "timeout"),
            
            TransitionRule(SaleState.COOLDOWN, SaleState.IDLE, "cooldown_complete"),
            TransitionRule(SaleState.COOLDOWN, SaleState.IDLE, "timeout"),
            TransitionRule(SaleState.COOLDOWN, SaleState.WARM_UP, "restart_flow"),
            
            # Interrupt flows (from any state)
            TransitionRule(SaleState.WARM_UP, SaleState.HANDLING_QUESTION, "question_received", priority=8),
            TransitionRule(SaleState.INTEREST, SaleState.HANDLING_QUESTION, "question_received", priority=8),
            TransitionRule(SaleState.PRICE, SaleState.HANDLING_QUESTION, "question_received", priority=8),
            
            # Crisis handling
            TransitionRule(SaleState.WARM_UP, SaleState.CRISIS, "complaint_received", priority=9),
            TransitionRule(SaleState.INTEREST, SaleState.CRISIS, "complaint_received", priority=9),
            TransitionRule(SaleState.PRICE, SaleState.CRISIS, "complaint_received", priority=9),
            TransitionRule(SaleState.CTA, SaleState.CRISIS, "complaint_received", priority=9),
            
            # Return from interrupts
            TransitionRule(SaleState.HANDLING_QUESTION, SaleState.INTEREST, "question_answered"),
            TransitionRule(SaleState.CRISIS, SaleState.COOLDOWN, "crisis_resolved"),
        ]
        
        # Sort by priority (higher first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        return rules
    
    @property
    def current_state(self) -> SaleState:
        return self._current_state
    
    @property
    def current_state_name(self) -> str:
        return self._current_state.value
    
    @property
    def state_duration(self) -> float:
        """Duration in current state (seconds)"""
        return time.time() - self._state_entered_at
    
    @property
    def state_config(self) -> StateConfig:
        """Get config for current state"""
        return STATE_CONFIGS.get(self._current_state, StateConfig(name="UNKNOWN"))
    
    def can_transition(self, trigger: str) -> bool:
        """Check if transition is possible with given trigger"""
        for rule in self._rules:
            if rule.from_state == self._current_state and rule.trigger == trigger:
                if rule.condition is None or rule.condition():
                    return True
        return False
    
    def transition(self, trigger: str, force: bool = False) -> bool:
        """
        Attempt state transition
        
        Args:
            trigger: Event that triggers transition
            force: Force transition even if conditions not met
            
        Returns:
            True if transition successful
        """
        
        # Find matching rule
        target_state = None
        
        for rule in self._rules:
            if rule.from_state == self._current_state and rule.trigger == trigger:
                if force or rule.condition is None or rule.condition():
                    target_state = rule.to_state
                    break
        
        if target_state is None:
            return False
        
        # Check min duration (unless forced)
        if not force:
            min_duration = self.state_config.min_duration
            if self.state_duration < min_duration:
                return False
        
        # Execute transition
        self._execute_transition(target_state, trigger)
        
        return True
    
    def force_state(self, state: SaleState, reason: str = "forced"):
        """Force set state (bypass rules)"""
        self._execute_transition(state, reason)
    
    def _execute_transition(self, new_state: SaleState, trigger: str):
        """Execute the state transition"""
        
        old_state = self._current_state
        now = time.time()
        
        # Save snapshot of old state
        snapshot = StateSnapshot(
            state=old_state,
            entered_at=self._state_entered_at,
            duration=now - self._state_entered_at,
            previous_state=self._previous_state,
            transition_count=self._transition_count,
            viewer_delta=self._current_viewer_count - self._viewer_count_at_enter
        )
        self._state_history.append(snapshot)
        
        # Update metrics for old state
        self._state_metrics[old_state]["duration"] += snapshot.duration
        
        # Transition
        self._previous_state = old_state
        self._current_state = new_state
        self._state_entered_at = now
        self._transition_count += 1
        self._viewer_count_at_enter = self._current_viewer_count
        
        # Callback
        if self.on_transition:
            self.on_transition(old_state, new_state, trigger)
        
        print(f"[STATE] {old_state.value} → {new_state.value} (trigger: {trigger})")
    
    def check_timeout(self) -> bool:
        """
        Check if current state has timed out
        
        Returns:
            True if timed out and transition executed
        """
        max_duration = self.state_config.max_duration
        
        if self.state_duration >= max_duration:
            # Auto transition
            success = self.transition("timeout")
            
            if success and self.on_state_timeout:
                self.on_state_timeout(self._previous_state, self._current_state)
            
            return success
        
        return False
    
    def update_viewer_count(self, count: int):
        """Update current viewer count"""
        self._current_viewer_count = count
    
    def notify_speak(self):
        """Notify that we just spoke"""
        self._state_metrics[self._current_state]["speak_count"] += 1
    
    def get_response_style(self) -> str:
        """Get recommended response style for current state"""
        return self.state_config.response_style
    
    def get_priority_intents(self) -> List[str]:
        """Get intents that have priority in current state"""
        return self.state_config.priority_intents
    
    def get_snapshot(self) -> StateSnapshot:
        """Get current state snapshot"""
        return StateSnapshot(
            state=self._current_state,
            entered_at=self._state_entered_at,
            duration=self.state_duration,
            previous_state=self._previous_state,
            transition_count=self._transition_count,
            viewer_delta=self._current_viewer_count - self._viewer_count_at_enter
        )
    
    def get_stats(self) -> dict:
        """Get state machine statistics"""
        return {
            "current_state": self._current_state.value,
            "state_duration": self.state_duration,
            "transition_count": self._transition_count,
            "state_metrics": {
                state.value: metrics 
                for state, metrics in self._state_metrics.items()
            },
            "history_length": len(self._state_history)
        }
    
    def reset(self):
        """Reset state machine to initial state"""
        self._current_state = SaleState.IDLE
        self._state_entered_at = time.time()
        self._previous_state = None
        self._transition_count = 0
        self._state_history.clear()
        
        for state in self._state_metrics:
            self._state_metrics[state] = {"speak_count": 0, "duration": 0.0}


# Singleton instance
_state_machine: Optional[SaleStateMachine] = None


def get_state_machine() -> SaleStateMachine:
    """Get singleton state machine instance"""
    global _state_machine
    
    if _state_machine is None:
        _state_machine = SaleStateMachine()
    
    return _state_machine
