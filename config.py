"""
Configuration and constants for BlueChat (WhatsApp-style Bluetooth Messenger).
"""
import os

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

# Storage directories
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".bluechat_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
MEDIA_DIR = os.path.join(CACHE_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
