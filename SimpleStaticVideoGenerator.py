#!/usr/bin/env python3
import sys
import os
import math
import subprocess
import platform
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLineEdit, QLabel, 
                             QFileDialog, QProgressBar, QTextEdit, QComboBox, QCheckBox)
from PySide6.QtCore import QThread, Signal, Qt, QRect
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
from PIL import Image

class VideoWorker(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, audio, image, out_dir, out_name, res, seed_len, bitrate, no_clobber, is_portrait):
        super().__init__()
        self.audio = os.path.abspath(os.path.expanduser(audio))
        self.image = os.path.abspath(os.path.expanduser(image))
        self.out_dir = os.path.abspath(os.path.expanduser(out_dir))
        
        # Ensure .mp4 extension
        if "." not in out_name:
            out_name += ".mp4"
        self.out_name = out_name
        
        self.res_str = res
        self.seed_str = seed_len
        self.bitrate = bitrate
        self.no_clobber = no_clobber
        self.is_portrait = is_portrait

    def get_safe_path(self, directory, filename):
        base, ext = os.path.splitext(filename)
        path = os.path.join(directory, filename)
        if not self.no_clobber or not os.path.exists(path): 
            return path
        counter = 0
        while os.path.exists(path):
            path = os.path.join(directory, f"{base}-{counter:03d}{ext}")
            counter += 1
        return path

    def run(self):
        try:
            os.makedirs(self.out_dir, exist_ok=True)
            final_output = self.get_safe_path(self.out_dir, self.out_name)

            self.progress.emit("Analyzing audio duration...")
            duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.audio]
            audio_duration = float(subprocess.check_output(duration_cmd))

            with Image.open(self.image) as img:
                if self.res_str == "From Image":
                    w, h = img.size
                else:
                    match = re.match(r"(\d+)\s*[xX]\s*(\d+)", self.res_str)
                    if not match: raise ValueError("Invalid resolution format.")
                    w, h = int(match.group(1)), int(match.group(2))
                
                if self.is_portrait: w, h = h, w
                w, h = (w // 2) * 2, (h // 2) * 2
                
                img.thumbnail((w, h), Image.Resampling.LANCZOS)
                new_img = Image.new("RGB", (w, h), (0, 0, 0))
                offset = ((w - img.size[0]) // 2, (h - img.size[1]) // 2)
                new_img.paste(img, offset)
                resized_img_filename = "temp_resized_image.png"
                resized_img_path = os.path.join(self.out_dir,resized_img_filename)
                new_img.save(resized_img_path)

            s_len = 60
            if self.seed_str == "Guess":
                s_len = 10 if audio_duration < 60 else 60 if audio_duration < 600 else 240
            else:
                s_len = int(re.sub(r"[^\d]", "", self.seed_str))

            br_match = re.search(r"(\d+)", self.bitrate)
            final_bitrate = f"{br_match.group(1)}k"

            self.progress.emit(f"Encoding seed segment...")
            seed_clip_filename = "temp_seed.mp4"
            seed_clip = os.path.join(self.out_dir,seed_clip_filename)
            subprocess.run(['ffmpeg', '-y', '-loop', '1', '-i', resized_img_path, 
                    '-c:v', 'libx264', '-t', str(s_len), '-pix_fmt', 'yuv420p', 
                    '-vf', f'scale={w}:{h}', '-preset', 'veryfast', seed_clip], 
                check=True)

            self.progress.emit(f"Muxing final video ({final_bitrate})...")
            num_loops = math.ceil(audio_duration / s_len)
            concat_filename = "temp_list.txt"
            concat_file = os.path.join(self.out_dir,concat_filename)
            with open(concat_file, "w") as f:
                for _ in range(num_loops):
                    f.write(f"file '{os.path.abspath(seed_clip)}'\n")

            subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file, '-i', self.audio, 
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', final_bitrate, '-shortest', '-t', 
                    str(audio_duration), final_output], 
                check=True)

            for tmp in [resized_img_path, seed_clip, concat_file]:
                if os.path.exists(tmp): os.remove(tmp)
            self.finished.emit(True, final_output)
        except Exception as e:
            self.finished.emit(False, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Static Video Creator") ## Window Title
        self.setMinimumWidth(1050)
        self.setAcceptDrops(True)
        self.status_icon = None

        self.audio_exts = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.aif', '.aiff' }
        self.image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}

        # Main Widgets
        self.audio_input = QLineEdit()
        self.image_input = QLineEdit()
        self.dir_input = QLineEdit()
        self.filename_input = QLineEdit()
        self.image_input.textChanged.connect(self.update_preview)

        self.res_dropdown = QComboBox(); self.res_dropdown.setEditable(True)
        self.res_dropdown.addItems(["1920x1080", "1280x720", "854x480", "1080x1080", "640x640", "480x480", "From Image"]) ## Resolutions
        
        self.portrait_cb = QCheckBox("Portrait")
        self.seed_dropdown = QComboBox(); self.seed_dropdown.setEditable(True)
        self.seed_dropdown.addItems(["60s", "10s", "240s", "Guess"]) ## Seed Durations

        self.bitrate_dropdown = QComboBox(); self.bitrate_dropdown.setEditable(True)
        self.bitrate_dropdown.addItems(["128k", "192k", "256k", "320k"]) ## Bitrates

        self.no_clobber_cb = QCheckBox("No Clobber (don't overwrite existing files, append numbers like -003.mp4 as necessary)")
        self.no_clobber_cb.setChecked(True)
        
        self.preview_label = QLabel("No Image")
        self.preview_label.setFixedSize(300, 300)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px dashed #555; background: #111; color: #555; border-radius: 4px;")

        self.log_area = QTextEdit(); self.log_area.setReadOnly(True)
        self.progress_bar = QProgressBar()
        
        self.start_btn = QPushButton("Generate Video")
        self.open_folder_btn = QPushButton("Show in Folder")
        self.clear_all_btn = QPushButton("Clear All")
        self.open_folder_btn.setEnabled(False)
        
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # Left Side: Preview
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>PREVIEW</b>"))
        left.addWidget(self.preview_label)
        left.addStretch()
        
        # Right Side: Inputs
        right = QVBoxLayout()
        right.addLayout(self._create_row("Audio:", self.audio_input, self.browse_file))
        right.addLayout(self._create_row("Image:", self.image_input, self.browse_file))
        right.addLayout(self._create_row("Folder:", self.dir_input, self.browse_directory))
        right.addLayout(self._create_row("Output:", self.filename_input, None)) # File row with Clear button
        
        # Settings Row 1: Quality & Resolution
        settings_row = QHBoxLayout()
        settings_row.addWidget(QLabel("Bitrate:"))
        settings_row.addWidget(self.bitrate_dropdown)
        settings_row.addWidget(QLabel("Res:"))
        settings_row.addWidget(self.res_dropdown)
        settings_row.addWidget(self.portrait_cb)
        settings_row.addWidget(QLabel("Seed:"))
        settings_row.addWidget(self.seed_dropdown)
        right.addLayout(settings_row)

        right.addWidget(self.no_clobber_cb)
        
        # Buttons
        btns = QHBoxLayout()
        btns.addWidget(self.start_btn)
        btns.addWidget(self.open_folder_btn)
        btns.addWidget(self.clear_all_btn)

        right.addLayout(btns)
        right.addWidget(self.progress_bar)
        right.addWidget(self.log_area)

        main_layout.addLayout(left)
        main_layout.addLayout(right)

        cw = QWidget(); cw.setLayout(main_layout); self.setCentralWidget(cw)

        self.start_btn.clicked.connect(self.start_processing)
        self.open_folder_btn.clicked.connect(self.open_file_manager)
        self.clear_all_btn.clicked.connect(self.reset_fields)

    def _create_row(self, t, le, f):
        row = QHBoxLayout()
        lbl = QLabel(t); lbl.setFixedWidth(50); row.addWidget(lbl)
        row.addWidget(le)
        if f: # Browse button
            b1 = QPushButton("..."); b1.setFixedWidth(30); b1.clicked.connect(lambda: f(le)); row.addWidget(b1)
        b2 = QPushButton("✕"); b2.setFixedWidth(30); b2.clicked.connect(lambda: le.clear()); row.addWidget(b2)
        return row

    def update_preview(self):
        self.status_icon = None
        path = self.image_input.text().strip()
        if os.path.exists(path) and not os.path.isdir(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.preview_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.preview_label.setStyleSheet("border: 1px solid #333; background: #000;")
                return
        self.preview_label.clear(); self.preview_label.setText("No Image")
        self.preview_label.setStyleSheet("border: 2px dashed #555; background: #111; color: #555;")

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.status_icon:
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            rect = self.preview_label.rect()
            tl = self.preview_label.mapTo(self, rect.topLeft())
            overlay = QRect(tl.x() + 235, tl.y() + 235, 55, 55)
            p.setBrush(QColor(0, 0, 0, 200)); p.setPen(Qt.NoPen); p.drawEllipse(overlay)
            p.setFont(QFont("Arial", 24, QFont.Bold))
            if self.status_icon == "Success":
                p.setPen(QPen(QColor(0, 255, 127), 3)); p.drawText(overlay, Qt.AlignCenter, "✓")
            else:
                p.setPen(QPen(QColor(255, 69, 0), 3)); p.drawText(overlay, Qt.AlignCenter, "✗")

    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            path = os.path.abspath(os.path.expanduser(url.toLocalFile()))
            ext = os.path.splitext(path)[1].lower()
            if os.path.isdir(path): self.dir_input.setText(path)
            elif ext in self.audio_exts:
                self.audio_input.setText(path)
                if not self.dir_input.text(): self.dir_input.setText(os.path.dirname(path))
                if not self.filename_input.text():
                    self.filename_input.setText(os.path.splitext(os.path.basename(path))[0] + ".mp4")
            elif ext in self.image_exts: self.image_input.setText(path)
        e.accept()

    def play_finish_sound(self):
        try:
            if platform.system() == "Windows": import winsound; winsound.MessageBeep()
            elif platform.system() == "Darwin": os.system('afplay /System/Library/Sounds/Glass.aiff')
            else: os.system('echo -e "\a"')
        except: pass

    def reset_fields(self):
        self.status_icon = None
        for f in [self.audio_input, self.image_input, self.dir_input, self.filename_input, self.log_area]: f.clear()
        self.progress_bar.setValue(0); self.open_folder_btn.setEnabled(False); self.update_preview(); self.update()

    def browse_file(self, le):
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            le.setText(path)
            if le == self.audio_input:
                if not self.dir_input.text(): self.dir_input.setText(os.path.dirname(path))
                if not self.filename_input.text():
                    self.filename_input.setText(os.path.splitext(os.path.basename(path))[0] + ".mp4")

    def browse_directory(self, le):
        path = QFileDialog.getExistingDirectory(self, "Select Dir")
        if path: le.setText(path)

    def start_processing(self):
        self.status_icon = None; self.update()
        
        # Populate filename if empty
        if not self.filename_input.text().strip() and self.audio_input.text().strip():
            audio_base = os.path.splitext(os.path.basename(self.audio_input.text()))[0]
            self.filename_input.setText(audio_base + ".mp4")

        if not all([self.audio_input.text(), self.image_input.text(), self.dir_input.text(), self.filename_input.text()]):
            self.log_area.setText("Incomplete fields. Ensure Audio, Image, and Folder are set."); return
        
        self.start_btn.setEnabled(False); self.progress_bar.setRange(0, 0)
        self.worker = VideoWorker(
            self.audio_input.text(), 
            self.image_input.text(),
            self.dir_input.text(),
            self.filename_input.text(),
            self.res_dropdown.currentText(),
            self.seed_dropdown.currentText(),
            self.bitrate_dropdown.currentText(),
            self.no_clobber_cb.isChecked(),
            self.portrait_cb.isChecked())
        self.worker.progress.connect(self.log_area.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, msg):
        self.progress_bar.setRange(0, 100); self.progress_bar.setValue(100 if success else 0)
        self.start_btn.setEnabled(True); self.play_finish_sound()
        self.status_icon = "Success" if success else "Error"
        self.update()
        if success: 
            self.last_output_path = msg
            self.open_folder_btn.setEnabled(True)
            self.log_area.append(f"\n[DONE] {msg}")
        else: 
            self.log_area.append(f"\n[ERROR] {msg}")

    def open_file_manager(self):
        p = self.last_output_path
        if os.path.exists(p):
            if platform.system() == "Windows":
                subprocess.run(['explorer', '/select,', os.path.normpath(p)])
            elif platform.system() == "Darwin":
                subprocess.run(['open', '-R', p])
            else:
                subprocess.run(['xdg-open', os.path.dirname(p)])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
