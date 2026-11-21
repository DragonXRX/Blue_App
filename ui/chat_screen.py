"""
Main Chat Screen:
Assembles WhatsApp-themed top bar, chat history list, and bottom input controls.
Integrates with Transport, Protocol, and MediaManager.
Uses clean standard typography (no emoji glyphs) to ensure flawless rendering across all platforms.
"""
import os
import time
import math
import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp

from config import (
    COLOR_TEAL_DARK, COLOR_TEAL_LIGHT, COLOR_GREEN_ACCENT,
    COLOR_CHAT_BG, COLOR_DISCONNECTED, CHUNK_SIZE,
    PKT_TEXT, PKT_AUDIO, PKT_VIDEO, PKT_PROGRESS
)
from core.protocol import Packet, PacketParser, TransferManager
from core.media_manager import MediaManager
from ui.components import TextMessageBubble, VoiceNoteBubble, VideoMessageBubble

class ChatScreen(Screen):
    def __init__(self, transport, **kwargs):
        super().__init__(**kwargs)
        self.transport = transport
        self.parser = PacketParser()
        self.media_manager = MediaManager()
        self.transfer_manager = TransferManager(save_dir=os.path.join(os.path.expanduser("~"), ".bluechat_cache", "media"))
        
        self.active_video_bubbles = {}  # file_id -> VideoMessageBubble
        self.current_playing_bubble = None

        # Build UI
        self._build_ui()
        self._setup_transport_callbacks()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        # 1. Top App Bar (WhatsApp Dark Teal)
        self.top_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(4), dp(8), dp(4)],
            spacing=dp(8)
        )
        with self.top_bar.canvas.before:
            Color(*COLOR_TEAL_DARK)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=lambda *_: setattr(self.top_bar_rect, 'pos', self.top_bar.pos),
                          size=lambda *_: setattr(self.top_bar_rect, 'size', self.top_bar.size))

        # Avatar / Badge
        avatar_lbl = Label(
            text="[P2P]",
            font_size="14sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(46), dp(38)),
            color=(0.9, 1.0, 0.9, 1.0)
        )
        self.top_bar.add_widget(avatar_lbl)

        # Contact Name & Status
        contact_box = BoxLayout(orientation="vertical")
        self.name_lbl = Label(
            text="BlueChat (Disconnected)",
            font_size="15sp",
            bold=True,
            halign="left",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        self.name_lbl.bind(size=lambda *_: setattr(self.name_lbl, 'text_size', self.name_lbl.size))

        self.status_lbl = Label(
            text="[Offline - Tap Devices]",
            font_size="11sp",
            halign="left",
            valign="middle",
            color=(0.85, 0.85, 0.85, 1.0)
        )
        self.status_lbl.bind(size=lambda *_: setattr(self.status_lbl, 'text_size', self.status_lbl.size))

        contact_box.add_widget(self.name_lbl)
        contact_box.add_widget(self.status_lbl)
        self.top_bar.add_widget(contact_box)

        # Top Bar Action Buttons
        self.server_btn = Button(
            text="Listen",
            size_hint=(None, None),
            size=(dp(70), dp(36)),
            background_color=COLOR_TEAL_LIGHT,
            color=(1, 1, 1, 1),
            font_size="12sp",
            bold=True
        )
        self.server_btn.bind(on_release=self._start_server_mode)
        self.top_bar.add_widget(self.server_btn)

        self.pair_btn = Button(
            text="Devices",
            size_hint=(None, None),
            size=(dp(75), dp(36)),
            background_color=COLOR_TEAL_LIGHT,
            color=(1, 1, 1, 1),
            font_size="12sp",
            bold=True
        )
        self.pair_btn.bind(on_release=self._show_paired_devices_dialog)
        self.top_bar.add_widget(self.pair_btn)

        root.add_widget(self.top_bar)

        # 2. Chat Messages Area (WhatsApp Wallpaper Background)
        chat_bg_layout = BoxLayout(orientation="vertical")
        with chat_bg_layout.canvas.before:
            Color(*COLOR_CHAT_BG)
            self.chat_rect = Rectangle(pos=chat_bg_layout.pos, size=chat_bg_layout.size)
        chat_bg_layout.bind(pos=lambda *_: setattr(self.chat_rect, 'pos', chat_bg_layout.pos),
                            size=lambda *_: setattr(self.chat_rect, 'size', chat_bg_layout.size))

        self.scroll_view = ScrollView(do_scroll_x=False)
        self.messages_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(10), dp(10), dp(10), dp(10)],
            spacing=dp(8)
        )
        self.messages_box.bind(minimum_height=self.messages_box.setter('height'))
        self.scroll_view.add_widget(self.messages_box)
        chat_bg_layout.add_widget(self.scroll_view)
        root.add_widget(chat_bg_layout)

        # 3. WhatsApp Bottom Input Bar
        self.input_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            padding=[dp(6), dp(6), dp(6), dp(6)],
            spacing=dp(6)
        )
        with self.input_bar.canvas.before:
            Color(0.95, 0.95, 0.95, 1.0)
            self.input_bar_rect = Rectangle(pos=self.input_bar.pos, size=self.input_bar.size)
        self.input_bar.bind(pos=lambda *_: setattr(self.input_bar_rect, 'pos', self.input_bar.pos),
                            size=lambda *_: setattr(self.input_bar_rect, 'size', self.input_bar.size))

        # Media / Video Attachment Button
        self.attach_btn = Button(
            text="+",
            font_size="22sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(42), dp(40)),
            background_color=(0.85, 0.85, 0.85, 1.0),
            color=(0.2, 0.2, 0.2, 1.0)
        )
        self.attach_btn.bind(on_release=self._open_file_picker)
        self.input_bar.add_widget(self.attach_btn)

        # Text input field
        self.text_input = TextInput(
            hint_text="Type a message...",
            multiline=False,
            font_size="15sp",
            size_hint_y=None,
            height=dp(40),
            padding=[dp(10), dp(8), dp(10), dp(8)]
        )
        self.text_input.bind(on_text_validate=lambda *_: self._send_text_message())
        self.input_bar.add_widget(self.text_input)

        # Voice Note Record Button
        self.mic_btn = Button(
            text="Mic",
            font_size="13sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(46), dp(40)),
            background_color=COLOR_TEAL_LIGHT,
            color=(1, 1, 1, 1)
        )
        self.mic_btn.bind(on_release=self._toggle_voice_record)
        self.input_bar.add_widget(self.mic_btn)

        # Send Button (WhatsApp Green Accent)
        self.send_btn = Button(
            text="Send",
            font_size="13sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(56), dp(40)),
            background_color=COLOR_GREEN_ACCENT,
            color=(1, 1, 1, 1)
        )
        self.send_btn.bind(on_release=lambda *_: self._send_text_message())
        self.input_bar.add_widget(self.send_btn)

        root.add_widget(self.input_bar)
        self.add_widget(root)

    def _setup_transport_callbacks(self):
        self.transport.on_connected = self._on_connected
        self.transport.on_disconnected = self._on_disconnected
        self.transport.on_packet_received = self._on_raw_data_received
        self.transport.on_error = self._on_transport_error

    def _on_connected(self, peer_name):
        Clock.schedule_once(lambda dt: self._update_connection_ui(True, peer_name))

    def _on_disconnected(self):
        Clock.schedule_once(lambda dt: self._update_connection_ui(False, ""))

    def _update_connection_ui(self, is_connected: bool, peer_name: str):
        if is_connected:
            self.name_lbl.text = peer_name or "Connected Peer"
            self.status_lbl.text = "[Online]"
            self.status_lbl.color = COLOR_GREEN_ACCENT
        else:
            self.name_lbl.text = "BlueChat (Disconnected)"
            self.status_lbl.text = "[Offline - Tap Devices]"
            self.status_lbl.color = (0.8, 0.2, 0.2, 1.0)

    def _on_transport_error(self, err_msg: str):
        Clock.schedule_once(lambda dt: setattr(self.status_lbl, 'text', f"Error: {err_msg[:30]}"))

    def _on_raw_data_received(self, raw_bytes: bytes):
        self.parser.feed(raw_bytes)
        while True:
            pkt = self.parser.next_packet()
            if not pkt:
                break
            self._handle_packet(pkt)

    def _handle_packet(self, pkt):
        import json
        if pkt.pkt_type == PKT_TEXT:
            try:
                data = json.loads(pkt.payload.decode("utf-8"))
                text = data.get("text", "")
                timestamp_str = time.strftime("%H:%M", time.localtime(data.get("timestamp", time.time())))
                Clock.schedule_once(lambda dt: self._add_text_bubble(text, timestamp_str, is_outgoing=False))
            except Exception as e:
                print(f"[ChatScreen] Error parsing text packet: {e}")

        elif pkt.pkt_type in (PKT_AUDIO, PKT_VIDEO):
            try:
                meta = json.loads(pkt.payload.decode("utf-8"))
                file_id = meta.get("file_id")
                filename = meta.get("filename")
                total_size = meta.get("size", 0)
                duration = meta.get("duration", 0.0)

                filepath = self.transfer_manager.start_incoming(
                    file_id=file_id,
                    filename=filename,
                    total_size=total_size,
                    pkt_type=pkt.pkt_type,
                    duration=duration
                )

                timestamp_str = time.strftime("%H:%M")
                if pkt.pkt_type == PKT_VIDEO:
                    Clock.schedule_once(lambda dt: self._add_incoming_video_bubble(file_id, filepath, filename, total_size, timestamp_str))
            except Exception as e:
                print(f"[ChatScreen] Error receiving media meta: {e}")

        elif pkt.pkt_type == PKT_PROGRESS:
            import struct
            header_size = struct.calcsize(">12sII")
            if len(pkt.payload) >= header_size:
                file_id_raw, chunk_idx, total_chunks = struct.unpack_from(">12sII", pkt.payload, 0)
                file_id = file_id_raw.decode("utf-8", errors="ignore").strip()
                chunk_data = pkt.payload[header_size:]

                finished_info, progress, is_complete = self.transfer_manager.write_chunk(file_id, chunk_data)

                # Update video bubble progress if present
                if file_id in self.active_video_bubbles:
                    bubble = self.active_video_bubbles[file_id]
                    Clock.schedule_once(lambda dt, b=bubble, p=progress*100: b.set_progress(p))

                if is_complete and finished_info:
                    if finished_info["type"] == PKT_AUDIO:
                        timestamp_str = time.strftime("%H:%M")
                        Clock.schedule_once(lambda dt: self._add_voice_bubble(
                            finished_info["filepath"],
                            finished_info["duration"],
                            timestamp_str,
                            is_outgoing=False
                        ))

    def _send_text_message(self):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""

        pkt = Packet.create_text_packet(text=text, sender_name="Me")
        success = self.transport.send_data(pkt.pack())
        if success or not self.transport.is_connected:
            timestamp_str = time.strftime("%H:%M")
            self._add_text_bubble(text, timestamp_str, is_outgoing=True)

    def _add_text_bubble(self, text: str, timestamp_str: str, is_outgoing: bool):
        bubble = TextMessageBubble(text=text, timestamp_str=timestamp_str, is_outgoing=is_outgoing)
        self.messages_box.add_widget(bubble)
        self._scroll_to_bottom()

    def _add_voice_bubble(self, filepath: str, duration: float, timestamp_str: str, is_outgoing: bool):
        bubble = VoiceNoteBubble(
            filepath=filepath,
            duration=duration,
            timestamp_str=timestamp_str,
            is_outgoing=is_outgoing,
            on_play=self._handle_voice_play
        )
        self.messages_box.add_widget(bubble)
        self._scroll_to_bottom()

    def _add_incoming_video_bubble(self, file_id: str, filepath: str, filename: str, file_size: int, timestamp_str: str):
        bubble = VideoMessageBubble(
            filepath=filepath,
            filename=filename,
            file_size=file_size,
            timestamp_str=timestamp_str,
            is_outgoing=False,
            on_open_video=self._open_video_file
        )
        bubble.set_progress(0)
        self.active_video_bubbles[file_id] = bubble
        self.messages_box.add_widget(bubble)
        self._scroll_to_bottom()

    def _handle_voice_play(self, bubble):
        if self.current_playing_bubble and self.current_playing_bubble != bubble:
            self.current_playing_bubble.set_playing(False)
            self.media_manager.stop_audio()

        if bubble.is_playing:
            bubble.set_playing(False)
            self.media_manager.stop_audio()
            self.current_playing_bubble = None
        else:
            bubble.set_playing(True)
            self.current_playing_bubble = bubble
            self.media_manager.play_audio(bubble.filepath)

    def _open_video_file(self, filepath: str):
        """Attempts to open or preview the received video file."""
        if not os.path.exists(filepath):
            return
        try:
            if os.name == 'nt':
                os.startfile(filepath)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', filepath])
        except Exception as e:
            print(f"[ChatScreen] Cannot open video: {e}")

    def _toggle_voice_record(self, *args):
        if not self.media_manager.is_recording:
            # Start recording
            self.media_manager.start_voice_recording()
            self.mic_btn.text = "STOP"
            self.mic_btn.background_color = (0.9, 0.2, 0.2, 1.0)
            self.status_lbl.text = "[Recording Voice Note...]"
        else:
            # Stop recording and send
            filepath, duration = self.media_manager.stop_voice_recording()
            self.mic_btn.text = "Mic"
            self.mic_btn.background_color = COLOR_TEAL_LIGHT
            self.status_lbl.text = "[Online]" if self.transport.is_connected else "[Offline]"

            if filepath and os.path.exists(filepath):
                timestamp_str = time.strftime("%H:%M")
                self._add_voice_bubble(filepath, duration, timestamp_str, is_outgoing=True)
                threading.Thread(target=self._send_media_file, args=(filepath, PKT_AUDIO, duration), daemon=True).start()

    def _open_file_picker(self, *args):
        """Displays a file chooser popup to select a video/media file."""
        content = BoxLayout(orientation="vertical")
        file_chooser = FileChooserListView(path=os.path.expanduser("~"))
        content.add_widget(file_chooser)

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        select_btn = Button(text="Send File", background_color=COLOR_GREEN_ACCENT, bold=True)
        cancel_btn = Button(text="Cancel", background_color=(0.7, 0.7, 0.7, 1.0))

        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(select_btn)
        content.add_widget(btn_row)

        popup = Popup(title="Select Media File to Send", content=content, size_hint=(0.9, 0.9))

        def _on_select(*_):
            if file_chooser.selection:
                selected_file = file_chooser.selection[0]
                popup.dismiss()
                self._send_video_file(selected_file)

        select_btn.bind(on_release=_on_select)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _send_video_file(self, filepath: str):
        if not os.path.exists(filepath):
            return
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        timestamp_str = time.strftime("%H:%M")

        bubble = VideoMessageBubble(
            filepath=filepath,
            filename=filename,
            file_size=filesize,
            timestamp_str=timestamp_str,
            is_outgoing=True,
            on_open_video=self._open_video_file
        )
        self.messages_box.add_widget(bubble)
        self._scroll_to_bottom()

        threading.Thread(target=self._send_media_file, args=(filepath, PKT_VIDEO, 0.0, bubble), daemon=True).start()

    def _send_media_file(self, filepath: str, pkt_type: int, duration: float = 0.0, bubble_widget=None):
        import hashlib
        file_size = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        file_id = hashlib.md5(f"{filename}_{time.time()}".encode()).hexdigest()[:12]

        # 1. Send Metadata Packet
        meta_pkt = Packet.create_media_meta_packet(
            pkt_type=pkt_type,
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            duration=duration
        )
        self.transport.send_data(meta_pkt.pack())

        # 2. Send Chunks
        total_chunks = math.ceil(file_size / CHUNK_SIZE) if file_size > 0 else 1
        with open(filepath, "rb") as f:
            chunk_idx = 0
            sent_bytes = 0
            while True:
                chunk_data = f.read(CHUNK_SIZE)
                if not chunk_data:
                    break
                chunk_pkt = Packet.create_chunk_packet(
                    file_id=file_id,
                    chunk_index=chunk_idx,
                    total_chunks=total_chunks,
                    chunk_data=chunk_data
                )
                self.transport.send_data(chunk_pkt.pack())
                sent_bytes += len(chunk_data)
                chunk_idx += 1

                # Update outgoing progress bar
                if bubble_widget and file_size > 0:
                    percent = (sent_bytes / file_size) * 100
                    Clock.schedule_once(lambda dt, p=percent: bubble_widget.set_progress(p))

                # Slight throttle to avoid overwhelming Bluetooth RFCOMM buffer
                time.sleep(0.01)

    def _show_paired_devices_dialog(self, *args):
        devices = self.transport.get_paired_devices()
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        
        scroll = ScrollView()
        dev_list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        dev_list_box.bind(minimum_height=dev_list_box.setter('height'))

        popup = Popup(
            title="Paired Devices (Tap to connect)",
            content=content,
            size_hint=(0.85, 0.7)
        )

        if not devices:
            dev_list_box.add_widget(Label(text="No paired devices found.\nPlease pair your phone first in Bluetooth settings.", size_hint_y=None, height=dp(60)))
        else:
            for dev in devices:
                btn = Button(
                    text=f"{dev['name']}\n({dev['address']})",
                    size_hint_y=None,
                    height=dp(50),
                    background_color=COLOR_TEAL_LIGHT
                )
                btn.bind(on_release=lambda *_, addr=dev['address']: self._connect_to_addr(addr, popup))
                dev_list_box.add_widget(btn)

        scroll.add_widget(dev_list_box)
        content.add_widget(scroll)

        close_btn = Button(text="Close", size_hint_y=None, height=dp(36))
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    def _connect_to_addr(self, address: str, popup: Popup):
        popup.dismiss()
        self.status_lbl.text = "[Connecting...]"
        self.status_lbl.color = (0.9, 0.6, 0.1, 1.0)
        self.transport.connect_to_device(address)

    def _start_server_mode(self, *args):
        self.status_lbl.text = "[Listening for connection...]"
        self.status_lbl.color = (0.9, 0.6, 0.1, 1.0)
        self.transport.start_server()

    def _scroll_to_bottom(self):
        Clock.schedule_once(lambda dt: setattr(self.scroll_view, 'scroll_y', 0), 0.1)
