"""
BlueChat - Main Application Entry Point
Supports both Android (native Bluetooth RFCOMM via Pyjnius) and Desktop Simulation mode.
"""
import sys
import os

# Prevent Kivy from parsing custom command line arguments like --port
os.environ["KIVY_NO_ARGS"] = "1"

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform

from config import APP_NAME, DEFAULT_SIM_PORT_SERVER
from core.desktop_simulator import DesktopSimulatorTransport
from ui.chat_screen import ChatScreen

# Check if running on Android
IS_ANDROID = (platform == "android")

def request_android_permissions():
    """Requests Android runtime permissions for Bluetooth, Mic, and Storage."""
    if IS_ANDROID:
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.BLUETOOTH,
                Permission.BLUETOOTH_ADMIN,
                Permission.BLUETOOTH_CONNECT,
                Permission.BLUETOOTH_SCAN,
                Permission.RECORD_AUDIO,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        except Exception as e:
            print(f"[BlueChat] Permission request failed or not supported: {e}")

class BlueChatApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = APP_NAME

    def build(self):
        # Set a mobile-friendly window aspect ratio for Desktop testing
        if not IS_ANDROID:
            Window.size = (380, 680)

        # Select transport based on platform
        if IS_ANDROID:
            print("[BlueChat] Running on Android: Initializing native Bluetooth driver...")
            request_android_permissions()
            from core.android_bluetooth import AndroidBluetoothTransport
            transport = AndroidBluetoothTransport()
        else:
            # Parse custom port for desktop simulation testing (e.g. python main.py --port 8889)
            sim_port = DEFAULT_SIM_PORT_SERVER
            if "--port" in sys.argv:
                try:
                    idx = sys.argv.index("--port")
                    sim_port = int(sys.argv[idx + 1])
                except Exception:
                    pass
            print(f"[BlueChat] Running on Desktop: Initializing Simulator Transport on port {sim_port}...")
            transport = DesktopSimulatorTransport(port=sim_port)

        # Return Chat Screen
        return ChatScreen(transport=transport)

if __name__ == "__main__":
    BlueChatApp().run()
