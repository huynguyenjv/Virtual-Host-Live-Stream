"""
metrics.py
Observability - Metrics Collection
Thu thập và tracking tất cả metrics quan trọng
"""

import time
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from collections import deque
from threading import Lock
import statistics


@dataclass
class SpeakEvent:
    """Event khi avatar nói"""
    timestamp: float
    response_text: str
    duration: float             # Audio duration
    intent: str
    sale_state: str
    viewer_count: int
    priority: int
    reason: str
    
    # Calculated later
    viewer_delta: int = 0       # Viewer change after speak
    time_since_last: float = 0  # Time since last speak


@dataclass 
class CommentEvent:
    """Event khi nhận comment"""
    timestamp: float
    username: str
    text: str
    intent: str
    was_responded: bool = False
    response_time: float = 0.0  # Time to respond (if responded)


@dataclass
class MetricsSummary:
    """Summary của metrics trong một khoảng thời gian"""
    period_start: float
    period_end: float
    
    # Speak metrics
    total_speaks: int = 0
    avg_speak_interval: float = 0.0
    min_speak_interval: float = 0.0
    max_speak_interval: float = 0.0
    
    # Response metrics
    total_comments: int = 0
    responded_comments: int = 0
    response_rate: float = 0.0      # % comments được respond
    avg_response_time: float = 0.0
    
    # Sale metrics
    sale_phrase_count: int = 0
    sale_phrase_rate: float = 0.0   # % speaks là sale phrase
    
    # Viewer metrics
    avg_viewer_count: int = 0
    max_viewer_count: int = 0
    min_viewer_count: int = 0
    viewer_delta_total: int = 0     # Total viewer change
    
    # State metrics
    state_durations: Dict[str, float] = field(default_factory=dict)
    state_transitions: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


