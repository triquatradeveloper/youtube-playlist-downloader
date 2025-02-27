import os
import threading
import subprocess
import datetime
import tempfile
import glob
import flet as ft
import yt_dlp
import pythoncom
import win32com.client

# Default thumbnail placeholder URL
DEFAULT_THUMBNAIL = "https://via.placeholder.com/320x180?text=No+Thumbnail"

# Logos for header
YOUTUBE_LOGO = "https://upload.wikimedia.org/wikipedia/commons/4/42/YouTube_icon_%282013-2017%29.png"
SPOTIFY_LOGO = "https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Green.png"

playlist_data = None  # Global variable for playlist info

def get_folder():
    pythoncom.CoInitialize()
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        folder = shell.BrowseForFolder(0, "Select Save Location", 0, 0)
        if folder is None:
            return ""
        folder_path = folder.Items().Item().Path
        return folder_path
    finally:
        pythoncom.CoUninitialize()

def download_spotify_album(album_url, output_path="downloads/", audio_format="flac"):
    command = f"spotdl --output \"{output_path}\" --audio-format {audio_format} {album_url}"
    subprocess.run(command, shell=True)

def combine_all_audio_files(download_path, playlist_data, audio_format):
    file_list_path = os.path.join(download_path, "file_list.txt")
    lines = []
    for entry in playlist_data.get("entries", []):
        title = entry.get("title", "")
        pattern = os.path.join(download_path, f"{title}*.{audio_format}")
        files = glob.glob(pattern)
        if files:
            filename = os.path.basename(files[0])
            lines.append(f"file '{filename}'")
        else:
            print(f"Warning: Could not find file for {title}")
    with open(file_list_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    output_file = os.path.join(download_path, f"combined.{audio_format}")
    cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", file_list_path, "-c", "copy", output_file]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", file_list_path, "-acodec", "copy", output_file]
        result = subprocess.run(cmd, capture_output=True)
    return output_file

