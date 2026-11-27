#!python3.11
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
from kivy.clock import Clock

from config import APP_NAME, DEFAULT_SIM_PORT_SERVER
from ui.chat_screen import ChatScreen

# Check if running on Android
IS_ANDROID = (platform == "android")

def request_android_permissions():
    """Safely requests Android runtime permissions across Android 6 to 14."""
    if not IS_ANDROID:
        return
    try:
        from android.permissions import request_permissions, Permission
        perms_to_request = []

        # Audio recording permission
        if hasattr(Permission, 'RECORD_AUDIO'):
            perms_to_request.append(Permission.RECORD_AUDIO)
        else:
            perms_to_request.append("android.permission.RECORD_AUDIO")

        # Storage permissions
        if hasattr(Permission, 'READ_EXTERNAL_STORAGE'):
            perms_to_request.append(Permission.READ_EXTERNAL_STORAGE)
        if hasattr(Permission, 'WRITE_EXTERNAL_STORAGE'):
            perms_to_request.append(Permission.WRITE_EXTERNAL_STORAGE)

        # Android 12+ (API 31+) Bluetooth runtime permissions
        for b_perm in ['BLUETOOTH_CONNECT', 'BLUETOOTH_SCAN', 'BLUETOOTH_ADVERTISE']:
            if hasattr(Permission, b_perm):
                perms_to_request.append(getattr(Permission, b_perm))
            else:
                perms_to_request.append(f"android.permission.{b_perm}")

        # Android 13+ (API 33+) Media permissions
        for m_perm in ['READ_MEDIA_AUDIO', 'READ_MEDIA_VIDEO']:
            if hasattr(Permission, m_perm):
                perms_to_request.append(getattr(Permission, m_perm))
            else:
                perms_to_request.append(f"android.permission.{m_perm}")

        request_permissions(perms_to_request)
    except Exception as e:
        print(f"[BlueChat] Permission request error: {e}")


class BlueChatApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = APP_NAME
        self.transport = None

    def build(self):
        # Set a mobile-friendly window aspect ratio for Desktop testing
        if not IS_ANDROID:
            Window.size = (380, 680)

        # Select transport based on platform
        if IS_ANDROID:
            print("[BlueChat] Running on Android: Initializing native Bluetooth driver...")
            from core.android_bluetooth import AndroidBluetoothTransport
            self.transport = AndroidBluetoothTransport()
            # Request permissions right after app is built
            Clock.schedule_once(lambda dt: request_android_permissions(), 0.5)
        else:
            from core.desktop_simulator import DesktopSimulatorTransport
            sim_port = DEFAULT_SIM_PORT_SERVER
            if "--port" in sys.argv:
                try:
                    idx = sys.argv.index("--port")
                    sim_port = int(sys.argv[idx + 1])
                except Exception:
                    pass
            print(f"[BlueChat] Running on Desktop: Initializing Simulator Transport on port {sim_port}...")
            self.transport = DesktopSimulatorTransport(port=sim_port)

        return ChatScreen(transport=self.transport)

    def on_pause(self):
        # Return True so the app remains active in background when Bluetooth is connected
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    BlueChatApp().run()
