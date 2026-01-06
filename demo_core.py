"""
demo_core.py
Demo để test Live Brain + State Machine + Observability
"""

import time
import random
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    LiveBrain, BrainInput, Action,
    SaleStateMachine, SaleState,
    MetricsCollector, StructuredLogger,
    get_brain, get_state_machine, get_metrics, get_logger
)


def simulate_comment() -> dict:
    """Simulate random comment"""
    
    intents = [
        ("Xin chào mọi người!", "greeting"),
        ("Sản phẩm này giá bao nhiêu?", "price_question"),
        ("Có ship COD không?", "product_question"),
        ("Cảm ơn bạn!", "thanks"),
        ("Sản phẩm này có tốt không?", "product_question"),
        ("Mình muốn mua", "purchase_intent"),
        ("Hello hello", "greeting"),
        ("Đẹp quá", "chitchat"),
        ("Cho xin link", "request"),
        ("Giao hàng mấy ngày?", "product_question"),
    ]
    
    text, intent = random.choice(intents)
    
    return {
        "comment_id": f"cmt_{random.randint(1000, 9999)}",
        "username": f"user_{random.randint(100, 999)}",
        "comment_text": text,
        "intent": intent,
        "viewer_count": random.randint(50, 300),
        "is_follower": random.random() > 0.5,
        "is_subscriber": random.random() > 0.8,
    }


def main():
    print("=" * 60)
    print("🧠 CORE MODULE DEMO")
    print("   Live Brain + State Machine + Observability")
    print("=" * 60)
    print()
    
    # Initialize components
    brain = get_brain()
    state_machine = get_state_machine()
    metrics = get_metrics()
    logger = get_logger("demo")
    
    # Connect observability
    brain.on_decision = lambda inp, dec: metrics.log_decision(dec)
    state_machine.on_transition = lambda f, t, tr: logger.log_state_transition(f.value, t.value, tr)
    
    logger.log_session_start(mode="demo")
    
    print("\n📊 Starting simulation...")
    print("   Press Ctrl+C to stop\n")
    
    try:
        for i in range(20):  # Simulate 20 comments
            print(f"\n--- Round {i+1} ---")
            
            # Simulate comment
            comment = simulate_comment()
            
            # Log comment
            logger.log_comment_received(
                comment["username"],
                comment["comment_text"],
                comment["intent"]
            )
            
            comment_event = metrics.log_comment(
                comment["username"],
                comment["comment_text"],
                comment["intent"]
            )
            
            # Update viewer count
            metrics.log_viewer_count(comment["viewer_count"])
            state_machine.update_viewer_count(comment["viewer_count"])
            
            # Create brain input
            brain_input = BrainInput(
                comment_id=comment["comment_id"],
                username=comment["username"],
                comment_text=comment["comment_text"],
                intent=comment["intent"],
                viewer_count=comment["viewer_count"],
                sale_state=state_machine.current_state_name,
                is_follower=comment["is_follower"],
                is_subscriber=comment["is_subscriber"]
            )
            
            # Get decision from brain
            decision = brain.decide(brain_input)
            
            logger.log_decision(
                decision.action.value,
                decision.reason.value,
                decision.priority,
                intent=comment["intent"]
            )
            
            # Act on decision
            if decision.action == Action.SPEAK:
                # Simulate speaking
                response = f"Cảm ơn {comment['username']}! " + random.choice([
                    "Sản phẩm giá 299k ạ!",
                    "Cảm ơn bạn đã quan tâm!",
                    "Dạ có ship COD ạ!",
                    "Mình inbox cho bạn nhé!",
                ])
                duration = random.uniform(2.0, 5.0)
                
                logger.log_speak_event(
                    response,
                    duration,
                    comment["intent"],
                    comment["viewer_count"]
                )
                
                metrics.log_speak(
                    response_text=response,
                    duration=duration,
                    intent=comment["intent"],
                    sale_state=state_machine.current_state_name,
                    viewer_count=comment["viewer_count"],
                    priority=decision.priority,
                    reason=decision.reason.value
                )
                
                metrics.log_response(comment_event, random.uniform(0.5, 2.0))
                
                brain.mark_spoken()
                state_machine.notify_speak()
                
                # Check state transition based on intent
                if comment["intent"] == "price_question":
                    state_machine.transition("price_question")
                elif comment["intent"] == "product_question":
                    state_machine.transition("product_mention")
                elif comment["intent"] == "purchase_intent":
                    state_machine.transition("purchase_intent")
            
            # Check state timeout
            state_machine.check_timeout()
            
            # Wait a bit
            time.sleep(0.5)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopped by user")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SESSION SUMMARY")
    print("=" * 60)
    
    stats = metrics.get_realtime_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n📈 Speak Interval Stats:")
    interval_stats = metrics.get_speak_interval_stats()
    for key, value in interval_stats.items():
        print(f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}")
    
    print("\n🔄 State Machine Stats:")
    sm_stats = state_machine.get_stats()
    print(f"  Current State: {sm_stats['current_state']}")
    print(f"  Transitions: {sm_stats['transition_count']}")
    
    print("\n🧠 Brain Stats:")
    brain_stats = brain.get_stats()
    for key, value in brain_stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    # Export metrics
    metrics.export_to_json("./demo_metrics.json")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    main()
