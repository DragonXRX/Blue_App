#!python3.11
"""
BlueChat - Main Application Entry Point
Supports Android Native Bluetooth (RFCOMM + Pyjnius) and Desktop Simulation.
Features:
- Window softinput_mode = 'below_target' (keyboard sliding)
- Android WakeLock Manager (prevents background disconnection)
- Comprehensive runtime permissions
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

class WakeLockManager:
    """Manages Android WakeLock to prevent socket disconnection when phone is locked."""
    def __init__(self):
        self.wake_lock = None

    def acquire(self):
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            PowerManager = autoclass("android.os.PowerManager")
            
            activity = PythonActivity.mActivity
            if activity:
                pm = activity.getSystemService(Context.POWER_SERVICE)
                # PARTIAL_WAKE_LOCK = 1
                self.wake_lock = pm.newWakeLock(1, "BlueChat:BluetoothKeepAlive")
                self.wake_lock.acquire()
                print("[BlueChat] WakeLock acquired successfully.")
        except Exception as e:
            print(f"[BlueChat] Cannot acquire WakeLock: {e}")

    def release(self):
        if not IS_ANDROID or not self.wake_lock:
            return
        try:
            if self.wake_lock.isHeld():
                self.wake_lock.release()
                print("[BlueChat] WakeLock released.")
        except Exception as e:
            print(f"[BlueChat] Cannot release WakeLock: {e}")
        self.wake_lock = None


def configure_android_window():
    """Forces Android Window to resize when the soft keyboard is displayed."""
    if not IS_ANDROID:
        return
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        WindowManagerLayoutParams = autoclass("android.view.WindowManager$LayoutParams")
        activity = PythonActivity.mActivity
        if activity:
            def _set_mode():
                # SOFT_INPUT_ADJUST_RESIZE = 16 (0x10)
                # SOFT_INPUT_STATE_ALWAYS_HIDDEN = 2
                activity.getWindow().setSoftInputMode(0x10 | 2)
                print("[BlueChat] Android Window softInputMode set to ADJUST_RESIZE successfully.")
            activity.runOnUiThread(_set_mode)
    except Exception as e:
        print(f"[BlueChat] configure_android_window error: {e}")


def request_android_permissions():
    """Safely requests Android runtime permissions across all Android versions."""
    if not IS_ANDROID:
        return
    try:
        from android.permissions import request_permissions, Permission
        perms_to_request = []

        # Audio recording
        if hasattr(Permission, 'RECORD_AUDIO'):
            perms_to_request.append(Permission.RECORD_AUDIO)
        else:
            perms_to_request.append("android.permission.RECORD_AUDIO")

        # Storage permissions
        if hasattr(Permission, 'READ_EXTERNAL_STORAGE'):
            perms_to_request.append(Permission.READ_EXTERNAL_STORAGE)
        if hasattr(Permission, 'WRITE_EXTERNAL_STORAGE'):
            perms_to_request.append(Permission.WRITE_EXTERNAL_STORAGE)

        # Bluetooth runtime permissions (Android 12+)
        for b_perm in ['BLUETOOTH_CONNECT', 'BLUETOOTH_SCAN', 'BLUETOOTH_ADVERTISE']:
            if hasattr(Permission, b_perm):
                perms_to_request.append(getattr(Permission, b_perm))
            else:
                perms_to_request.append(f"android.permission.{b_perm}")

        # Media permissions (Android 13+)
        for m_perm in ['READ_MEDIA_AUDIO', 'READ_MEDIA_VIDEO']:
            if hasattr(Permission, m_perm):
                perms_to_request.append(getattr(Permission, m_perm))
            else:
                perms_to_request.append(f"android.permission.{m_perm}")

        # Location permissions for Bluetooth discovery on older Android
        for loc in ['ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION']:
            if hasattr(Permission, loc):
                perms_to_request.append(getattr(Permission, loc))
            else:
                perms_to_request.append(f"android.permission.{loc}")

        request_permissions(perms_to_request)
    except Exception as e:
        print(f"[BlueChat] Permission request error: {e}")


class BlueChatApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = APP_NAME
        self.transport = None
        self.wakelock_mgr = WakeLockManager()

    def build(self):
        # Configure Kivy Window to pan and animate cleanly with keyboard
        Window.softinput_mode = "pan"
        Window.keyboard_anim_args = {'d': 0.2, 't': 'in_out_quart'}

        if not IS_ANDROID:
            Window.size = (380, 680)

        # Select transport based on platform
        if IS_ANDROID:
            print("[BlueChat] Running on Android: Initializing native Bluetooth driver...")
            from core.android_bluetooth import AndroidBluetoothTransport
            self.transport = AndroidBluetoothTransport()
            Clock.schedule_once(lambda dt: configure_android_window(), 0.2)
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

        # Wire up WakeLock with connection lifecycle
        original_on_connected = self.transport.on_connected
        original_on_disconnected = self.transport.on_disconnected

        def _wrapped_connected(peer_name):
            self.wakelock_mgr.acquire()
            if original_on_connected:
                original_on_connected(peer_name)

        def _wrapped_disconnected():
            self.wakelock_mgr.release()
            if original_on_disconnected:
                original_on_disconnected()

        self.transport.on_connected = _wrapped_connected
        self.transport.on_disconnected = _wrapped_disconnected

        return ChatScreen(transport=self.transport)

    def on_pause(self):
        # Keep app active in background when connected
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        self.wakelock_mgr.release()


if __name__ == "__main__":
    BlueChatApp().run()
