"""
states.py
State Machine Definitions cho Sale Flow
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from datetime import datetime


class SaleState(Enum):
    """
    Các trạng thái trong Sale Flow
    
    Flow cơ bản:
    IDLE → WARM_UP → INTEREST → PRICE → CTA → COOLDOWN → IDLE
    """
    
    IDLE = "IDLE"           # Chưa có hoạt động sale
    WARM_UP = "WARM_UP"     # Làm nóng, tạo engagement
    INTEREST = "INTEREST"   # Tạo hứng thú với sản phẩm
    PRICE = "PRICE"         # Đề cập giá
    CTA = "CTA"             # Call to action (mua ngay!)
    COOLDOWN = "COOLDOWN"   # Nghỉ sau CTA, tránh pushy
    
    # Special states
    HANDLING_QUESTION = "HANDLING_QUESTION"  # Đang trả lời câu hỏi
    CRISIS = "CRISIS"       # Xử lý complaint/negative


@dataclass
class StateConfig:
    """Configuration cho mỗi state"""
    
    name: str
    min_duration: float = 0.0       # Minimum time in this state (seconds)
    max_duration: float = 300.0     # Maximum time before auto-transition (seconds)
    
    # Allowed intents in this state (priority boost)
    priority_intents: List[str] = field(default_factory=list)
    
    # Response templates/styles for this state
    response_style: str = "neutral"  # neutral, enthusiastic, urgent, calm
    
    # Metrics
    target_metrics: Dict[str, float] = field(default_factory=dict)


# Default state configurations
STATE_CONFIGS: Dict[SaleState, StateConfig] = {
    SaleState.IDLE: StateConfig(
        name="IDLE",
        min_duration=0,
        max_duration=60,  # Auto warm-up after 60s
        priority_intents=["greeting", "chitchat"],
        response_style="friendly"
    ),
    
    SaleState.WARM_UP: StateConfig(
        name="WARM_UP", 
        min_duration=30,
        max_duration=120,
        priority_intents=["greeting", "chitchat", "question"],
        response_style="enthusiastic"
    ),
    
    SaleState.INTEREST: StateConfig(
        name="INTEREST",
        min_duration=45,
        max_duration=180,
        priority_intents=["product_question", "question"],
        response_style="informative"
    ),
    
    SaleState.PRICE: StateConfig(
        name="PRICE",
        min_duration=20,
        max_duration=90,
        priority_intents=["price_question", "purchase_intent"],
        response_style="value_focused"
    ),
    
    SaleState.CTA: StateConfig(
        name="CTA",
        min_duration=15,
        max_duration=45,
        priority_intents=["purchase_intent"],
        response_style="urgent"
    ),
    
    SaleState.COOLDOWN: StateConfig(
        name="COOLDOWN",
        min_duration=60,
        max_duration=120,
        priority_intents=["thanks", "chitchat"],
        response_style="calm"
    ),
    
    SaleState.HANDLING_QUESTION: StateConfig(
        name="HANDLING_QUESTION",
        min_duration=0,
        max_duration=60,
        priority_intents=["question", "product_question", "price_question"],
        response_style="helpful"
    ),
    
    SaleState.CRISIS: StateConfig(
        name="CRISIS",
        min_duration=0,
        max_duration=120,
        priority_intents=["complaint"],
        response_style="empathetic"
    )
}


@dataclass
class StateSnapshot:
    """Snapshot của state tại một thời điểm"""
    
    state: SaleState
    entered_at: float           # Timestamp khi enter state
    duration: float = 0.0       # Duration in current state
    previous_state: Optional[SaleState] = None
    transition_count: int = 0   # Số lần transition trong session
    
    # Metrics trong state này
    speak_count: int = 0
    response_count: int = 0
    viewer_delta: int = 0       # Viewer change since entering state
    
    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "entered_at": self.entered_at,
            "duration": self.duration,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "transition_count": self.transition_count,
            "speak_count": self.speak_count,
            "response_count": self.response_count,
            "viewer_delta": self.viewer_delta
        }
