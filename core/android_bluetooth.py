"""
Native Android Bluetooth RFCOMM Transport using Pyjnius.
Enhanced with:
- Dynamic Nearby Device Discovery (Scan for unbonded devices)
- Automatic Reconnection when moving out/in of range
- Robust exception handling to prevent SecurityException crashes
"""
import time
import threading
from typing import List, Dict, Optional, Callable
from core.transport import BaseTransport
from config import SPP_UUID, SERVICE_NAME

# Try importing pyjnius autoclass
try:
    from jnius import autoclass
    HAS_PYJNIUS = True
except ImportError:
    HAS_PYJNIUS = False


class AndroidBluetoothTransport(BaseTransport):
    def __init__(self):
        super().__init__()
        self._server_socket = None
        self._client_socket = None
        self._in_stream = None
        self._out_stream = None
        self._running = False
        self._adapter = None
        self._uuid = None
        
        # Auto-reconnection state
        self.last_connected_address = None
        self.auto_reconnect_enabled = True
        self.is_reconnecting = False
        self.on_reconnecting_status: Optional[Callable[[str], None]] = None

        if HAS_PYJNIUS:
            try:
                UUID = autoclass("java.util.UUID")
                self._uuid = UUID.fromString(SPP_UUID)
                self._init_adapter()
            except Exception as e:
                print(f"[AndroidBluetooth] Init error: {e}")

    def _init_adapter(self):
        """Safely retrieves the default BluetoothAdapter."""
        if not HAS_PYJNIUS:
            return None
        if self._adapter is not None:
            return self._adapter
        try:
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            self._adapter = BluetoothAdapter.getDefaultAdapter()
            return self._adapter
        except Exception as e:
            print(f"[AndroidBluetooth] Cannot get BluetoothAdapter: {e}")
            return None

    def is_bluetooth_enabled(self) -> bool:
        adapter = self._init_adapter()
        if not adapter:
            return False
        try:
            return bool(adapter.isEnabled())
        except Exception:
            return False

    def get_paired_devices(self) -> List[Dict[str, str]]:
        """Returns list of bonded (paired) Bluetooth devices."""
        devices = []
        adapter = self._init_adapter()
        if not adapter:
            return devices

        try:
            bonded = adapter.getBondedDevices()
            if bonded is not None:
                bonded_devices = bonded.toArray()
                for dev in bonded_devices:
                    try:
                        name = str(dev.getName() or "Unknown Device")
                        address = str(dev.getAddress() or "")
                        devices.append({"name": name, "address": address})
                    except Exception:
                        pass
        except Exception as e:
            print(f"[AndroidBluetooth] Error getting bonded devices: {e}")
            if self.on_error:
                self.on_error("Bluetooth permission needed to read paired devices.")
        return devices

    def start_server(self, callback: Optional[Callable[[bool, str], None]] = None):
        """Starts Bluetooth RFCOMM server listener on Android."""
        adapter = self._init_adapter()
        if not adapter:
            msg = "Bluetooth hardware not detected or not available."
            if callback:
                callback(False, msg)
            if self.on_error:
                self.on_error(msg)
            return

        def _listen():
            try:
                self._server_socket = adapter.listenUsingRfcommWithServiceRecord(
                    SERVICE_NAME, self._uuid
                )
                self._running = True
                if callback:
                    callback(True, "Waiting for incoming Bluetooth connection...")

                # Blocking accept
                socket = self._server_socket.accept()
                self._client_socket = socket
                self._in_stream = socket.getInputStream()
                self._out_stream = socket.getOutputStream()
                self.is_connected = True

                try:
                    device = socket.getRemoteDevice()
                    self.peer_name = str(device.getName() or device.getAddress())
                    self.last_connected_address = str(device.getAddress())
                except Exception:
                    self.peer_name = "Remote Phone"

                if self.on_connected:
                    self.on_connected(self.peer_name)

                self._start_reader()
            except Exception as e:
                self._running = False
                err_text = str(e)
                print(f"[AndroidBluetooth] Server listen error: {err_text}")
                if "SecurityException" in err_text:
                    err_text = "Permission denied: Grant Bluetooth permissions in phone settings."
                if callback:
                    callback(False, err_text)
                if self.on_error:
                    self.on_error(err_text)

        threading.Thread(target=_listen, daemon=True).start()

    def connect_to_device(self, device_address_or_info: str, callback: Optional[Callable[[bool, str], None]] = None):
        """Connects to a remote Android Bluetooth device by MAC address."""
        adapter = self._init_adapter()
        if not adapter:
            msg = "Bluetooth not available on this device."
            if callback:
                callback(False, msg)
            if self.on_error:
                self.on_error(msg)
            return

        self.last_connected_address = device_address_or_info

        def _connect():
            try:
                try:
                    adapter.cancelDiscovery()
                except Exception:
                    pass

                remote_device = adapter.getRemoteDevice(device_address_or_info)
                socket = remote_device.createRfcommSocketToServiceRecord(self._uuid)
                
                # Connect (blocking)
                socket.connect()

                self._client_socket = socket
                self._in_stream = socket.getInputStream()
                self._out_stream = socket.getOutputStream()
                self.is_connected = True
                self.is_reconnecting = False
                self._running = True
                try:
                    self.peer_name = str(remote_device.getName() or device_address_or_info)
                except Exception:
                    self.peer_name = str(device_address_or_info)

                if callback:
                    callback(True, f"Connected to {self.peer_name}")
                if self.on_connected:
                    self.on_connected(self.peer_name)

                self._start_reader()
            except Exception as e:
                self.is_connected = False
                err_text = str(e)
                print(f"[AndroidBluetooth] Connection error: {err_text}")
                if "SecurityException" in err_text:
                    err_text = "Permission denied: Grant Bluetooth Connect permission in settings."
                if callback:
                    callback(False, err_text)
                if self.on_error:
                    self.on_error(err_text)

        threading.Thread(target=_connect, daemon=True).start()

    def _start_reader(self):
        """Continuously reads bytes from Bluetooth InputStream."""
        def _read_loop():
            byte_array = bytearray(4096)
            while self._running and self._in_stream:
                try:
                    num_bytes = self._in_stream.read(byte_array)
                    if num_bytes > 0:
                        raw_data = bytes(byte_array[:num_bytes])
                        if self.on_packet_received:
                            self.on_packet_received(raw_data)
                    elif num_bytes == -1:
                        break
                except Exception:
                    break

            self._handle_unexpected_disconnect()

        threading.Thread(target=_read_loop, daemon=True).start()

    def _handle_unexpected_disconnect(self):
        """Attempts auto-reconnection if enabled before fully disconnecting."""
        was_connected = self.is_connected
        self.disconnect(trigger_callback=False)

        if was_connected and self.auto_reconnect_enabled and self.last_connected_address:
            self.is_reconnecting = True
            if self.on_reconnecting_status:
                self.on_reconnecting_status("reconnecting...")

            def _auto_reconnect_worker():
                for attempt in range(1, 4):
                    if not self.is_reconnecting:
                        break
                    time.sleep(3.0)
                    try:
                        adapter = self._init_adapter()
                        if not adapter or not adapter.isEnabled():
                            break
                        remote_device = adapter.getRemoteDevice(self.last_connected_address)
                        socket = remote_device.createRfcommSocketToServiceRecord(self._uuid)
                        socket.connect()

                        self._client_socket = socket
                        self._in_stream = socket.getInputStream()
                        self._out_stream = socket.getOutputStream()
                        self.is_connected = True
                        self.is_reconnecting = False
                        self._running = True

                        if self.on_connected:
                            self.on_connected(self.peer_name)
                        self._start_reader()
                        return
                    except Exception as e:
                        print(f"[AndroidBluetooth] Auto-reconnect attempt {attempt} failed: {e}")

                self.is_reconnecting = False
                if self.on_disconnected:
                    self.on_disconnected()

            threading.Thread(target=_auto_reconnect_worker, daemon=True).start()
        else:
            if self.on_disconnected:
                self.on_disconnected()

    def send_data(self, data: bytes) -> bool:
        if not self.is_connected or not self._out_stream:
            return False
        try:
            self._out_stream.write(data)
            self._out_stream.flush()
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Send failed: {e}")
            self.disconnect()
            return False

    def disconnect(self, trigger_callback: bool = True):
        self._running = False
        self.is_connected = False
        self.is_reconnecting = False

        if self._in_stream:
            try:
                self._in_stream.close()
            except Exception:
                pass
            self._in_stream = None

        if self._out_stream:
            try:
                self._out_stream.close()
            except Exception:
                pass
            self._out_stream = None

        if self._client_socket:
            try:
                self._client_socket.close()
            except Exception:
                pass
            self._client_socket = None

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        if trigger_callback and self.on_disconnected:
            self.on_disconnected()
