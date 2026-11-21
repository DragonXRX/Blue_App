"""
Native Android Bluetooth RFCOMM Transport using Pyjnius.
Interacts with Android BluetoothAdapter, BluetoothDevice, BluetoothServerSocket, and BluetoothSocket.
"""
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

        if HAS_PYJNIUS:
            UUID = autoclass("java.util.UUID")
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            self._uuid = UUID.fromString(SPP_UUID)
            self._adapter = BluetoothAdapter.getDefaultAdapter()

    def is_bluetooth_enabled(self) -> bool:
        if not HAS_PYJNIUS or not self._adapter:
            return False
        return bool(self._adapter.isEnabled())

    def get_paired_devices(self) -> List[Dict[str, str]]:
        """Returns list of bonded (paired) Bluetooth devices."""
        devices = []
        if not HAS_PYJNIUS or not self._adapter:
            return devices

        try:
            bonded_devices = self._adapter.getBondedDevices().toArray()
            for dev in bonded_devices:
                name = dev.getName() or "Unknown Device"
                address = dev.getAddress()
                devices.append({"name": str(name), "address": str(address)})
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to get paired devices: {e}")
        return devices

    def start_server(self, callback: Optional[Callable[[bool, str], None]] = None):
        """Starts Bluetooth RFCOMM server listener on Android."""
        if not HAS_PYJNIUS or not self._adapter:
            if callback:
                callback(False, "Pyjnius or BluetoothAdapter not available on this platform")
            return

        def _listen():
            try:
                self._server_socket = self._adapter.listenUsingRfcommWithServiceRecord(
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

                device = socket.getRemoteDevice()
                self.peer_name = str(device.getName() or device.getAddress())

                if self.on_connected:
                    self.on_connected(self.peer_name)

                self._start_reader()
            except Exception as e:
                self._running = False
                if callback:
                    callback(False, str(e))
                if self.on_error:
                    self.on_error(f"Bluetooth Server Error: {e}")

        threading.Thread(target=_listen, daemon=True).start()

    def connect_to_device(self, device_address_or_info: str, callback: Optional[Callable[[bool, str], None]] = None):
        """Connects to a remote Android Bluetooth device by MAC address."""
        if not HAS_PYJNIUS or not self._adapter:
            if callback:
                callback(False, "Pyjnius or BluetoothAdapter not available on this platform")
            return

        def _connect():
            try:
                # Cancel discovery as it slows down connections
                self._adapter.cancelDiscovery()

                remote_device = self._adapter.getRemoteDevice(device_address_or_info)
                socket = remote_device.createRfcommSocketToServiceRecord(self._uuid)
                
                # Connect (blocking)
                socket.connect()

                self._client_socket = socket
                self._in_stream = socket.getInputStream()
                self._out_stream = socket.getOutputStream()
                self.is_connected = True
                self._running = True
                self.peer_name = str(remote_device.getName() or device_address_or_info)

                if callback:
                    callback(True, f"Connected to {self.peer_name}")
                if self.on_connected:
                    self.on_connected(self.peer_name)

                self._start_reader()
            except Exception as e:
                self.is_connected = False
                if callback:
                    callback(False, str(e))
                if self.on_error:
                    self.on_error(f"Bluetooth Connection Failed: {e}")

        threading.Thread(target=_connect, daemon=True).start()

    def _start_reader(self):
        """Continuously reads bytes from Bluetooth InputStream."""
        def _read_loop():
            # Create a 4096 byte buffer
            byte_array = bytearray(4096)
            while self._running and self._in_stream:
                try:
                    num_bytes = self._in_stream.read(byte_array)
                    if num_bytes > 0:
                        raw_data = bytes(byte_array[:num_bytes])
                        if self.on_packet_received:
                            self.on_packet_received(raw_data)
                    elif num_bytes == -1:
                        # Stream closed
                        break
                except Exception:
                    break

            self.disconnect()

        threading.Thread(target=_read_loop, daemon=True).start()

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

    def disconnect(self):
        self._running = False
        self.is_connected = False

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

        if self.on_disconnected:
            self.on_disconnected()
