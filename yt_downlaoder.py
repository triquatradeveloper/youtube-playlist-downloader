import sys
import os
import threading
import subprocess
import datetime
import requests
import yt_dlp
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox, QProgressBar, QFileDialog, QTextEdit,
    QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

# Constants and history file
HISTORY_FILE = "download_history.txt"
DEFAULT_THUMBNAIL = "https://dummyimage.com/320x180/cccccc/ffffff&text=No+Thumbnail"
YOUTUBE_LOGO = "https://upload.wikimedia.org/wikipedia/commons/4/42/YouTube_icon_%282013-2017%29.png"
SPOTIFY_LOGO = "https://www.vectorlogo.zone/logos/spotify/spotify-icon.svg"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def save_history(text):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

# Custom logger to suppress yt_dlp warnings
class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(msg)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Playlist Downloader")
        self.setGeometry(100, 100, 900, 700)
        self.playlist_data = None
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()

        # Title label
        title_lbl = QLabel("Playlist Downloader")
        title_lbl.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #FFD700;")
        main_layout.addWidget(title_lbl)

        # Logo layout (YouTube and Spotify logos)
        logo_layout = QHBoxLayout()
        self.youtube_logo = QLabel()
        self.youtube_logo.setPixmap(QPixmap(YOUTUBE_LOGO).scaled(50, 50, Qt.KeepAspectRatio))
        logo_layout.addWidget(self.youtube_logo)
        self.spotify_logo = QLabel()
        self.spotify_logo.setPixmap(QPixmap(SPOTIFY_LOGO).scaled(50, 50, Qt.KeepAspectRatio))
        logo_layout.addWidget(self.spotify_logo)
        main_layout.addLayout(logo_layout)

        # URL input and Add URL button
        url_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter YouTube playlist URL or single video URL...")
        url_layout.addWidget(QLabel("Playlist URL:"))
        url_layout.addWidget(self.url_edit)
        self.add_url_btn = QPushButton("Add URL")
        self.add_url_btn.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 8px;")
        self.add_url_btn.clicked.connect(self.on_add_url)
        url_layout.addWidget(self.add_url_btn)
        main_layout.addLayout(url_layout)

        # Dropdowns for Source and Format
        dropdown_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(["YouTube", "Spotify"])
        self.source_combo.setStyleSheet("color: black;")
        dropdown_layout.addWidget(QLabel("Source:"))
        dropdown_layout.addWidget(self.source_combo)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["FLAC", "MP3", "HD Video"])
        self.format_combo.setStyleSheet("color: black;")
        dropdown_layout.addWidget(QLabel("Format:"))
        dropdown_layout.addWidget(self.format_combo)
        main_layout.addLayout(dropdown_layout)

        # Save location and Browse button
        loc_layout = QHBoxLayout()
        self.loc_edit = QLineEdit()
        self.loc_edit.setReadOnly(True)
        loc_layout.addWidget(QLabel("Save Location:"))
        loc_layout.addWidget(self.loc_edit)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setStyleSheet("background-color: #3faffa; color: white; border-radius: 8px;")
        self.browse_btn.clicked.connect(self.on_browse)
        loc_layout.addWidget(self.browse_btn)
        main_layout.addLayout(loc_layout)

        # Video list
        self.video_list = QListWidget()
        self.video_list.setStyleSheet("background-color: #000000; color: white;")
        main_layout.addWidget(self.video_list)

        # Log display and progress bar
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet("background-color: #2e2e2e; color: white; border-radius: 8px; padding: 10px;")
        main_layout.addWidget(self.log_edit)
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Download and Reset buttons
        btn_layout = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.download_btn.setStyleSheet("background-color: #FF6347; color: white; border-radius: 8px;")
        self.download_btn.clicked.connect(self.on_download)
        btn_layout.addWidget(self.download_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet("background-color: #808080; color: white; border-radius: 8px;")
        self.reset_btn.clicked.connect(self.on_reset)
        btn_layout.addWidget(self.reset_btn)
        main_layout.addLayout(btn_layout)

        # History display
        history_lbl = QLabel("Download History:")
        history_lbl.setStyleSheet("color: white; font-size: 18px;")
        main_layout.addWidget(history_lbl)
        self.history_edit = QTextEdit()
        self.history_edit.setReadOnly(True)
        self.history_edit.setPlainText(load_history())
        self.history_edit.setStyleSheet("background-color: #3e3e3e; color: white; border-radius: 8px; padding: 10px;")
        main_layout.addWidget(self.history_edit)

        central.setLayout(main_layout)

    def log(self, message):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_edit.append(f"[{ts}] {message}")

    def on_add_url(self):
        url = self.url_edit.text().strip()
        if not url.lower().startswith("http"):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid URL (starting with http/https).")
            return
        self.log("URL added. Please select a save location.")
        # Check if the URL is for a playlist or a single video
        if 'playlist' in url:
            self.log("You entered a playlist URL.")
        else:
            self.log("You entered a single video URL.")

    def on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Location")
        if folder:
            self.loc_edit.setText(folder)
            if self.source_combo.currentText() == "YouTube":
                threading.Thread(target=self.load_playlist_info, daemon=True).start()
            else:
                self.log("Ready to download Spotify album.")

    def load_playlist_info(self):
        url = self.url_edit.text().strip()
        if not url:
            self.log("No URL provided.")
            return

        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "logger": MyLogger(),
            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            video_count = len(info.get("entries", [])) if "entries" in info else 1
            title = info.get("title", "Playlist")
            self.playlist_data = info
            self.log(f"Playlist '{title}' loaded with {video_count} videos.")

            # Display playlist name and video titles
            self.video_list.clear()  # Clear the previous list
            for entry in info.get("entries", []):
                item = QListWidgetItem(entry.get("title", "Unknown Video"))
                item.setBackground(Qt.black)  # Set background to black
                self.video_list.addItem(item)

        except Exception as ex:
            self.log(f"Error loading playlist: {ex}")

    def on_download(self):
        if self.source_combo.currentText() == "YouTube" and not self.playlist_data:
            self.log("Please wait for playlist info to load...")
            return
        folder = self.loc_edit.text().strip()
        if not folder:
            self.log("Please select a save location.")
            return
        threading.Thread(target=self.download_content, daemon=True).start()

    def download_content(self):
        url = self.url_edit.text().strip()
        folder = self.loc_edit.text().strip()
        fmt = self.format_combo.currentText()
        audio_format = fmt.lower()
        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Determine total number of videos (default to 1 for single video)
        total_videos = 1
        if self.playlist_data and "entries" in self.playlist_data and isinstance(self.playlist_data["entries"], list):
            total_videos = len(self.playlist_data["entries"])
        
        progress_state = {"videos_downloaded": 0, "total_videos": total_videos}

        if self.source_combo.currentText() == "Spotify":
            self.log("Starting Spotify download...")
            try:
                cmd = f'spotdl --output "{folder}" --audio-format {audio_format} {url}'
                subprocess.run(cmd, shell=True)
                self.log("Spotify download completed successfully.")
                history_line = f"{datetime.datetime.now().strftime('%H:%M:%S')} Spotify album downloaded."
                save_history(history_line)
                self.history_edit.append(history_line)
            except Exception as ex:
                self.log(f"Error: {ex}")
        else:
            self.log("Starting YouTube download...")
            
            if fmt == "HD Video":
                ydl_opts = {
                    "format": "bestvideo[height<=1080]+bestaudio/best",
                    "merge_output_format": "mp4",
                    "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
                    "progress_hooks": [self.make_progress_hook(progress_state)],
                    "no_warnings": True,
                    "quiet": True,
                    "logger": MyLogger(),
                }
            else:
                postprocessor = {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3" if audio_format == "mp3" else "flac",
                    "preferredquality": "192" if audio_format == "mp3" else "1706",
                }
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
                    "postprocessors": [postprocessor],
                    "progress_hooks": [self.make_progress_hook(progress_state)],
                    "no_warnings": True,
                    "quiet": True,
                    "logger": MyLogger(),
                }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                if fmt == "HD Video":
                    self.log("HD Video download completed successfully.")
                    history_line = f"{datetime.datetime.now().strftime('%H:%M:%S')} YouTube HD video downloaded."
                else:
                    self.log("Download completed successfully.")
                    history_line = f"{datetime.datetime.now().strftime('%H:%M:%S')} YouTube playlist downloaded."
                save_history(history_line)
                self.history_edit.append(history_line)
            except Exception as ex:
                self.log(f"Error: {ex}")
        self.download_btn.setEnabled(True)

    def make_progress_hook(self, progress_state):
        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    downloaded = d.get("downloaded_bytes", 0)
                    percentage = downloaded / total
                    overall = (progress_state["videos_downloaded"] + percentage) / progress_state["total_videos"]
                    self.progress_bar.setValue(int(overall * 100))
                    self.log(f"Downloading: {overall * 100:.2f}%")
            elif d["status"] == "finished":
                progress_state["videos_downloaded"] += 1
                overall = progress_state["videos_downloaded"] / progress_state["total_videos"]
                self.progress_bar.setValue(int(overall * 100))
                self.log(f"Completed video {progress_state['videos_downloaded']} of {progress_state['total_videos']}")
        return hook

    def on_reset(self):
        self.url_edit.clear()
        self.loc_edit.clear()
        self.video_list.clear()
        self.log_edit.clear()
        self.playlist_data = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply an advanced dark style using Qt Stylesheets
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background-color: #1e1e1e; }
        QLabel { color: #FFFFFF; font-size: 18px; font-weight: bold; }
        QLineEdit, QComboBox, QTextEdit {
            background-color: #3E3E3E; 
            color: #FFFFFF; 
            border: 1px solid #555555; 
            border-radius: 8px; 
            padding: 4px;
        }
        QPushButton { 
            background-color: #FF6347; 
            color: white; 
            border-radius: 12px; 
            padding: 10px 20px;
        }
        QPushButton:hover { background-color: #FF4500; }
        QProgressBar { 
            background-color: #555555; 
            color: white; 
            border: 1px solid #444444; 
            border-radius: 8px; 
            text-align: center; 
        }
        QProgressBar::chunk { background-color: #FF6347; border-radius: 8px; }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
