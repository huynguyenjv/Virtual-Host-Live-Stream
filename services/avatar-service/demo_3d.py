"""
demo_3d.py
Demo 3D Talking Head - Xem preview AI avatar người thật
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from talking_head import (
    TalkingHeadConfig, 
    TalkingHeadRenderer, 
    TalkingHeadEngine
)

try:
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox
    from PIL import Image, ImageTk
    HAS_TK = True
except ImportError:
    HAS_TK = False


class TalkingHeadDemo:
    """Demo window cho 3D Talking Head"""
    
    def __init__(self):
        self.root = None
        self.config = TalkingHeadConfig()
        self.renderer = None
        self.source_image = None
        self.photo = None
    
    def run(self):
        if not HAS_TK:
            print("❌ Tkinter not available")
            return
        
        self.root = tk.Tk()
        self.root.title("🎭 3D Talking Head Demo")
        self.root.configure(bg='#1a1a2e')
        self.root.geometry("600x700")
        
        # Main frame
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(padx=20, pady=20, fill='both', expand=True)
        
        # Title
        title = tk.Label(
            main_frame,
            text="🎭 AI Talking Head Avatar",
            font=('Arial', 18, 'bold'),
            fg='white',
            bg='#1a1a2e'
        )
        title.pack(pady=(0, 20))
        
        # Engine selection
        engine_frame = tk.Frame(main_frame, bg='#1a1a2e')
        engine_frame.pack(fill='x', pady=10)
        
        tk.Label(
            engine_frame,
            text="Engine:",
            fg='white',
            bg='#1a1a2e',
            font=('Arial', 11)
        ).pack(side='left', padx=5)
        
        self.engine_var = tk.StringVar(value="sadtalker")
        engines = [
            ("SadTalker", "sadtalker"),
            ("Wav2Lip", "wav2lip"),
            ("LivePortrait", "liveportrait"),
            ("D-ID API", "did"),
        ]
        
        for text, value in engines:
            rb = tk.Radiobutton(
                engine_frame,
                text=text,
                variable=self.engine_var,
                value=value,
                bg='#1a1a2e',
                fg='white',
                selectcolor='#0f3460',
                activebackground='#1a1a2e',
                font=('Arial', 10)
            )
            rb.pack(side='left', padx=10)
        
        # Image preview frame
        preview_frame = tk.Frame(main_frame, bg='#16213e', padx=10, pady=10)
        preview_frame.pack(fill='x', pady=15)
        
        tk.Label(
            preview_frame,
            text="📷 Source Image (Ảnh người thật)",
            fg='white',
            bg='#16213e',
            font=('Arial', 11, 'bold')
        ).pack(anchor='w')
        
        self.image_canvas = tk.Canvas(
            preview_frame,
            width=256,
            height=256,
            bg='#0f3460',
            highlightthickness=1,
            highlightbackground='#533483'
        )
        self.image_canvas.pack(pady=10)
        
        # Draw placeholder
        self.image_canvas.create_text(
            128, 128,
            text="Click để chọn ảnh",
            fill='#888',
            font=('Arial', 11)
        )
        self.image_canvas.bind("<Button-1>", self.select_image)
        
        btn_frame = tk.Frame(preview_frame, bg='#16213e')
        btn_frame.pack(fill='x')
        
        tk.Button(
            btn_frame,
            text="📂 Chọn ảnh",
            command=self.select_image,
            bg='#e94560',
            fg='white',
            font=('Arial', 10)
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame,
            text="📥 Tải ảnh mẫu",
            command=self.download_sample,
            bg='#0f3460',
            fg='white',
            font=('Arial', 10)
        ).pack(side='left', padx=5)
        
        # Audio selection
        audio_frame = tk.Frame(main_frame, bg='#16213e', padx=10, pady=10)
        audio_frame.pack(fill='x', pady=15)
        
        tk.Label(
            audio_frame,
            text="🔊 Audio Input",
            fg='white',
            bg='#16213e',
            font=('Arial', 11, 'bold')
        ).pack(anchor='w')
        
        self.audio_path_var = tk.StringVar(value="Chưa chọn audio")
        tk.Label(
            audio_frame,
            textvariable=self.audio_path_var,
            fg='#888',
            bg='#16213e',
            font=('Arial', 9)
        ).pack(anchor='w', pady=5)
        
        tk.Button(
            audio_frame,
            text="📂 Chọn Audio (.mp3, .wav)",
            command=self.select_audio,
            bg='#e94560',
            fg='white',
            font=('Arial', 10)
        ).pack(anchor='w')
        
        # Generate button
        self.generate_btn = tk.Button(
            main_frame,
            text="🎬 Generate Video",
            command=self.generate_video,
            bg='#533483',
            fg='white',
            font=('Arial', 14, 'bold'),
            width=20,
            height=2
        )
        self.generate_btn.pack(pady=20)
        
        # Status
        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.status_label = tk.Label(
            main_frame,
            textvariable=self.status_var,
            fg='#888',
            bg='#1a1a2e',
            font=('Arial', 10)
        )
        self.status_label.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=300
        )
        self.progress.pack(pady=10)
        
        # Setup instructions button
        tk.Button(
            main_frame,
            text="📖 Setup Instructions",
            command=self.show_setup,
            bg='#0f3460',
            fg='white',
            font=('Arial', 10)
        ).pack(pady=10)
        
        # Store paths
        self.audio_path = None
        self.image_path = None
        
        self.root.mainloop()
    
    def select_image(self, event=None):
        """Select source image"""
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.webp"),
            ("All files", "*.*")
        ]
        
        path = filedialog.askopenfilename(
            title="Chọn ảnh người thật",
            filetypes=filetypes
        )
        
        if path:
            self.image_path = path
            self.config.source_image = path
            
            # Show preview
            try:
                img = Image.open(path)
                img.thumbnail((256, 256))
                self.photo = ImageTk.PhotoImage(img)
                
                self.image_canvas.delete("all")
                self.image_canvas.create_image(128, 128, image=self.photo)
            except Exception as e:
                print(f"Error loading image: {e}")
    
    def select_audio(self):
        """Select audio file"""
        filetypes = [
            ("Audio files", "*.mp3 *.wav *.m4a *.ogg"),
            ("All files", "*.*")
        ]
        
        path = filedialog.askopenfilename(
            title="Chọn audio file",
            filetypes=filetypes
        )
        
        if path:
            self.audio_path = path
            self.audio_path_var.set(Path(path).name)
    
    def generate_video(self):
        """Generate talking head video"""
        if not self.image_path:
            messagebox.showerror("Error", "Vui lòng chọn ảnh nguồn!")
            return
        
        if not self.audio_path:
            messagebox.showerror("Error", "Vui lòng chọn audio!")
            return
        
        # Get engine
        engine_name = self.engine_var.get()
        engine_map = {
            "sadtalker": TalkingHeadEngine.SADTALKER,
            "wav2lip": TalkingHeadEngine.WAV2LIP,
            "liveportrait": TalkingHeadEngine.LIVEPORTRAIT,
            "did": TalkingHeadEngine.DID_API,
        }
        
        self.config.engine = engine_map.get(engine_name, TalkingHeadEngine.SADTALKER)
        self.config.source_image = self.image_path
        
        # Start generation
        self.progress.start()
        self.status_var.set(f"Đang generate với {engine_name}...")
        self.generate_btn.config(state='disabled')
        
        # Run in thread
        import threading
        thread = threading.Thread(target=self._run_generation)
        thread.start()
    
    def _run_generation(self):
        """Run generation in background"""
        try:
            renderer = TalkingHeadRenderer(self.config)
            
            # Run async in new loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            output_path = loop.run_until_complete(
                renderer.generate_video(self.audio_path)
            )
            
            loop.close()
            
            # Update UI
            self.root.after(0, lambda: self._on_complete(output_path))
            
        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))
    
    def _on_complete(self, output_path):
        """Handle completion"""
        self.progress.stop()
        self.generate_btn.config(state='normal')
        
        if output_path:
            self.status_var.set(f"✅ Done: {output_path}")
            messagebox.showinfo(
                "Success", 
                f"Video đã được tạo:\n{output_path}"
            )
            
            # Open output folder
            os.startfile(str(Path(output_path).parent))
        else:
            self.status_var.set("❌ Generation failed")
            messagebox.showerror(
                "Error",
                "Không thể tạo video. Kiểm tra engine đã được cài đặt chưa."
            )
    
    def _on_error(self, error):
        """Handle error"""
        self.progress.stop()
        self.generate_btn.config(state='normal')
        self.status_var.set(f"❌ Error: {error}")
        messagebox.showerror("Error", error)
    
    def show_setup(self):
        """Show setup instructions"""
        engine_name = self.engine_var.get()
        engine_map = {
            "sadtalker": TalkingHeadEngine.SADTALKER,
            "wav2lip": TalkingHeadEngine.WAV2LIP,
            "liveportrait": TalkingHeadEngine.LIVEPORTRAIT,
            "did": TalkingHeadEngine.DID_API,
        }
        
        engine = engine_map.get(engine_name, TalkingHeadEngine.SADTALKER)
        instructions = TalkingHeadRenderer.get_setup_instructions(engine)
        
        # Show in new window
        win = tk.Toplevel(self.root)
        win.title(f"Setup {engine_name}")
        win.geometry("600x400")
        win.configure(bg='#1a1a2e')
        
        text = tk.Text(
            win,
            bg='#0f3460',
            fg='white',
            font=('Consolas', 10),
            padx=10,
            pady=10
        )
        text.pack(fill='both', expand=True, padx=10, pady=10)
        text.insert('1.0', instructions)
        text.config(state='disabled')
    
    def download_sample(self):
        """Download sample face image"""
        messagebox.showinfo(
            "Hướng dẫn",
            "Để có kết quả tốt nhất:\n\n"
            "1. Dùng ảnh chân dung rõ nét\n"
            "2. Mặt nhìn thẳng camera\n"
            "3. Ánh sáng đều\n"
            "4. Nền đơn giản\n"
            "5. Resolution: 512x512 trở lên\n\n"
            "Có thể dùng ảnh AI generated từ:\n"
            "- thispersondoesnotexist.com\n"
            "- Stable Diffusion\n"
            "- Midjourney"
        )


def main():
    print("🎭 3D Talking Head Demo")
    print("=" * 40)
    
    demo = TalkingHeadDemo()
    demo.run()


if __name__ == "__main__":
    main()
