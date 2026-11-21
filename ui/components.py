"""
UI components with WhatsApp aesthetic:
- Chat bubbles for Text, Voice Notes, and Video files.
- Connection status header.
- Message input bar with voice note recorder and attachment picker.
Clean ASCII/standard typography to prevent missing glyph boxes on all platforms.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from config import (
    COLOR_TEAL_DARK, COLOR_TEAL_LIGHT, COLOR_GREEN_ACCENT,
    COLOR_BUBBLE_OUT, COLOR_BUBBLE_IN, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED
)

class BubbleBase(BoxLayout):
    """Base class for chat bubbles with WhatsApp-like rounded background."""
    def __init__(self, is_outgoing: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.is_outgoing = is_outgoing
        self.orientation = "vertical"
        self.size_hint_y = None
        self.size_hint_x = 0.75
        self.padding = [dp(12), dp(8), dp(12), dp(8)]
        self.spacing = dp(4)

        # Bubble color: light green for outgoing, white for incoming
        self.bg_color = COLOR_BUBBLE_OUT if is_outgoing else COLOR_BUBBLE_IN
        self.pos_hint = {"right": 0.98} if is_outgoing else {"x": 0.02}

        with self.canvas.before:
            self.color_instruction = Color(*self.bg_color)
            self.rect_instruction = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12), dp(12), dp(2) if is_outgoing else dp(12), dp(12) if is_outgoing else dp(2)]
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect_instruction.pos = self.pos
        self.rect_instruction.size = self.size


class TextMessageBubble(BubbleBase):
    """WhatsApp-style text message bubble."""
    def __init__(self, text: str, timestamp_str: str, is_outgoing: bool = True, **kwargs):
        super().__init__(is_outgoing=is_outgoing, **kwargs)

        # Text label
        self.text_label = Label(
            text=text,
            color=COLOR_TEXT_PRIMARY,
            font_size="15sp",
            size_hint_y=None,
            halign="right" if is_outgoing else "left",
            valign="middle"
        )
        self.text_label.bind(texture_size=self._update_label_size)
        self.add_widget(self.text_label)

        # Timestamp & Status
        time_text = f"{timestamp_str}  Read" if is_outgoing else timestamp_str
        self.time_label = Label(
            text=time_text,
            color=COLOR_TEXT_MUTED,
            font_size="11sp",
            size_hint_y=None,
            height=dp(16),
            halign="right",
            valign="bottom"
        )
        self.time_label.bind(size=lambda *_: setattr(self.time_label, 'text_size', self.time_label.size))
        self.add_widget(self.time_label)
        self.height = dp(60)

    def _update_label_size(self, *args):
        self.text_label.text_size = (self.width - dp(24), None)
        self.text_label.height = self.text_label.texture_size[1]
        self.height = self.text_label.height + dp(32)


class VoiceNoteBubble(BubbleBase):
    """WhatsApp-style voice note bubble with clean playback controls."""
    def __init__(self, filepath: str, duration: float, timestamp_str: str, is_outgoing: bool = True, on_play=None, **kwargs):
        super().__init__(is_outgoing=is_outgoing, **kwargs)
        self.filepath = filepath
        self.duration = duration
        self.on_play = on_play
        self.is_playing = False
        self.height = dp(75)

        row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(40))

        # Play/Pause button
        self.play_btn = Button(
            text="Play",
            font_size="13sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(48), dp(36)),
            background_color=COLOR_TEAL_LIGHT,
            color=(1, 1, 1, 1)
        )
        self.play_btn.bind(on_release=self._toggle_play)
        row.add_widget(self.play_btn)

        # Voice info layout
        info_box = BoxLayout(orientation="vertical", spacing=dp(2))
        self.title_label = Label(
            text="Voice Note",
            color=COLOR_TEAL_DARK,
            font_size="13sp",
            bold=True,
            halign="left"
        )
        self.title_label.bind(size=lambda *_: setattr(self.title_label, 'text_size', self.title_label.size))
        
        duration_mins = int(duration // 60)
        duration_secs = int(duration % 60)
        self.dur_label = Label(
            text=f"{duration_mins:02d}:{duration_secs:02d}",
            color=COLOR_TEXT_MUTED,
            font_size="11sp",
            halign="left"
        )
        self.dur_label.bind(size=lambda *_: setattr(self.dur_label, 'text_size', self.dur_label.size))

        info_box.add_widget(self.title_label)
        info_box.add_widget(self.dur_label)
        row.add_widget(info_box)

        self.add_widget(row)

        # Timestamp
        self.time_label = Label(
            text=f"{timestamp_str}  Read" if is_outgoing else timestamp_str,
            color=COLOR_TEXT_MUTED,
            font_size="11sp",
            size_hint_y=None,
            height=dp(16),
            halign="right"
        )
        self.time_label.bind(size=lambda *_: setattr(self.time_label, 'text_size', self.time_label.size))
        self.add_widget(self.time_label)

    def _toggle_play(self, *args):
        if self.on_play:
            self.on_play(self)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        self.play_btn.text = "Pause" if playing else "Play"


class VideoMessageBubble(BubbleBase):
    """WhatsApp-style video message bubble with filename, progress bar, and play action."""
    def __init__(self, filepath: str, filename: str, file_size: int, timestamp_str: str, is_outgoing: bool = True, on_open_video=None, **kwargs):
        super().__init__(is_outgoing=is_outgoing, **kwargs)
        self.filepath = filepath
        self.on_open_video = on_open_video
        self.height = dp(115)

        # Video Header Box
        header_box = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(36))
        video_tag = Label(
            text="[VIDEO]",
            color=COLOR_TEAL_DARK,
            font_size="12sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(55), dp(36))
        )
        header_box.add_widget(video_tag)

        meta_box = BoxLayout(orientation="vertical")
        name_label = Label(
            text=filename[:22] + ("..." if len(filename) > 22 else ""),
            color=COLOR_TEXT_PRIMARY,
            font_size="13sp",
            bold=True,
            halign="left"
        )
        name_label.bind(size=lambda *_: setattr(name_label, 'text_size', name_label.size))

        size_kb = round(file_size / 1024, 1)
        size_label = Label(
            text=f"{size_kb} KB",
            color=COLOR_TEXT_MUTED,
            font_size="11sp",
            halign="left"
        )
        size_label.bind(size=lambda *_: setattr(size_label, 'text_size', size_label.size))

        meta_box.add_widget(name_label)
        meta_box.add_widget(size_label)
        header_box.add_widget(meta_box)
        self.add_widget(header_box)

        # Progress bar
        self.progress_bar = ProgressBar(max=100, value=100, size_hint_y=None, height=dp(12))
        self.add_widget(self.progress_bar)

        # Action button (Open / Watch Video)
        self.action_btn = Button(
            text="Play Video",
            size_hint_y=None,
            height=dp(28),
            background_color=COLOR_TEAL_LIGHT,
            color=(1, 1, 1, 1),
            font_size="12sp"
        )
        self.action_btn.bind(on_release=lambda *_: self.on_open_video(self.filepath) if self.on_open_video else None)
        self.add_widget(self.action_btn)

        # Timestamp
        self.time_label = Label(
            text=f"{timestamp_str}  Read" if is_outgoing else timestamp_str,
            color=COLOR_TEXT_MUTED,
            font_size="11sp",
            size_hint_y=None,
            height=dp(14),
            halign="right"
        )
        self.time_label.bind(size=lambda *_: setattr(self.time_label, 'text_size', self.time_label.size))
        self.add_widget(self.time_label)

    def set_progress(self, percent: float):
        self.progress_bar.value = percent
        if percent < 100:
            self.action_btn.text = f"Transferring... {int(percent)}%"
            self.action_btn.disabled = True
        else:
            self.action_btn.text = "Play Video"
            self.action_btn.disabled = False
