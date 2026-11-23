"""
Configuration and constants for BlueChat (Telegram-style Bluetooth Messenger).
Cross-platform safe for Android and Desktop.
"""
import os
import sys

# Application Info
APP_NAME = "BlueChat"
APP_VERSION = "2.0.0"

# Telegram Modern Blue Palette
COLOR_TELEGRAM_BLUE = (0.137, 0.616, 0.847, 1.0)    # #239ED8 - Telegram Header
COLOR_TELEGRAM_DARK = (0.102, 0.455, 0.627, 1.0)    # #1A74A0 - Header shadow / borders
COLOR_TELEGRAM_ACCENT = (0.157, 0.655, 0.898, 1.0)  # #28A7E5 - Send button / Active icons
COLOR_CHAT_BG = (0.878, 0.914, 0.941, 1.0)         # #E0E9F0 - Telegram light chat background
COLOR_BUBBLE_OUT = (0.824, 0.922, 0.984, 1.0)      # #D2EBFB - Outgoing message (Telegram soft blue)
COLOR_BUBBLE_IN = (1.0, 1.0, 1.0, 1.0)              # #FFFFFF - Incoming message (pure white)
COLOR_TEXT_PRIMARY = (0.13, 0.13, 0.13, 1.0)       # Charcoal text
COLOR_TEXT_MUTED = (0.50, 0.58, 0.64, 1.0)         # Timestamp & read status
COLOR_AVATAR_BG = (0.28, 0.65, 0.90, 1.0)          # Telegram avatar circle
COLOR_INPUT_CONTAINER = (1.0, 1.0, 1.0, 1.0)       # White input bar container

# Bluetooth Standard Serial Port Profile (SPP) UUID
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
SERVICE_NAME = "BlueChatService"

# Protocol Buffer & Chunk Sizes
CHUNK_SIZE = 4096       # 4 KB chunk size for smooth transfer over Bluetooth RFCOMM
MAGIC_HEADER = b"BC"    # 2 bytes magic identifier: 'BlueChat'
PROTOCOL_VERSION = 2    # Protocol version 2 with CRC32 & Typing

# Packet Types
PKT_TEXT = 0x01
PKT_AUDIO = 0x02
PKT_VIDEO = 0x03
PKT_IMAGE = 0x04
PKT_PROGRESS = 0x05
PKT_TYPING = 0x06
PKT_PING = 0x07

# Desktop Simulation Ports
DEFAULT_SIM_PORT_SERVER = 8888
DEFAULT_SIM_PORT_CLIENT = 8889

def get_base_dir() -> str:
    """Safely retrieves a writable storage directory across Android and Desktop."""
    try:
        from kivy.utils import platform
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                mActivity = PythonActivity.mActivity
                if mActivity:
                    return str(mActivity.getFilesDir().getAbsolutePath())
            except Exception:
                pass
            return "/data/data/org.bluechat.app/files"
    except Exception:
        pass
    
    home = os.path.expanduser("~")
    if not home or not os.path.isdir(home) or home == "/":
        home = os.getcwd()
    return os.path.join(home, ".bluechat_cache")

def get_media_dir() -> str:
    """Returns the media storage directory, creating it if needed."""
    base = get_base_dir()
    media_dir = os.path.join(base, "media")
    try:
        os.makedirs(media_dir, exist_ok=True)
    except Exception as e:
        print(f"[Config] Error creating media dir {media_dir}: {e}")
        media_dir = os.path.join(os.getcwd(), "media")
        os.makedirs(media_dir, exist_ok=True)
    return media_dir

def get_default_picker_dir() -> str:
    """Returns a valid starting directory for the file chooser."""
    try:
        from kivy.utils import platform
        if platform == "android":
            for candidate in ["/sdcard/Download", "/sdcard/Pictures", "/sdcard/DCIM", "/sdcard/Movies", "/storage/emulated/0", "/sdcard"]:
                if os.path.exists(candidate):
                    return candidate
    except Exception:
        pass
    return os.path.expanduser("~")
