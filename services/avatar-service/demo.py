"""
demo.py
Demo script để xem 2D Vtuber Avatar render
"""

import asyncio
import math
import time
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from renderer import VtuberRenderer, Expression

try:
    from PIL import Image
    import tkinter as tk
    from PIL import ImageTk
    HAS_TK = True
except ImportError:
    HAS_TK = False


class AvatarDemo:
    """Demo window để xem avatar animation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.renderer = VtuberRenderer(config)
        self.running = False
        
        # Tkinter window
        self.root = None
        self.canvas = None
        self.photo = None
        
        # Animation state
        self.is_speaking = False
        self.current_expression = Expression.NEUTRAL
        self.mouth_value = 0.0
    
    def run(self):
        """Run demo window"""
        if not HAS_TK:
            print("❌ Tkinter not available. Run: pip install tk")
            return
        
        # Create window
        self.root = tk.Tk()
        self.root.title("🎭 2D Vtuber Avatar Demo")
        self.root.configure(bg='#1a1a2e')
        
        # Main frame
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(padx=20, pady=20)
        
        # Title
        title = tk.Label(
            main_frame, 
            text="2D Vtuber Avatar Preview",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#1a1a2e'
        )
        title.pack(pady=(0, 10))
        
        # Canvas for avatar
        canvas_size = max(self.config.AVATAR_WIDTH, self.config.AVATAR_HEIGHT)
        self.canvas = tk.Canvas(
            main_frame,
            width=canvas_size,
            height=canvas_size,
            bg='#16213e',
            highlightthickness=2,
            highlightbackground='#0f3460'
        )
        self.canvas.pack(pady=10)
        
        # Control frame
        control_frame = tk.Frame(main_frame, bg='#1a1a2e')
        control_frame.pack(pady=10, fill='x')
        
        # Speaking toggle
        self.speak_btn = tk.Button(
            control_frame,
            text="🗣️ Start Speaking",
            command=self.toggle_speaking,
            font=('Arial', 11),
            bg='#e94560',
            fg='white',
            activebackground='#ff6b6b',
            width=15
        )
        self.speak_btn.pack(side='left', padx=5)
        
        # Expression buttons frame
        expr_frame = tk.Frame(main_frame, bg='#1a1a2e')
        expr_frame.pack(pady=10)
        
        tk.Label(
            expr_frame, 
            text="Expressions:",
            fg='white',
            bg='#1a1a2e',
            font=('Arial', 10)
        ).pack(side='left', padx=5)
        
        expressions = [
            ("😐", Expression.NEUTRAL),
            ("😊", Expression.HAPPY),
            ("😢", Expression.SAD),
            ("🤔", Expression.THINKING),
            ("😲", Expression.SURPRISED),
        ]
        
        for emoji, expr in expressions:
            btn = tk.Button(
                expr_frame,
                text=emoji,
                command=lambda e=expr: self.set_expression(e),
                font=('Arial', 14),
                width=3,
                bg='#0f3460',
                fg='white',
                activebackground='#533483'
            )
            btn.pack(side='left', padx=2)
        
        # Mouth slider
        slider_frame = tk.Frame(main_frame, bg='#1a1a2e')
        slider_frame.pack(pady=10, fill='x')
        
        tk.Label(
            slider_frame,
            text="👄 Mouth:",
            fg='white',
            bg='#1a1a2e',
            font=('Arial', 10)
        ).pack(side='left', padx=5)
        
        self.mouth_slider = tk.Scale(
            slider_frame,
            from_=0,
            to=100,
            orient='horizontal',
            command=self.on_mouth_change,
            bg='#0f3460',
            fg='white',
            highlightthickness=0,
            troughcolor='#16213e',
            length=200
        )
        self.mouth_slider.pack(side='left', padx=5, fill='x', expand=True)
        
        # Info label
        self.info_label = tk.Label(
            main_frame,
            text="FPS: 30 | Resolution: 512x512",
            fg='#888',
            bg='#1a1a2e',
            font=('Arial', 9)
        )
        self.info_label.pack(pady=5)
        
        # Start animation loop
        self.running = True
        self.animate()
        
        # Run
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def toggle_speaking(self):
        """Toggle speaking animation"""
        self.is_speaking = not self.is_speaking
        
        if self.is_speaking:
            self.speak_btn.config(text="🔇 Stop Speaking", bg='#533483')
        else:
            self.speak_btn.config(text="🗣️ Start Speaking", bg='#e94560')
            self.mouth_value = 0.0
    
    def set_expression(self, expression: Expression):
        """Set avatar expression"""
        self.current_expression = expression
    
    def on_mouth_change(self, value):
        """Handle mouth slider change"""
        if not self.is_speaking:
            self.mouth_value = int(value) / 100.0
    
    def animate(self):
        """Animation loop"""
        if not self.running:
            return
        
        # Update mouth if speaking (simulate)
        if self.is_speaking:
            # Simulate speech with sine wave
            t = time.time() * 8
            self.mouth_value = (math.sin(t) + 1) / 2 * 0.7 + 0.1
            # Add some randomness
            self.mouth_value += math.sin(t * 2.7) * 0.15
            self.mouth_value = max(0, min(1, self.mouth_value))
        
        # Update renderer state
        self.renderer.update_state(
            mouth_open=self.mouth_value,
            expression=self.current_expression,
            is_speaking=self.is_speaking
        )
        
        # Render frame
        frame = self.renderer.render_frame()
        
        if frame:
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(frame)
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(
                self.config.AVATAR_WIDTH // 2,
                self.config.AVATAR_HEIGHT // 2,
                image=self.photo
            )
        
        # Schedule next frame
        self.root.after(33, self.animate)  # ~30 FPS
    
    def on_close(self):
        """Handle window close"""
        self.running = False
        self.root.destroy()


def main():
    print("🎭 Starting 2D Vtuber Avatar Demo...")
    print("=" * 40)
    
    config = Config()
    config.AVATAR_WIDTH = 512
    config.AVATAR_HEIGHT = 512
    
    demo = AvatarDemo(config)
    demo.run()


if __name__ == "__main__":
    main()