def main(page: ft.Page):
    global playlist_data

    # Window settings
    page.window.width = 1000
    page.window.height = 800
    page.window.resizable = True

    # Theme Colors
    light_bg = "#E6F7FF"
    dark_bg = "#2C2C2C"
    # For other boxes we now use transparent backgrounds
    transparent_bg = "transparent"

    dark_mode = {"value": False}
    page.title = "Playlist Downloader"
    page.bgcolor = light_bg
    page.padding = 20

    # ----- Download History Panel -----
    download_history_list = []
    download_history = ft.Column(
        controls=[],
        spacing=10,
        scroll=True,
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER
    )

    def add_download_history(item_text: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        history_item = ft.Text(
            f"[{timestamp}] {item_text}",
            size=14,
            color="white" if dark_mode["value"] else "black",
        )
        download_history.controls.append(history_item)
        download_history_list.append(history_item)
        download_history.update()

    def clear_history(e):
        download_history.controls.clear()
        download_history_list.clear()
        download_history.update()

    clear_history_button = ft.ElevatedButton(
        text="Clear History",
        width=150,
        bgcolor="#d9534f",
        color="white",
        tooltip="Clear all download history",
        on_click=clear_history
    )

    # ----- Header -----
    header_logo = ft.Image(
        src=YOUTUBE_LOGO,
        width=50,
        height=50,
        fit=ft.ImageFit.CONTAIN
    )
    header_title = ft.Text(
        "YouTube Downloader",
        size=32,
        weight="bold",
        color="#FF0000"
    )
    dark_mode_switch = ft.Switch(label="Dark Mode", value=False)
    settings_button = ft.IconButton(
        icon=ft.Icons.SETTINGS,
        tooltip="Settings",
        on_click=lambda e: open_settings_modal()
    )
    header = ft.Container(
        content=ft.Row(
            controls=[
                header_logo,
                header_title,
                ft.Container(expand=True),
                dark_mode_switch,
                settings_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        ),
        padding=15,
        border_radius=8,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#FFEEAD", "#FF6F69"],
        ),
        shadow=ft.BoxShadow(blur_radius=10, color="grey", spread_radius=2)
    )

    def open_settings_modal():
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Settings & Info", weight="bold"),
            content=ft.Text("Playlist Downloader v2.0\nEnjoy the new animations and features!"),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        def close_dialog(e):
            dlg.open = False
            page.update()
        dlg.actions = [ft.TextButton("Close", on_click=close_dialog)]
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ----- Dropdowns -----
    source_dropdown = ft.Dropdown(
        label="Select Source",
        width=200,
        options=[
            ft.dropdown.Option("YouTube"),
            ft.dropdown.Option("Spotify")
        ],
        value="YouTube",
        color="black",
    )
    format_dropdown = ft.Dropdown(
        label="Audio Format",
        width=200,
        options=[
            ft.dropdown.Option("FLAC"),
            ft.dropdown.Option("MP3")
        ],
        value="FLAC",
        color="#800080",
    )
    def on_source_change(e):
        if source_dropdown.value == "YouTube":
            header_logo.src = YOUTUBE_LOGO
            header_title.value = "YouTube Downloader"
            header_title.color = "#FF0000"
            playlist_url_field.label = "Playlist URL"
            playlist_url_field.hint_text = "Enter YouTube playlist URL..."
            log_text.value = "YouTube selected."
        else:
            header_logo.src = SPOTIFY_LOGO
            header_title.value = "Spotify Downloader"
            header_title.color = "#1DB954"
            playlist_url_field.label = "Spotify Album Download"
            playlist_url_field.hint_text = "Enter Spotify album URL..."
            log_text.value = "Spotify selected."
        info_loaded["value"] = False
        playlist_url_field.visible = True
        add_url_button.visible = True
        page.update()
    source_dropdown.on_change = on_source_change

    def on_format_change(e):
        if format_dropdown.value == "FLAC":
            format_dropdown.color = "#800080"
        else:
            format_dropdown.color = "#FFA500"
        page.update()
    format_dropdown.on_change = on_format_change

    # ----- URL Input & Add URL Button -----
    playlist_url_field = ft.TextField(
        label="Playlist URL",
        hint_text="Enter YouTube playlist URL...",
        width=500,
        color="black",
        # Removed explicit border and white background
        border_color=transparent_bg
    )
    add_url_button = ft.ElevatedButton(
        text="Add URL",
        bgcolor="#e0e0e0",
        color="black",
    )
    def on_add_url_click(e):
        if not playlist_url_field.value.strip():
            log_text.value = "Please enter a valid URL."
            page.update()
            return
        playlist_url_field.read_only = True
        add_url_button.visible = False
        download_location_field.visible = True
        browse_button.visible = True
        log_text.value = "URL added. Please select a save location."
        page.update()
    add_url_button.on_click = on_add_url_click

    # ----- Save Location & Browse Button -----
    download_location_field = ft.TextField(
        label="Save Location",
        width=500,
        read_only=True,
        color="black",
        # Remove white background and border:
        border_color=transparent_bg,
        bgcolor=transparent_bg,
        visible=False
    )
    browse_button = ft.IconButton(
        icon=ft.Icons.FOLDER_OPEN,
        tooltip="Browse for Save Location",
        icon_color="black",
        visible=False,
    )
    def on_browse_click(e):
        folder_selected = get_folder()
        if folder_selected:
            download_location_field.value = folder_selected
            progress_bar.visible = True
            log_text.visible = True
            download_button.visible = True
            page.update()
            # Remove any white background for thumbnail container
            thumbnail_container.bgcolor = transparent_bg
            thumbnail_container.opacity = 0
            thumbnail_container.offset = ft.Offset(-1, 0)
            thumbnail_image.src = DEFAULT_THUMBNAIL
            thumbnail_container.visible = True
            page.update()
            if source_dropdown.value == "YouTube":
                threading.Thread(target=load_playlist_info, daemon=True).start()
            else:
                log_text.value = "Ready to download Spotify album."
            page.update()
    browse_button.on_click = on_browse_click

    # ----- Playlist Info & Thumbnail -----
    thumbnail_image = ft.Image(
        src="",
        width=320,
        height=180,
        fit=ft.ImageFit.CONTAIN,
    )
    thumbnail_container = ft.Container(
        content=thumbnail_image,
        visible=False,
        opacity=0,
        offset=ft.Offset(0, 0),
        bgcolor=transparent_bg  # Transparent background instead of white
    )
    playlist_title_text = ft.Text(
        "",
        visible=False,
        color="black",
        size=18,
        weight="bold",
    )
    playlist_info_text = ft.Text(
        "",
        visible=False,
        color="black",
        size=16,
    )
    def load_playlist_info():
        global playlist_data
        url = playlist_url_field.value.strip()
        if not url:
            log_text.value = "No URL provided."
            page.update()
            return
        opts = {"quiet": True, "skip_download": True, "extract_flat": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                playlist_data = ydl.extract_info(url, download=False)
            playlist_title = playlist_data.get("title", "Playlist")
            playlist_title_text.value = playlist_title
            playlist_title_text.visible = True
            if "entries" in playlist_data and playlist_data["entries"]:
                count = len(playlist_data["entries"])
                playlist_info_text.value = f"Total Videos: {count}"
                playlist_info_text.visible = True
            else:
                playlist_info_text.value = "Single Video"
                playlist_info_text.visible = True
            # Try to get thumbnail from first video; if missing, fetch full info.
            thumb = ""
            if "entries" in playlist_data and playlist_data["entries"]:
                first = playlist_data["entries"][0]
                thumb = first.get("thumbnail", "")
                if not thumb:
                    video_id = first.get("id", None)
                    if video_id:
                        video_full_url = f"https://www.youtube.com/watch?v={video_id}"
                        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl2:
                            full_info = ydl2.extract_info(video_full_url, download=False)
                            thumb = full_info.get("thumbnail", "")
            else:
                thumb = playlist_data.get("thumbnail", "")
            thumbnail_image.src = thumb if thumb else DEFAULT_THUMBNAIL
            thumbnail_container.opacity = 1
            thumbnail_container.offset = ft.Offset(0, 0)
            thumbnail_container.update()
            log_text.value = "Playlist loaded."
            info_loaded["value"] = True
        except Exception as ex:
            log_text.value = f"Error loading playlist: {ex}"
        finally:
            page.update()

    # ----- Download Button, Progress Bar & Log Text -----
    download_button = ft.ElevatedButton(
        text="Download",
        width=200,
        bgcolor="#e0e0e0",
        color="black",
        visible=False,
    )
    progress_bar = ft.ProgressBar(
        width=500,
        value=0,
        visible=False,
    )
    log_text = ft.Text(
        value="",
        color="black",
        size=16,
        visible=False,
    )
    info_loaded = {"value": False}
    def download_content():
        if source_dropdown.value == "YouTube" and not info_loaded["value"]:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Please wait for loading info..."),
                bgcolor="#FFA500",
                open=True,
            )
            page.snack_bar.open = True
            page.update()
            return
        url = playlist_url_field.value.strip()
        download_path = download_location_field.value.strip()
        if not url:
            log_text.value = "Please enter a URL."
            page.update()
            return
        if not download_path:
            log_text.value = "Please select a save location."
            page.update()
            return
        audio_format = format_dropdown.value.lower()
        if source_dropdown.value == "Spotify":
            download_button.disabled = True
            progress_bar.visible = False
            log_text.value = "Starting Spotify download..."
            page.update()
            try:
                download_spotify_album(url, output_path=download_path, audio_format=audio_format)
                log_text.value = "Spotify download completed successfully."
                add_download_history("Spotify album downloaded.")
            except Exception as ex:
                log_text.value = f"Error: {ex}"
            finally:
                download_button.disabled = False
                page.update()
        else:
            download_button.disabled = True
            progress_bar.value = 0
            log_text.value = "Starting YouTube download..."
            page.update()
            total_videos = 1
            if playlist_data and "entries" in playlist_data and len(playlist_data["entries"]) > 1:
                total_videos = len(playlist_data["entries"])
            progress_state = {"videos_downloaded": 0, "total_videos": total_videos}
            def progress_hook(d):
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    if total:
                        downloaded = d.get("downloaded_bytes", 0)
                        percentage = downloaded / total
                        overall = (progress_state["videos_downloaded"] + percentage) / progress_state["total_videos"]
                        progress_bar.value = overall
                        speed = d.get("download_speed", 0)
                        if speed:
                            speed_kb = speed / 1024
                            log_text.value = f"Downloading: {overall*100:.2f}% at {speed_kb:.2f} KB/s"
                        else:
                            log_text.value = f"Downloading: {overall*100:.2f}%"
                    else:
                        log_text.value = "Downloading..."
                    progress_bar.update()
                    page.update()
                elif d["status"] == "finished":
                    progress_state["videos_downloaded"] += 1
                    overall = progress_state["videos_downloaded"] / progress_state["total_videos"]
                    progress_bar.value = overall
                    log_text.value = f"Completed video {progress_state['videos_downloaded']} of {progress_state['total_videos']}"
                    progress_bar.update()
                    page.update()
            postprocessor = {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3" if audio_format=="mp3" else "flac",
                "preferredquality": "192" if audio_format=="mp3" else "1706",
            }
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),
                "postprocessors": [postprocessor],
                "progress_hooks": [progress_hook],
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                log_text.value = "Download completed successfully."
                add_download_history("YouTube playlist downloaded.")
                if total_videos > 1:
                    combined_file = combine_all_audio_files(download_path, playlist_data, audio_format)
                    log_text.value = f"Combined into {os.path.basename(combined_file)}"
                    add_download_history(f"Combined file: {os.path.basename(combined_file)}")
            except Exception as ex:
                log_text.value = f"Error: {ex}"
            finally:
                download_button.disabled = False
                page.update()
    download_button.on_click = lambda e: threading.Thread(target=download_content, daemon=True).start()

    # ----- Reset Button -----
    reset_button = ft.ElevatedButton(
        text="Reset",
        width=200,
        bgcolor="#e0e0e0",
        color="black"
    )
    def on_reset_hover(e):
        reset_button.bgcolor = "#cccccc" if e.data == "true" else "#e0e0e0"
        reset_button.update()
    reset_button.on_hover = on_reset_hover
    def reset_ui(e):
        playlist_url_field.value = ""
        playlist_url_field.read_only = False
        add_url_button.visible = True
        download_location_field.value = ""
        download_location_field.visible = False
        browse_button.visible = False
        thumbnail_image.src = ""
        thumbnail_container.visible = False
        thumbnail_container.opacity = 0
        playlist_title_text.value = ""
        playlist_title_text.visible = False
        playlist_info_text.value = ""
        playlist_info_text.visible = False
        download_button.visible = False
        progress_bar.value = 0
        progress_bar.visible = False
        log_text.value = ""
        log_text.visible = False
        info_loaded["value"] = False
        page.update()
    reset_button.on_click = reset_ui

    # ----- Dark Mode Toggle -----
    def toggle_theme(e):
        dark_mode["value"] = dark_mode_switch.value
        if dark_mode["value"]:
            page.bgcolor = dark_bg
            playlist_url_field.color = "white"
            playlist_url_field.border_color = "white"
            download_location_field.color = "white"
            download_location_field.border_color = "white"
        else:
            page.bgcolor = light_bg
            playlist_url_field.color = "black"
            playlist_url_field.border_color = "black"
            download_location_field.color = "black"
            download_location_field.border_color = "black"
        history_panel.bgcolor = "#444444" if dark_mode["value"] else "#DDDDDD"
        header.update()
        history_panel.update()
        control_panel.update()
        page.update()
    dark_mode_switch.on_change = toggle_theme

    # ----- Main Layout -----
    control_panel = ft.Column(
        controls=[
            header,
            ft.Divider(height=2, color="black"),
            ft.Row(
                controls=[source_dropdown, format_dropdown],
                spacing=20,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(controls=[playlist_url_field, add_url_button], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Row(controls=[download_location_field, browse_button], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                    ],
                    spacing=15,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                padding=10,
                border=ft.border.all(1, "black"),
                border_radius=5,
                bgcolor=transparent_bg  # Transparent background
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        playlist_title_text,
                        playlist_info_text,
                        thumbnail_container,
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                padding=10,
                # Remove border and background for playlist info area
                bgcolor=transparent_bg,
                border_radius=5,
            ),
            download_button,
            progress_bar,
            log_text,
            ft.Row(
                controls=[reset_button, clear_history_button],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
            ),
        ],
        spacing=20,
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True
    )

    history_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Download History", size=20, weight="bold", color="white" if dark_mode["value"] else "black"),
                ft.Divider(color="white" if dark_mode["value"] else "black"),
                download_history,
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER
        ),
        width=300,
        padding=15,
        border_radius=8,
        bgcolor="#444444" if dark_mode["value"] else "#DDDDDD",
        shadow=ft.BoxShadow(blur_radius=10, color="grey", spread_radius=2)
    )

    main_layout = ft.Row(
        controls=[control_panel, history_panel],
        spacing=20,
        alignment=ft.MainAxisAlignment.CENTER
    )
    page.add(main_layout)

ft.app(target=main, view=ft.AppView.WEB_BROWSER)
