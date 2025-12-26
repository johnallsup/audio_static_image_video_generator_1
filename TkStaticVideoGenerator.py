#!/usr/bin/env python3

import os
import sys
import math
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk

class MediaProcessor:
    def __init__(self):
        # Trigger the search for binaries immediately
        self.ffmpeg_path = self.ensure_binary("ffmpeg")
        self.ffprobe_path = self.ensure_binary("ffprobe")
        
        if not self.ffmpeg_path or not self.ffprobe_path:
            messagebox.showerror("Dependency Error", 
                "Could not locate ffmpeg or ffprobe.\n\n"
                "Searched in: System PATH, ~/bin, and /opt/local/bin.\n"
                "Please install FFmpeg to continue.")
            sys.exit(1)

    def ensure_binary(self, binary):
        """Tries to find a binary, expanding the search to specific Mac paths if needed."""
        # 1. Check standard PATH
        found_path = shutil.which(binary)
        if found_path:
            return found_path

        # 2. Check extra paths requested
        extra_paths = [
            os.path.expanduser("~/bin"),
            "/opt/local/bin",
            "/opt/homebrew/bin",
            "/usr/local/bin"
        ]
        
        for p in extra_paths:
            candidate = os.path.join(p, binary)
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                # Update environment so subprocess can use it seamlessly
                os.environ["PATH"] += os.pathsep + p
                return candidate
        
        return None

    def get_audio_duration(self, audio_path):
        cmd = [self.ffprobe_path, '-v', 'error', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return float(result.stdout.strip())

    def process_video_stream(self, audio_path, image_path, output_path, resolution, seed_setting, log_callback):
        w, h = resolution
        img = Image.open(image_path)
        img.thumbnail((w, h), Image.Resampling.LANCZOS)
        new_img = Image.new("RGB", (w, h), (0, 0, 0))
        new_img.paste(img, ((w - img.size[0]) // 2, (h - img.size[1]) // 2))
        
        temp_img = "temp_resized.png"
        new_img.save(temp_img)

        audio_duration = self.get_audio_duration(audio_path)
        
        cmd = [
            self.ffmpeg_path, '-y',
            '-loop', '1', '-t', str(audio_duration), '-i', temp_img,
            '-i', audio_path,
            '-c:v', 'libx264', '-tune', 'stillimage', '-preset', 'veryfast',
            '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', '-shortest', output_path
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                   text=True, bufsize=1, universal_newlines=True)

        for line in process.stdout:
            log_callback(line)
        
        process.wait()
        if os.path.exists(temp_img): os.remove(temp_img)
        if process.returncode != 0: raise Exception("FFmpeg rendering failed.")

class VideoMakerApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Static Video Generator")
        self.geometry("950x900")
        
        self.processor = MediaProcessor()
        self.entries = {}
        self.last_output_path = None
        self.res_var = tk.StringVar(value="1920x1080")
        self.transpose_var = tk.BooleanVar(value=False)
        self.seed_var = tk.StringVar(value="20s")
        self._setup_ui()

    def _setup_ui(self):
        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.columnconfigure(1, weight=1)

        fields = [("Audio File:", "audio"), ("Image File:", "image"), 
                  ("Output Dir:", "out_dir"), ("Output Name:", "out_name")]
        
        for i, (label, key) in enumerate(fields):
            ttk.Label(self.main_frame, text=label).grid(row=i, column=0, sticky="w", pady=2)
            ent = ttk.Entry(self.main_frame)
            ent.grid(row=i, column=1, sticky="ew", padx=10, pady=2)
            self.entries[key] = ent
            ttk.Button(self.main_frame, text="Clear", width=8, 
                       command=lambda k=key: self.clear_field(k)).grid(row=i, column=2)

        settings_frame = ttk.LabelFrame(self.main_frame, text=" Video Settings ", padding=10)
        settings_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=15)
        
        ttk.Label(settings_frame, text="Resolution:").pack(side="left")
        res_opts = ["1920x1080", "1280x720", "854x480", "640x480", "640x640", "480x480"]
        ttk.OptionMenu(settings_frame, self.res_var, res_opts[0], *res_opts).pack(side="left", padx=5)
        ttk.Checkbutton(settings_frame, text="Transpose", variable=self.transpose_var).pack(side="left", padx=10)
        
        ttk.Label(settings_frame, text="Seed:").pack(side="left")
        seed_opts = ["Auto", "10s", "20s", "1minute"]
        ttk.OptionMenu(settings_frame, self.seed_var, seed_opts[2], *seed_opts).pack(side="left", padx=5)

        self.preview_label = ttk.Label(self.main_frame, text="No Image Selected", relief="sunken", anchor="center")
        self.preview_label.grid(row=5, column=0, columnspan=3, pady=10, sticky="nsew")
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.main_frame, textvariable=self.status_var, font=('Arial', 10, 'bold')).grid(row=6, column=0, columnspan=3, sticky="w")
        
        self.log_text = tk.Text(self.main_frame, height=12, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.log_text.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=5)
        
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=10)
        self.btn_gen = ttk.Button(btn_frame, text="Generate Video", command=self.start_generation)
        self.btn_gen.pack(side="left", padx=5)
        self.btn_reveal = ttk.Button(btn_frame, text="Reveal in Finder", command=self.reveal_in_finder, state="disabled")
        self.btn_reveal.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side="left", padx=5)

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        path = event.data.strip('{}')
        if os.path.isdir(path):
            self._set_entry("out_dir", path)
        elif path.lower().endswith(('.mp4', '.mkv', '.mov')):
            self._set_entry("out_dir", os.path.dirname(path))
            self._set_entry("out_name", os.path.basename(path))
        elif path.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
            self._set_entry("audio", path)
            if not self.entries["out_name"].get():
                base = os.path.splitext(os.path.basename(path))[0]
                self._set_entry("out_name", f"{base}.mp4")
                self._set_entry("out_dir", os.path.dirname(path))
        elif path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            self._set_entry("image", path)
            self.update_preview(path)

    def _set_entry(self, key, value):
        self.entries[key].delete(0, "end")
        self.entries[key].insert(0, value)

    def clear_field(self, key):
        self.entries[key].delete(0, "end")
        if key == "image": self.preview_label.config(image="", text="No Image Selected")

    def clear_all(self):
        for key in self.entries: self.clear_field(key)
        self.log_text.delete("1.0", "end")
        self.status_var.set("Ready")
        self.btn_reveal.config(state="disabled")

    def reveal_in_finder(self):
        if self.last_output_path and os.path.exists(self.last_output_path):
            subprocess.run(["open", "-R", self.last_output_path])

    def update_preview(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((300, 150))
            self.photo = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.photo, text="")
        except: pass

    def start_generation(self):
        audio = self.entries["audio"].get()
        image = self.entries["image"].get()
        out_dir = self.entries["out_dir"].get()
        out_name = self.entries["out_name"].get()

        if not all([audio, image, out_dir, out_name]):
            messagebox.showerror("Error", "All fields are required.")
            return

        # Ensure .mp4 extension
        if not out_name.lower().endswith(".mp4"):
            out_name += ".mp4"
            self._set_entry("out_name", out_name)

        res_str = self.res_var.get()
        w, h = map(int, res_str.split('x'))
        if self.transpose_var.get(): w, h = h, w
        
        self.last_output_path = os.path.join(out_dir, out_name)
        self.btn_gen.config(state="disabled")
        self.btn_reveal.config(state="disabled")
        
        thread = threading.Thread(target=self.run_ffmpeg_thread, args=(audio, image, self.last_output_path, (w, h), self.seed_var.get()))
        thread.start()

    def run_ffmpeg_thread(self, audio, image, output, res, seed):
        try:
            self.status_var.set("Rendering...")
            self.processor.process_video_stream(audio, image, output, res, seed, lambda m: (self.log_text.insert("end", m), self.log_text.see("end")))
            self.status_var.set("Success!")
            self.btn_reveal.config(state="normal")
            messagebox.showinfo("Complete", f"Video saved to:\n{output}")
        except Exception as e:
            self.status_var.set("Error")
            self.log_text.insert("end", f"\nERROR: {e}")
        finally:
            self.btn_gen.config(state="normal")

if __name__ == "__main__":
    app = VideoMakerApp()
    app.mainloop()