class MetricsCollector:
    """
    📊 OBSERVABILITY - Metrics Collector
    
    Thu thập tất cả metrics cần thiết để đánh giá và tối ưu:
    - Time giữa 2 câu nói
    - % comment được trả lời
    - % sale phrase
    - Viewer delta sau mỗi câu nói
    """
    
    def __init__(self, config: dict = None):
        self.config = config or self._default_config()
        
        # Events storage (deque for memory efficiency)
        self._speak_events: deque = deque(maxlen=1000)
        self._comment_events: deque = deque(maxlen=5000)
        self._viewer_history: deque = deque(maxlen=1000)
        
        # Current session
        self._session_start = time.time()
        self._last_speak_time = 0.0
        
        # Real-time counters
        self._counters = {
            "total_speaks": 0,
            "total_comments": 0,
            "responded_comments": 0,
            "sale_phrases": 0,
        }
        
        # Thread safety
        self._lock = Lock()
        
        # Callbacks for real-time updates
        self.on_metric_update: Optional[Callable] = None
        
        # Sale phrase patterns
        self._sale_patterns = [
            "mua ngay", "đặt hàng", "giá", "khuyến mãi", "giảm giá",
            "flash sale", "số lượng có hạn", "link", "inbox", "dm"
        ]
    
    def _default_config(self) -> dict:
        return {
            "viewer_sample_interval": 10.0,  # Sample viewer count every N seconds
            "summary_interval": 300.0,       # Generate summary every 5 minutes
            "alert_thresholds": {
                "max_speak_interval": 30.0,   # Alert if silent too long
                "min_response_rate": 0.1,     # Alert if response rate < 10%
                "viewer_drop": 0.2,           # Alert if viewer drop > 20%
            }
        }
    
    # ==================== LOGGING METHODS ====================
    
    def log_speak(self, 
                  response_text: str,
                  duration: float,
                  intent: str,
                  sale_state: str,
                  viewer_count: int,
                  priority: int = 5,
                  reason: str = "") -> SpeakEvent:
        """Log một speak event"""
        
        now = time.time()
        time_since_last = now - self._last_speak_time if self._last_speak_time > 0 else 0
        
        event = SpeakEvent(
            timestamp=now,
            response_text=response_text,
            duration=duration,
            intent=intent,
            sale_state=sale_state,
            viewer_count=viewer_count,
            priority=priority,
            reason=reason,
            time_since_last=time_since_last
        )
        
        with self._lock:
            self._speak_events.append(event)
            self._counters["total_speaks"] += 1
            
            # Check if sale phrase
            if self._is_sale_phrase(response_text):
                self._counters["sale_phrases"] += 1
            
            self._last_speak_time = now
        
        # Log to console
        self._log_to_console("SPEAK", {
            "intent": intent,
            "state": sale_state,
            "viewers": viewer_count,
            "interval": f"{time_since_last:.1f}s"
        })
        
        # Callback
        if self.on_metric_update:
            self.on_metric_update("speak", event)
        
        return event
    
    def log_comment(self,
                    username: str,
                    text: str,
                    intent: str) -> CommentEvent:
        """Log một comment event"""
        
        event = CommentEvent(
            timestamp=time.time(),
            username=username,
            text=text,
            intent=intent
        )
        
        with self._lock:
            self._comment_events.append(event)
            self._counters["total_comments"] += 1
        
        return event
    
    def log_response(self, comment_event: CommentEvent, response_time: float):
        """Mark comment as responded"""
        
        comment_event.was_responded = True
        comment_event.response_time = response_time
        
        with self._lock:
            self._counters["responded_comments"] += 1
    
    def log_viewer_count(self, count: int):
        """Log viewer count"""
        
        with self._lock:
            self._viewer_history.append({
                "timestamp": time.time(),
                "count": count
            })
        
        # Check for significant change
        if len(self._viewer_history) >= 2:
            prev = self._viewer_history[-2]["count"]
            if prev > 0:
                delta_pct = (count - prev) / prev
                
                if abs(delta_pct) > 0.1:  # > 10% change
                    self._log_to_console("VIEWER_CHANGE", {
                        "from": prev,
                        "to": count,
                        "delta": f"{delta_pct:+.1%}"
                    })
    
    def log_decision(self, decision: Any):
        """Log brain decision"""
        
        self._log_to_console("DECISION", {
            "action": decision.action.value if hasattr(decision.action, 'value') else str(decision.action),
            "reason": decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason),
            "priority": decision.priority
        })
    
    def log_state_transition(self, from_state: str, to_state: str, trigger: str):
        """Log state machine transition"""
        
        self._log_to_console("STATE_TRANSITION", {
            "from": from_state,
            "to": to_state,
            "trigger": trigger
        })
    
    # ==================== QUERY METHODS ====================
    
    def get_speak_interval_stats(self, window_seconds: float = 300) -> dict:
        """Get statistics về khoảng cách giữa các câu nói"""
        
        cutoff = time.time() - window_seconds
        intervals = []
        
        with self._lock:
            events = [e for e in self._speak_events if e.timestamp > cutoff]
        
        for event in events:
            if event.time_since_last > 0:
                intervals.append(event.time_since_last)
        
        if not intervals:
            return {"avg": 0, "min": 0, "max": 0, "count": 0}
        
        return {
            "avg": statistics.mean(intervals),
            "min": min(intervals),
            "max": max(intervals),
            "std": statistics.stdev(intervals) if len(intervals) > 1 else 0,
            "count": len(intervals)
        }
    
    def get_response_rate(self, window_seconds: float = 300) -> float:
        """Get % comments được trả lời"""
        
        cutoff = time.time() - window_seconds
        
        with self._lock:
            events = [e for e in self._comment_events if e.timestamp > cutoff]
        
        if not events:
            return 0.0
        
        responded = sum(1 for e in events if e.was_responded)
        return responded / len(events)
    
    def get_sale_phrase_rate(self, window_seconds: float = 300) -> float:
        """Get % câu nói là sale phrase"""
        
        cutoff = time.time() - window_seconds
        
        with self._lock:
            events = [e for e in self._speak_events if e.timestamp > cutoff]
        
        if not events:
            return 0.0
        
        sale_count = sum(1 for e in events if self._is_sale_phrase(e.response_text))
        return sale_count / len(events)
    
    def get_viewer_delta_after_speak(self, window_seconds: float = 30) -> List[dict]:
        """Get viewer change sau mỗi câu nói"""
        
        results = []
        
        with self._lock:
            for event in self._speak_events:
                # Find viewer count right after speak
                viewer_after = None
                for vh in self._viewer_history:
                    if vh["timestamp"] > event.timestamp and \
                       vh["timestamp"] < event.timestamp + window_seconds:
                        viewer_after = vh["count"]
                        break
                
                if viewer_after is not None:
                    delta = viewer_after - event.viewer_count
                    results.append({
                        "speak_time": event.timestamp,
                        "intent": event.intent,
                        "viewer_before": event.viewer_count,
                        "viewer_after": viewer_after,
                        "delta": delta
                    })
        
        return results
    
    def get_summary(self, window_seconds: float = 300) -> MetricsSummary:
        """Get summary của metrics trong window"""
        
        now = time.time()
        cutoff = now - window_seconds
        
        with self._lock:
            speak_events = [e for e in self._speak_events if e.timestamp > cutoff]
            comment_events = [e for e in self._comment_events if e.timestamp > cutoff]
            viewer_data = [v for v in self._viewer_history if v["timestamp"] > cutoff]
        
        # Calculate speak metrics
        intervals = [e.time_since_last for e in speak_events if e.time_since_last > 0]
        
        # Calculate response metrics
        responded = [e for e in comment_events if e.was_responded]
        response_times = [e.response_time for e in responded if e.response_time > 0]
        
        # Calculate viewer metrics
        viewer_counts = [v["count"] for v in viewer_data]
        
        summary = MetricsSummary(
            period_start=cutoff,
            period_end=now,
            
            # Speak
            total_speaks=len(speak_events),
            avg_speak_interval=statistics.mean(intervals) if intervals else 0,
            min_speak_interval=min(intervals) if intervals else 0,
            max_speak_interval=max(intervals) if intervals else 0,
            
            # Response
            total_comments=len(comment_events),
            responded_comments=len(responded),
            response_rate=len(responded) / len(comment_events) if comment_events else 0,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            
            # Sale
            sale_phrase_count=sum(1 for e in speak_events if self._is_sale_phrase(e.response_text)),
            sale_phrase_rate=self.get_sale_phrase_rate(window_seconds),
            
            # Viewer
            avg_viewer_count=int(statistics.mean(viewer_counts)) if viewer_counts else 0,
            max_viewer_count=max(viewer_counts) if viewer_counts else 0,
            min_viewer_count=min(viewer_counts) if viewer_counts else 0,
        )
        
        return summary
    
    def get_realtime_stats(self) -> dict:
        """Get real-time statistics"""
        
        session_duration = time.time() - self._session_start
        
        with self._lock:
            counters = self._counters.copy()
            last_viewer = self._viewer_history[-1]["count"] if self._viewer_history else 0
        
        return {
            "session_duration": session_duration,
            "total_speaks": counters["total_speaks"],
            "total_comments": counters["total_comments"],
            "response_rate": counters["responded_comments"] / counters["total_comments"] 
                            if counters["total_comments"] > 0 else 0,
            "sale_phrase_rate": counters["sale_phrases"] / counters["total_speaks"]
                               if counters["total_speaks"] > 0 else 0,
            "current_viewers": last_viewer,
            "time_since_speak": time.time() - self._last_speak_time if self._last_speak_time > 0 else 0
        }
    
    # ==================== HELPER METHODS ====================
    
    def _is_sale_phrase(self, text: str) -> bool:
        """Check if text contains sale phrases"""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self._sale_patterns)
    
    def _log_to_console(self, event_type: str, data: dict):
        """Log to console với format chuẩn"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        data_str = " | ".join(f"{k}={v}" for k, v in data.items())
        print(f"[{timestamp}] 📊 {event_type}: {data_str}")
    
    def export_to_json(self, filepath: str):
        """Export all metrics to JSON file"""
        
        with self._lock:
            data = {
                "session_start": self._session_start,
                "export_time": time.time(),
                "counters": self._counters,
                "speak_events": [asdict(e) for e in self._speak_events],
                "comment_events": [asdict(e) for e in self._comment_events],
                "viewer_history": list(self._viewer_history),
                "summary": self.get_summary().to_dict()
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] Metrics exported to {filepath}")
    
    def reset(self):
        """Reset all metrics"""
        
        with self._lock:
            self._speak_events.clear()
            self._comment_events.clear()
            self._viewer_history.clear()
            self._session_start = time.time()
            self._last_speak_time = 0.0
            
            for key in self._counters:
                self._counters[key] = 0


# Singleton instance
_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get singleton metrics instance"""
    global _metrics
    
    if _metrics is None:
        _metrics = MetricsCollector()
    
    return _metrics
