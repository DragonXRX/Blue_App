"""
Desktop Simulation Transport:
Enables testing BlueChat on PC (Windows/Linux/Mac) without requiring an Android phone.
Uses local TCP sockets to mimic Bluetooth RFCOMM stream behavior.
"""
import socket
import threading
import time
from typing import List, Dict, Optional, Callable
from core.transport import BaseTransport
from config import DEFAULT_SIM_PORT_SERVER

class DesktopSimulatorTransport(BaseTransport):
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_SIM_PORT_SERVER):
        super().__init__()
        self.host = host
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self._running = False
        self._listener_thread: Optional[threading.Thread] = None
        self._recv_thread: Optional[threading.Thread] = None

    def get_paired_devices(self) -> List[Dict[str, str]]:
        # In simulation mode, simulate paired instances
        return [
            {"name": "Simulated Partner A (Port 8888)", "address": "127.0.0.1:8888"},
            {"name": "Simulated Partner B (Port 8889)", "address": "127.0.0.1:8889"},
            {"name": "Local Network Peer", "address": "127.0.0.1:8888"}
        ]

    def start_server(self, callback: Optional[Callable[[bool, str], None]] = None):
        """Starts a local TCP server acting like a Bluetooth Server Socket."""
        def _listen():
            try:
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_sock.bind((self.host, self.port))
                self.server_sock.listen(1)
                self._running = True
                if callback:
                    callback(True, f"Server listening on {self.host}:{self.port}")

                conn, addr = self.server_sock.accept()
                self.client_sock = conn
                self.is_connected = True
                self.peer_name = f"Simulator ({addr[0]}:{addr[1]})"

                if self.on_connected:
                    self.on_connected(self.peer_name)

                self._start_receiver()
            except Exception as e:
                self._running = False
                if callback:
                    callback(False, str(e))
                if self.on_error:
                    self.on_error(f"Server error: {e}")

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()

    def connect_to_device(self, device_address_or_info: str, callback: Optional[Callable[[bool, str], None]] = None):
        """Connects to a simulated peer."""
        def _connect():
            try:
                # Parse host and port
                parts = device_address_or_info.split(":")
                target_host = parts[0].strip()
                target_port = int(parts[1].strip()) if len(parts) > 1 else self.port

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((target_host, target_port))
                self.client_sock = sock
                self.is_connected = True
                self._running = True
                self.peer_name = f"Partner ({target_host}:{target_port})"

                if callback:
                    callback(True, f"Connected to {self.peer_name}")
                if self.on_connected:
                    self.on_connected(self.peer_name)

                self._start_receiver()
            except Exception as e:
                self.is_connected = False
                if callback:
                    callback(False, str(e))
                if self.on_error:
                    self.on_error(f"Connection failed: {e}")

        threading.Thread(target=_connect, daemon=True).start()

    def _start_receiver(self):
        def _recv_loop():
            while self._running and self.client_sock:
                try:
                    data = self.client_sock.recv(4096)
                    if not data:
                        # Peer disconnected
                        break
                    if self.on_packet_received:
                        self.on_packet_received(data)
                except Exception:
                    break

            self.is_connected = False
            if self.on_disconnected:
                self.on_disconnected()

        self._recv_thread = threading.Thread(target=_recv_loop, daemon=True)
        self._recv_thread.start()

    def send_data(self, data: bytes) -> bool:
        if not self.is_connected or not self.client_sock:
            return False
        try:
            self.client_sock.sendall(data)
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Send failed: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        self._running = False
        self.is_connected = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None

        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

        if self.on_disconnected:
            self.on_disconnected()
