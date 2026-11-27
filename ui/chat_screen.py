"""
Main Chat Screen (Telegram Blue Edition):
- Telegram Blue Header (#239ED8) with Circular Avatar & Typing Indicator.
- Telegram Chat Wallpaper (#E0E9F0) & Bubble Aesthetics.
- Floating Circular Send Button & Rounded Action Pills.
"""
import os
import time
import math
import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.effects.scroll import ScrollEffect
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.utils import platform

from config import (
    COLOR_TELEGRAM_BLUE, COLOR_TELEGRAM_DARK, COLOR_TELEGRAM_ACCENT,
    COLOR_CHAT_BG, COLOR_AVATAR_BG, CHUNK_SIZE,
    PKT_TEXT, PKT_AUDIO, PKT_VIDEO, PKT_IMAGE, PKT_PROGRESS,
    PKT_TYPING, PKT_PING, get_media_dir, get_default_picker_dir
)
from core.protocol import Packet, PacketParser, TransferManager
from core.media_manager import MediaManager
from ui.components import TextMessageBubble, VoiceNoteBubble, VideoMessageBubble, ImageMessageBubble

class ChatScreen(Screen):
    def __init__(self, transport, **kwargs):
        super().__init__(**kwargs)
        self.transport = transport
        self.parser = PacketParser()
        self.media_manager = MediaManager()
        self.transfer_manager = TransferManager(save_dir=get_media_dir())
        
        self.active_video_bubbles = {}
        self.current_playing_bubble = None
        self._last_typed_time = 0.0
        self._peer_typing_clear_event = None
        self._heartbeat_event = None
        self.keyboard_height = 0

        self._build_ui()
        self._setup_transport_callbacks()
        self._setup_keyboard_listener()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        # 1. Top App Bar (Telegram Modern Blue)
        self.top_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            padding=[dp(10), dp(6), dp(10), dp(6)],
            spacing=dp(8)
        )
        with self.top_bar.canvas.before:
            Color(*COLOR_TELEGRAM_BLUE)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=lambda *_: setattr(self.top_bar_rect, 'pos', self.top_bar.pos),
                          size=lambda *_: setattr(self.top_bar_rect, 'size', self.top_bar.size))

        # Telegram Circular Avatar
        avatar_box = BoxLayout(size_hint=(None, None), size=(dp(44), dp(44)))
        with avatar_box.canvas.before:
            Color(*COLOR_AVATAR_BG)
            self.avatar_circle = Ellipse(pos=avatar_box.pos, size=avatar_box.size)
        avatar_box.bind(pos=lambda *_: setattr(self.avatar_circle, 'pos', avatar_box.pos),
                        size=lambda *_: setattr(self.avatar_circle, 'size', avatar_box.size))
        
        avatar_text = Label(text="BC", bold=True, font_size="15sp", color=(1, 1, 1, 1))
        avatar_box.add_widget(avatar_text)
        self.top_bar.add_widget(avatar_box)

        # Contact Name & Status (Telegram Subtitle)
        contact_box = BoxLayout(orientation="vertical", spacing=dp(1))
        self.name_lbl = Label(
            text="BlueChat",
            font_size="16sp",
            bold=True,
            halign="left",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        self.name_lbl.bind(size=lambda *_: setattr(self.name_lbl, 'text_size', self.name_lbl.size))

        self.status_lbl = Label(
            text="offline",
            font_size="12sp",
            halign="left",
            valign="middle",
            color=(0.85, 0.94, 1.0, 1.0)
        )
        self.status_lbl.bind(size=lambda *_: setattr(self.status_lbl, 'text_size', self.status_lbl.size))

        contact_box.add_widget(self.name_lbl)
        contact_box.add_widget(self.status_lbl)
        self.top_bar.add_widget(contact_box)

        # Top Bar Action Buttons (Telegram Pill Styling)
        self.server_btn = Button(
            text="Listen",
            size_hint=(None, None),
            size=(dp(68), dp(34)),
            background_normal="",
            background_color=(0.18, 0.68, 0.92, 1.0),
            color=(1, 1, 1, 1),
            font_size="12sp",
            bold=True
        )
        with self.server_btn.canvas.before:
            Color(1, 1, 1, 0.25)
            self.server_btn_rect = RoundedRectangle(pos=self.server_btn.pos, size=self.server_btn.size, radius=[dp(17)])
        self.server_btn.bind(pos=lambda *_: setattr(self.server_btn_rect, 'pos', self.server_btn.pos),
                             size=lambda *_: setattr(self.server_btn_rect, 'size', self.server_btn.size))
        self.server_btn.bind(on_release=self._start_server_mode)
        self.top_bar.add_widget(self.server_btn)

        self.pair_btn = Button(
            text="Devices",
            size_hint=(None, None),
            size=(dp(72), dp(34)),
            background_normal="",
            background_color=(0.18, 0.68, 0.92, 1.0),
            color=(1, 1, 1, 1),
            font_size="12sp",
            bold=True
        )
        with self.pair_btn.canvas.before:
            Color(1, 1, 1, 0.25)
            self.pair_btn_rect = RoundedRectangle(pos=self.pair_btn.pos, size=self.pair_btn.size, radius=[dp(17)])
        self.pair_btn.bind(pos=lambda *_: setattr(self.pair_btn_rect, 'pos', self.pair_btn.pos),
                           size=lambda *_: setattr(self.pair_btn_rect, 'size', self.pair_btn.size))
        self.pair_btn.bind(on_release=self._show_paired_devices_dialog)
        self.top_bar.add_widget(self.pair_btn)

        self.clear_btn = Button(
            text="Clear",
            size_hint=(None, None),
            size=(dp(54), dp(34)),
            background_normal="",
            background_color=(0.18, 0.68, 0.92, 0.6),
            color=(1, 1, 1, 0.9),
            font_size="11sp"
        )
        self.clear_btn.bind(on_release=self._clear_chat)
        self.top_bar.add_widget(self.clear_btn)

        root.add_widget(self.top_bar)

        # 2. Chat Messages Area (Anchored to TOP without bouncing)
        chat_bg_layout = BoxLayout(orientation="vertical")
        with chat_bg_layout.canvas.before:
            Color(*COLOR_CHAT_BG)
            self.chat_rect = Rectangle(pos=chat_bg_layout.pos, size=chat_bg_layout.size)
        chat_bg_layout.bind(pos=lambda *_: setattr(self.chat_rect, 'pos', chat_bg_layout.pos),
                            size=lambda *_: setattr(self.chat_rect, 'size', chat_bg_layout.size))

        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            effect_cls=ScrollEffect,
            scroll_y=1
        )
        self.anchor_container = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            size_hint_y=None
        )
        self.messages_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(10), dp(10), dp(10), dp(10)],
            spacing=dp(8)
        )
        self.messages_box.bind(minimum_height=self._on_messages_height_change)
        self.anchor_container.add_widget(self.messages_box)
        self.scroll_view.add_widget(self.anchor_container)
        chat_bg_layout.add_widget(self.scroll_view)
        root.add_widget(chat_bg_layout)

        # 3. Telegram Bottom Input Bar (Floating White Pill)
        self.input_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(6), dp(8), dp(6)],
            spacing=dp(8)
        )
        with self.input_bar.canvas.before:
            Color(0.97, 0.98, 0.99, 1.0)
            self.input_bar_rect = Rectangle(pos=self.input_bar.pos, size=self.input_bar.size)
        self.input_bar.bind(pos=lambda *_: setattr(self.input_bar_rect, 'pos', self.input_bar.pos),
                            size=lambda *_: setattr(self.input_bar_rect, 'size', self.input_bar.size))

        # Media Attachment Button
        self.attach_btn = Button(
            text="+",
            font_size="22sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(42), dp(42)),
            background_normal="",
            background_color=(0.92, 0.94, 0.96, 1.0),
            color=COLOR_TELEGRAM_ACCENT
        )
        with self.attach_btn.canvas.before:
            Color(0.85, 0.90, 0.94, 1.0)
            self.attach_circle = Ellipse(pos=self.attach_btn.pos, size=self.attach_btn.size)
        self.attach_btn.bind(pos=lambda *_: setattr(self.attach_circle, 'pos', self.attach_btn.pos),
                             size=lambda *_: setattr(self.attach_circle, 'size', self.attach_btn.size))
        self.attach_btn.bind(on_release=self._open_file_picker)
        self.input_bar.add_widget(self.attach_btn)

        # Rounded Text Input Box (Telegram style)
        self.text_input = TextInput(
            hint_text="Message...",
            multiline=False,
            font_size="15sp",
            size_hint_y=None,
            height=dp(42),
            background_color=(1, 1, 1, 1),
            padding=[dp(12), dp(10), dp(12), dp(10)]
        )
        self.text_input.bind(text=self._on_input_text_change)
        self.text_input.bind(focus=self._on_input_focus_change)
        self.text_input.bind(on_text_validate=lambda *_: self._send_text_message())
        self.input_bar.add_widget(self.text_input)

        # Voice Record Button
        self.mic_btn = Button(
            text="Mic",
            font_size="13sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(44), dp(42)),
            background_normal="",
            background_color=(0.92, 0.94, 0.96, 1.0),
            color=COLOR_TELEGRAM_ACCENT
        )
        self.mic_btn.bind(on_release=self._toggle_voice_record)
        self.input_bar.add_widget(self.mic_btn)

        # Telegram Circular Floating Send Button
        self.send_btn = Button(
            text="Send",
            font_size="13sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(56), dp(42)),
            background_normal="",
            background_color=COLOR_TELEGRAM_ACCENT,
            color=(1, 1, 1, 1)
        )
        with self.send_btn.canvas.before:
            Color(*COLOR_TELEGRAM_ACCENT)
            self.send_rect = RoundedRectangle(pos=self.send_btn.pos, size=self.send_btn.size, radius=[dp(21)])
        self.send_btn.bind(pos=lambda *_: setattr(self.send_rect, 'pos', self.send_btn.pos),
                           size=lambda *_: setattr(self.send_rect, 'size', self.send_btn.size))
        self.send_btn.bind(on_release=lambda *_: self._send_text_message())
        self.input_bar.add_widget(self.send_btn)

        root.add_widget(self.input_bar)
        
        # Spacer widget at the bottom that dynamically expands to match keyboard height
        self.keyboard_spacer = Widget(size_hint_y=None, height=0)
        root.add_widget(self.keyboard_spacer)
        
        self.add_widget(root)

    def _setup_keyboard_listener(self):
        Window.bind(on_keyboard_height=self._on_keyboard_height_change)

    def _on_input_focus_change(self, instance, is_focused):
        if is_focused:
            # When user focuses input, if on_keyboard_height hasn't fired yet or returns 0 on some devices,
            # ensure input area is kept visible and scroll to bottom
            Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.15)
            Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.35)
        else:
            if self.keyboard_height == 0:
                self.keyboard_spacer.height = 0

    def _on_keyboard_height_change(self, window, height):
        self.keyboard_height = max(0, height)
        # Update spacer height so the input bar is elevated exactly above the keyboard
        self.keyboard_spacer.height = self.keyboard_height
        if self.keyboard_height > 0:
            Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.05)
            Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.2)

    def _setup_transport_callbacks(self):
        self.transport.on_connected = self._on_connected
        self.transport.on_disconnected = self._on_disconnected
        self.transport.on_packet_received = self._on_raw_data_received
        self.transport.on_error = self._on_transport_error
        if hasattr(self.transport, 'on_reconnecting_status'):
            self.transport.on_reconnecting_status = self._on_reconnecting_status

    def _on_reconnecting_status(self, status_msg: str):
        Clock.schedule_once(lambda dt: setattr(self.status_lbl, 'text', status_msg))

    def _on_connected(self, peer_name):
        Clock.schedule_once(lambda dt: self._update_connection_ui(True, peer_name))
        if not self._heartbeat_event:
            self._heartbeat_event = Clock.schedule_interval(self._send_heartbeat, 10.0)

    def _on_disconnected(self):
        Clock.schedule_once(lambda dt: self._update_connection_ui(False, ""))
        if self._heartbeat_event:
            self._heartbeat_event.cancel()
            self._heartbeat_event = None

    def _send_heartbeat(self, dt):
        if self.transport.is_connected:
            ping_pkt = Packet.create_ping_packet()
            self.transport.send_data(ping_pkt.pack())

    def _update_connection_ui(self, is_connected: bool, peer_name: str):
        if is_connected:
            self.name_lbl.text = peer_name or "Connected Peer"
            self.status_lbl.text = "online"
            self.status_lbl.color = (0.75, 0.95, 1.0, 1.0)
        else:
            self.name_lbl.text = "BlueChat"
            self.status_lbl.text = "offline"
            self.status_lbl.color = (0.85, 0.94, 1.0, 0.8)

    def _on_transport_error(self, err_msg: str):
        Clock.schedule_once(lambda dt: setattr(self.status_lbl, 'text', f"Error: {err_msg[:25]}"))

    def _on_input_text_change(self, instance, value):
        now = time.time()
        if now - self._last_typed_time > 1.5 and self.transport.is_connected:
            self._last_typed_time = now
            threading.Thread(target=self._send_typing_signal, args=(bool(value),), daemon=True).start()

    def _send_typing_signal(self, is_typing: bool):
        try:
            pkt = Packet.create_typing_packet(is_typing)
            self.transport.send_data(pkt.pack())
        except Exception:
            pass

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

        elif pkt.pkt_type == PKT_TYPING:
            try:
                data = json.loads(pkt.payload.decode("utf-8"))
                if data.get("is_typing"):
                    Clock.schedule_once(lambda dt: self._set_peer_typing(True))
                    if self._peer_typing_clear_event:
                        self._peer_typing_clear_event.cancel()
                    self._peer_typing_clear_event = Clock.schedule_once(lambda dt: self._set_peer_typing(False), 3.0)
            except Exception:
                pass

        elif pkt.pkt_type == PKT_PING:
            pass

        elif pkt.pkt_type in (PKT_AUDIO, PKT_VIDEO, PKT_IMAGE):
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
            import zlib
            header_size = struct.calcsize(">12sIIIB")
            if len(pkt.payload) >= header_size:
                file_id_raw, chunk_idx, total_chunks, chunk_crc, is_comp = struct.unpack_from(">12sIIIB", pkt.payload, 0)
                file_id = file_id_raw.decode("utf-8", errors="ignore").strip()
                chunk_data = pkt.payload[header_size:]

                # Decompress chunk if it was compressed by sender
                if is_comp == 1:
                    try:
                        chunk_data = zlib.decompress(chunk_data)
                    except Exception as e:
                        print(f"[ChatScreen] Error decompressing chunk: {e}")

                finished_info, progress, speed_kb, is_complete = self.transfer_manager.write_chunk(file_id, chunk_data, chunk_crc)

                if file_id in self.active_video_bubbles:
                    bubble = self.active_video_bubbles[file_id]
                    Clock.schedule_once(lambda dt, b=bubble, p=progress*100, s=speed_kb: b.set_progress(p, s))

                if is_complete and finished_info:
                    timestamp_str = time.strftime("%H:%M")
                    if finished_info["type"] == PKT_AUDIO:
                        Clock.schedule_once(lambda dt: self._add_voice_bubble(
                            finished_info["filepath"],
                            finished_info["duration"],
                            timestamp_str,
                            is_outgoing=False
                        ))
                    elif finished_info["type"] == PKT_IMAGE:
                        Clock.schedule_once(lambda dt: self._add_image_bubble(
                            finished_info["filepath"],
                            finished_info["filename"],
                            timestamp_str,
                            is_outgoing=False
                        ))

    def _set_peer_typing(self, is_typing: bool):
        if self.transport.is_connected:
            if is_typing:
                self.status_lbl.text = "typing..."
                self.status_lbl.color = (0.75, 1.0, 0.85, 1.0)
            else:
                self.status_lbl.text = "online"
                self.status_lbl.color = (0.75, 0.95, 1.0, 1.0)

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

    def _add_image_bubble(self, filepath: str, filename: str, timestamp_str: str, is_outgoing: bool):
        bubble = ImageMessageBubble(
            filepath=filepath,
            filename=filename,
            timestamp_str=timestamp_str,
            is_outgoing=is_outgoing,
            on_open_image=self._open_image_file
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

    def _open_image_file(self, filepath: str):
        self._open_media_native(filepath, "image/*")

    def _open_video_file(self, filepath: str):
        self._open_media_native(filepath, "video/*")

    def _open_media_native(self, filepath: str, mime_type: str):
        if not os.path.exists(filepath):
            return
        if platform == "android":
            try:
                from jnius import autoclass, cast
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                File = autoclass("java.io.File")
                
                file_obj = File(filepath)
                intent = Intent(Intent.ACTION_VIEW)
                uri = Uri.fromFile(file_obj)
                intent.setDataAndType(uri, mime_type)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                currentActivity = cast("android.app.Activity", PythonActivity.mActivity)
                currentActivity.startActivity(intent)
                return
            except Exception as e:
                print(f"[ChatScreen] Android intent error: {e}")

        try:
            if os.name == 'nt':
                os.startfile(filepath)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', filepath])
        except Exception as e:
            print(f"[ChatScreen] Cannot open media: {e}")

    def _toggle_voice_record(self, *args):
        if not self.media_manager.is_recording:
            self.media_manager.start_voice_recording()
            self.mic_btn.text = "STOP"
            self.mic_btn.background_color = (0.9, 0.25, 0.25, 1.0)
            self.status_lbl.text = "recording..."
        else:
            filepath, duration = self.media_manager.stop_voice_recording()
            self.mic_btn.text = "Mic"
            self.mic_btn.background_color = (0.92, 0.94, 0.96, 1.0)
            self.status_lbl.text = "online" if self.transport.is_connected else "offline"

            if filepath and os.path.exists(filepath):
                timestamp_str = time.strftime("%H:%M")
                self._add_voice_bubble(filepath, duration, timestamp_str, is_outgoing=True)
                threading.Thread(target=self._send_media_file, args=(filepath, PKT_AUDIO, duration), daemon=True).start()

    def _open_file_picker(self, *args):
        content = BoxLayout(orientation="vertical")
        start_dir = get_default_picker_dir()
        file_chooser = FileChooserListView(
            path=start_dir,
            filters=["*.mp4", "*.mkv", "*.avi", "*.3gp", "*.jpg", "*.jpeg", "*.png"]
        )
        content.add_widget(file_chooser)

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        select_btn = Button(text="Send Media", background_normal="", background_color=COLOR_TELEGRAM_ACCENT, bold=True)
        cancel_btn = Button(text="Cancel", background_normal="", background_color=(0.7, 0.7, 0.7, 1.0))

        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(select_btn)
        content.add_widget(btn_row)

        popup = Popup(title="Select Media File to Send", content=content, size_hint=(0.9, 0.9))

        def _on_select(*_):
            if file_chooser.selection:
                selected_file = file_chooser.selection[0]
                popup.dismiss()
                ext = os.path.splitext(selected_file)[1].lower()
                if ext in [".jpg", ".jpeg", ".png"]:
                    self._send_image_file(selected_file)
                else:
                    self._send_video_file(selected_file)

        select_btn.bind(on_release=_on_select)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _send_image_file(self, filepath: str):
        if not os.path.exists(filepath):
            return
        filename = os.path.basename(filepath)
        timestamp_str = time.strftime("%H:%M")

        bubble = ImageMessageBubble(
            filepath=filepath,
            filename=filename,
            timestamp_str=timestamp_str,
            is_outgoing=True,
            on_open_image=self._open_image_file
        )
        self.messages_box.add_widget(bubble)
        self._scroll_to_bottom()

        threading.Thread(target=self._send_media_file, args=(filepath, PKT_IMAGE, 0.0, None), daemon=True).start()

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

        meta_pkt = Packet.create_media_meta_packet(
            pkt_type=pkt_type,
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            duration=duration
        )
        self.transport.send_data(meta_pkt.pack())

        total_chunks = math.ceil(file_size / CHUNK_SIZE) if file_size > 0 else 1
        with open(filepath, "rb") as f:
            chunk_idx = 0
            sent_bytes = 0
            start_t = time.time()
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

                if bubble_widget and file_size > 0:
                    percent = (sent_bytes / file_size) * 100
                    elapsed = max(0.01, time.time() - start_t)
                    speed_kbps = (sent_bytes / 1024.0) / elapsed
                    Clock.schedule_once(lambda dt, p=percent, s=speed_kbps: bubble_widget.set_progress(p, s))

                time.sleep(0.008)

    def _clear_chat(self, *args):
        self.messages_box.clear_widgets()
        self.active_video_bubbles.clear()
        self.scroll_view.scroll_y = 1

    def _show_paired_devices_dialog(self, *args):
        devices = self.transport.get_paired_devices()
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        
        scroll = ScrollView()
        dev_list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        dev_list_box.bind(minimum_height=dev_list_box.setter('height'))

        popup = Popup(
            title="Bluetooth Devices",
            content=content,
            size_hint=(0.85, 0.75)
        )

        def _populate_devices(dev_list):
            dev_list_box.clear_widgets()
            if not dev_list:
                dev_list_box.add_widget(Label(text="No devices found.\nMake sure Bluetooth is enabled.", size_hint_y=None, height=dp(60)))
            else:
                for dev in dev_list:
                    btn = Button(
                        text=f"{dev['name']}\n({dev['address']})",
                        size_hint_y=None,
                        height=dp(50),
                        background_normal="",
                        background_color=COLOR_TELEGRAM_BLUE
                    )
                    btn.bind(on_release=lambda *_, addr=dev['address']: self._connect_to_addr(addr, popup))
                    dev_list_box.add_widget(btn)

        _populate_devices(devices)
        scroll.add_widget(dev_list_box)
        content.add_widget(scroll)

        action_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        
        # Scan Nearby button (for Android discovery)
        scan_btn = Button(text="Scan Nearby", size_hint_x=0.6, background_normal="", background_color=COLOR_TELEGRAM_ACCENT, bold=True)
        def _on_scan_clicked(*_):
            if hasattr(self.transport, 'start_discovery'):
                scan_btn.text = "Scanning..."
                scan_btn.disabled = True
                def _on_discovered(discovered_list):
                    Clock.schedule_once(lambda dt: _populate_devices(discovered_list))
                    Clock.schedule_once(lambda dt: setattr(scan_btn, 'text', 'Scan Nearby'))
                    Clock.schedule_once(lambda dt: setattr(scan_btn, 'disabled', False))
                self.transport.start_discovery(on_device_found=_on_discovered)
            else:
                _populate_devices(self.transport.get_paired_devices())

        scan_btn.bind(on_release=_on_scan_clicked)
        action_row.add_widget(scan_btn)

        close_btn = Button(text="Close", size_hint_x=0.4, background_normal="", background_color=(0.5, 0.5, 0.5, 1.0))
        close_btn.bind(on_release=popup.dismiss)
        action_row.add_widget(close_btn)

        content.add_widget(action_row)
        popup.open()

    def _connect_to_addr(self, address: str, popup: Popup):
        popup.dismiss()
        self.status_lbl.text = "connecting..."
        self.status_lbl.color = (0.9, 0.95, 1.0, 1.0)
        self.transport.connect_to_device(address)

    def _start_server_mode(self, *args):
        self.status_lbl.text = "listening..."
        self.status_lbl.color = (0.9, 0.95, 1.0, 1.0)
        self.transport.start_server()

    def _on_messages_height_change(self, instance, min_height):
        instance.height = min_height
        # Anchor container matches screen height or message height to lock messages cleanly to the top
        self.anchor_container.height = max(self.scroll_view.height, min_height)

    def _scroll_to_bottom(self):
        # Prevent bounce/jumping: only scroll when content exceeds screen height
        if self.messages_box.height > self.scroll_view.height:
            self.scroll_view.scroll_y = 0
