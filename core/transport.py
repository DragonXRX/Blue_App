"""
Base Transport abstraction for Bluetooth and local simulation.
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional, List, Dict

class BaseTransport(ABC):
    def __init__(self):
        # Callbacks
        self.on_connected: Optional[Callable[[str], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_packet_received: Optional[Callable[[bytes], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.is_connected = False
        self.peer_name = "Unknown"

    @abstractmethod
    def start_server(self, callback: Optional[Callable[[bool, str], None]] = None):
        """Start listening for incoming Bluetooth/socket connections."""
        pass

    @abstractmethod
    def connect_to_device(self, device_address_or_info: str, callback: Optional[Callable[[bool, str], None]] = None):
        """Connect to a selected remote device."""
        pass

    @abstractmethod
    def send_data(self, data: bytes) -> bool:
        """Send raw bytes over the connection."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close connection and clean up resources."""
        pass

    @abstractmethod
    def get_paired_devices(self) -> List[Dict[str, str]]:
        """Return list of available paired devices [{"name": ..., "address": ...}]."""
        pass
