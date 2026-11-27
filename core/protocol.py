"""
Binary packet framing and message protocol for Bluetooth RFCOMM transport.
Enhanced with CRC32 chunk verification, Typing indicator, and Image support.
"""
import struct
import json
import time
import os
import zlib
import hashlib
from config import (
    MAGIC_HEADER, PROTOCOL_VERSION, PKT_TEXT, PKT_AUDIO,
    PKT_VIDEO, PKT_IMAGE, PKT_PROGRESS, PKT_TYPING,
    PKT_PING, CHUNK_SIZE
)

# Packet Header format: 
# 2 bytes magic (BC) + 1 byte version + 1 byte type + 4 bytes payload length (Big Endian)
# Total header length: 8 bytes
HEADER_FMT = ">2sBBI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

class Packet:
    def __init__(self, pkt_type: int, payload: bytes):
        self.pkt_type = pkt_type
        self.payload = payload

    def pack(self) -> bytes:
        header = struct.pack(HEADER_FMT, MAGIC_HEADER, PROTOCOL_VERSION, self.pkt_type, len(self.payload))
        return header + self.payload

    @staticmethod
    def create_text_packet(text: str, sender_name: str = "User") -> 'Packet':
        payload_data = {
            "type": "text",
            "text": text,
            "sender": sender_name,
            "timestamp": time.time(),
            "msg_id": hashlib.md5(f"{text}_{time.time()}".encode()).hexdigest()[:12]
        }
        return Packet(PKT_TEXT, json.dumps(payload_data).encode("utf-8"))

    @staticmethod
    def create_typing_packet(is_typing: bool) -> 'Packet':
        payload_data = {"is_typing": is_typing, "timestamp": time.time()}
        return Packet(PKT_TYPING, json.dumps(payload_data).encode("utf-8"))

    @staticmethod
    def create_ping_packet() -> 'Packet':
        return Packet(PKT_PING, b"PING")

    @staticmethod
    def create_media_meta_packet(pkt_type: int, file_id: str, filename: str, file_size: int, duration: float = 0.0) -> 'Packet':
        payload_data = {
            "file_id": file_id,
            "filename": filename,
            "size": file_size,
            "duration": duration,
            "timestamp": time.time()
        }
        return Packet(pkt_type, json.dumps(payload_data).encode("utf-8"))

    @staticmethod
    def create_chunk_packet(file_id: str, chunk_index: int, total_chunks: int, chunk_data: bytes) -> 'Packet':
        file_id_bytes = file_id.encode("utf-8")[:12].ljust(12, b" ")
        chunk_crc = zlib.crc32(chunk_data) & 0xffffffff

        # Fast compression (level 1) to reduce Bluetooth transmission time
        compressed = zlib.compress(chunk_data, level=1)
        if len(compressed) < len(chunk_data):
            is_comp = 1
            payload_data = compressed
        else:
            is_comp = 0
            payload_data = chunk_data

        chunk_header = struct.pack(">12sIIIB", file_id_bytes, chunk_index, total_chunks, chunk_crc, is_comp)
        return Packet(PKT_PROGRESS, chunk_header + payload_data)


class PacketParser:
    """
    Parses a continuous stream of incoming bytes into individual packets.
    Handles partial reads and stream fragmentation naturally.
    """
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data: bytes):
        self.buffer.extend(data)

    def next_packet(self):
        if len(self.buffer) < HEADER_SIZE:
            return None

        magic, version, pkt_type, payload_len = struct.unpack_from(HEADER_FMT, self.buffer, 0)
        
        # Verify Magic header
        if magic != MAGIC_HEADER:
            # Shift buffer forward by 1 byte to find alignment if stream is corrupted
            self.buffer.pop(0)
            return None

        total_packet_size = HEADER_SIZE + payload_len
        if len(self.buffer) < total_packet_size:
            # Waiting for more bytes to complete payload
            return None

        # Full packet ready
        payload = bytes(self.buffer[HEADER_SIZE:total_packet_size])
        del self.buffer[:total_packet_size]
        return Packet(pkt_type, payload)


class TransferManager:
    """
    Manages incoming file transfers (Audio, Video, Images) across multiple chunks with CRC32 checks.
    """
    def __init__(self, save_dir: str):
        self.save_dir = save_dir
        self.active_transfers = {}  # file_id -> {meta, file_handle, received_bytes, total_bytes, start_time}

    def start_incoming(self, file_id: str, filename: str, total_size: int, pkt_type: int, duration: float = 0.0):
        filepath = os.path.join(self.save_dir, f"{file_id}_{filename}")
        f = open(filepath, "wb")
        self.active_transfers[file_id] = {
            "filepath": filepath,
            "filename": filename,
            "total_size": total_size,
            "received_bytes": 0,
            "handle": f,
            "type": pkt_type,
            "duration": duration,
            "start_time": time.time(),
            "last_calc_time": time.time(),
            "last_bytes": 0,
            "speed": 0.0
        }
        return filepath

    def write_chunk(self, file_id: str, chunk_data: bytes, expected_crc: int = 0):
        if file_id not in self.active_transfers:
            return None, 0.0, 0.0, False

        # Verify CRC32 if provided
        if expected_crc != 0:
            actual_crc = zlib.crc32(chunk_data) & 0xffffffff
            if actual_crc != expected_crc:
                print(f"[TransferManager] Warning: CRC mismatch on chunk for {file_id}")

        transfer = self.active_transfers[file_id]
        transfer["handle"].write(chunk_data)
        transfer["received_bytes"] += len(chunk_data)
        
        now = time.time()
        elapsed = now - transfer["last_calc_time"]
        if elapsed >= 0.5:
            delta_bytes = transfer["received_bytes"] - transfer["last_bytes"]
            transfer["speed"] = (delta_bytes / 1024.0) / elapsed
            transfer["last_calc_time"] = now
            transfer["last_bytes"] = transfer["received_bytes"]

        total = transfer["total_size"]
        progress = (transfer["received_bytes"] / total) if total > 0 else 1.0
        
        is_complete = transfer["received_bytes"] >= total
        if is_complete:
            transfer["handle"].close()
            finished_info = {
                "file_id": file_id,
                "filepath": transfer["filepath"],
                "filename": transfer["filename"],
                "type": transfer["type"],
                "duration": transfer["duration"]
            }
            del self.active_transfers[file_id]
            return finished_info, 1.0, transfer["speed"], True
        
        return None, progress, transfer["speed"], False
