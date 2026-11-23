"""
Configuration and constants for BlueChat (WhatsApp-style Bluetooth Messenger).
Cross-platform safe for Android and Desktop.
"""
import os
import sys

# Application Info
APP_NAME = "BlueChat"
APP_VERSION = "1.0.0"

# WhatsApp Palette Colors (Hex strings & RGBA tuples for Kivy)
COLOR_TEAL_DARK = (0.027, 0.369, 0.329, 1.0)       # #075E54 - Top App Bar
COLOR_TEAL_LIGHT = (0.071, 0.549, 0.494, 1.0)      # #128C7E - Secondary elements
COLOR_GREEN_ACCENT = (0.145, 0.827, 0.400, 1.0)    # #25D366 - Send button / Online status
COLOR_CHAT_BG = (0.925, 0.898, 0.867, 1.0)         # #ECE5DD - WhatsApp chat wallpaper background
COLOR_BUBBLE_OUT = (0.863, 0.969, 0.776, 1.0)      # #DCF8C6 - Outgoing message bubble (light green)
COLOR_BUBBLE_IN = (1.0, 1.0, 1.0, 1.0)              # #FFFFFF - Incoming message bubble (pure white)
COLOR_TEXT_PRIMARY = (0.1, 0.1, 0.1, 1.0)          # Text color
COLOR_TEXT_MUTED = (0.5, 0.5, 0.5, 1.0)            # Timestamp and status text
COLOR_DISCONNECTED = (0.8, 0.2, 0.2, 1.0)          # Disconnected red indicator
COLOR_CONNECTING = (0.9, 0.6, 0.1, 1.0)            # Connecting amber indicator

# Bluetooth Standard Serial Port Profile (SPP) UUID
# Standard UUID for RFCOMM serial data exchange between devices
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
SERVICE_NAME = "BlueChatService"

# Protocol Buffer & Chunk Sizes
CHUNK_SIZE = 4096       # 4 KB chunk size for smooth transfer over Bluetooth RFCOMM
MAGIC_HEADER = b"BC"    # 2 bytes magic identifier: 'BlueChat'
PROTOCOL_VERSION = 1    # Protocol version

# Packet Types
PKT_TEXT = 0x01
PKT_AUDIO = 0x02
PKT_VIDEO = 0x03
PKT_FILE = 0x04
PKT_PROGRESS = 0x05
PKT_ACK = 0x06

# Desktop Simulation Ports
DEFAULT_SIM_PORT_SERVER = 8888
DEFAULT_SIM_PORT_CLIENT = 8889

def get_base_dir() -> str:
    """Safely retrieves a writable storage directory across Android and Desktop."""
    try:
        from kivy.utils import platform
        if platform == "android":
            # On Android, use the app's dedicated internal storage to avoid permission errors
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
    
    # Desktop fallback
    home = os.path.expanduser("~")
    # Verify home is writable
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
            for candidate in ["/sdcard/Download", "/sdcard/Movies", "/sdcard/DCIM", "/storage/emulated/0", "/sdcard"]:
                if os.path.exists(candidate):
                    return candidate
    except Exception:
        pass
    return os.path.expanduser("~")
