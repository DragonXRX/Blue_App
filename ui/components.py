"""
UI components with Telegram aesthetic:
- Telegram Blue theme (#239ED8 / #28A7E5).
- Chat bubbles for Text, Voice Notes, Videos, and Photos.
- Crisp vector-styled circular action buttons and pill badges.
"""
import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp

from config import (
    COLOR_TELEGRAM_BLUE, COLOR_TELEGRAM_ACCENT, COLOR_BUBBLE_OUT,
    COLOR_BUBBLE_IN, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED
)

class BubbleBase(BoxLayout):
    """Base class for Telegram-style message bubbles with smooth rounded corners."""
    def __init__(self, is_outgoing: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.is_outgoing = is_outgoing
        self.orientation = "vertical"
        self.size_hint_y = None
        self.size_hint_x = 0.78
        self.padding = [dp(12), dp(8), dp(12), dp(8)]
        self.spacing = dp(4)

        # Telegram bubble colors: soft cyan-blue for outgoing, pure white for incoming
        self.bg_color = COLOR_BUBBLE_OUT if is_outgoing else COLOR_BUBBLE_IN
        self.pos_hint = {"right": 0.98} if is_outgoing else {"x": 0.02}

        # Corner radiuses: small tail on the sending side
        corner_radii = [dp(16), dp(16), dp(3) if is_outgoing else dp(16), dp(16) if is_outgoing else dp(3)]

        with self.canvas.before:
            self.color_instruction = Color(*self.bg_color)
            self.rect_instruction = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=corner_radii
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect_instruction.pos = self.pos
        self.rect_instruction.size = self.size


class TextMessageBubble(BubbleBase):
    """Telegram-style text message bubble."""
    def __init__(self, text: str, timestamp_str: str, is_outgoing: bool = True, **kwargs):
        super().__init__(is_outgoing=is_outgoing, **kwargs)

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
    """Telegram-style voice note bubble with circular play button."""
    def __init__(self, filepath: str, duration: float, timestamp_str: str, is_outgoing: bool = True, on_play=None, **kwargs):
        super().__init__(is_outgoing=is_outgoing, **kwargs)
        self.filepath = filepath
        self.duration = duration
        self.on_play = on_play
        self.is_playing = False
        self.height = dp(76)

        row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(42))

        # Telegram Circular Play/Pause button
        self.play_btn = Button(
            text="Play",
            font_size="12sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1)
        )
        with self.play_btn.canvas.before:
            Color(*COLOR_TELEGRAM_ACCENT)
            self.play_circle = Ellipse(pos=self.play_btn.pos, size=self.play_btn.size)
        self.play_btn.bind(pos=lambda *_: setattr(self.play_circle, 'pos', self.play_btn.pos),
                           size=lambda *_: setattr(self.play_circle, 'size', self.play_btn.size))
        self.play_btn.bind(on_release=self._toggle_play)
        row.add_widget(self.play_btn)

        # Voice info layout
        info_box = BoxLayout(orientation="vertical", spacing=dp(2))
        self.title_label = Label(
            text="Voice Message",
            color=COLOR_TELEGRAM_ACCENT,
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


class ImageMessageBubble(BubbleBase):
    """Telegram-style photo message bubble with rounded preview."""
    def __init__(self, filepath: str, filename: str, timestamp_str: str, is_outgoing: bool = True, on_open_image=None, **kwargs):
        super().__init__(is_outgoing=is_outgoing, **kwargs)
        self.filepath = filepath
        self.on_open_image = on_open_image
        self.height = dp(215)

        # Inline image view
        self.img_view = AsyncImage(
            source=filepath if os.path.exists(filepath) else "",
            size_hint_y=None,
            height=dp(155),
            allow_stretch=True,
            keep_ratio=True
        )
        self.add_widget(self.img_view)

        # Bottom info row
        info_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(24))
        name_lbl = Label(
            text=filename[:20] + ("..." if len(filename) > 20 else ""),
            color=COLOR_TEXT_PRIMARY,
            font_size="12sp",
            halign="left"
        )
        name_lbl.bind(size=lambda *_: setattr(name_lbl, 'text_size', name_lbl.size))
        info_row.add_widget(name_lbl)

        time_text = f"{timestamp_str}  Read" if is_outgoing else timestamp_str
        time_lbl = Label(
            text=time_text,
            color=COLOR_TEXT_MUTED,
            font_size="11sp",
            halign="right"
        )
        time_lbl.bind(size=lambda *_: setattr(time_lbl, 'text_size', time_lbl.size))
        info_row.add_widget(time_lbl)

        self.add_widget(info_row)


class VideoMessageBubble(BubbleBase):
    """Telegram-style video message card with blue progress bar and watch action."""
    def __init__(self, filepath: str, filename: str, file_size: int, timestamp_str: str, is_outgoing: bool = True, on_open_video=None, **kwargs):
        super().__init__(is_outgoing=is_outgoing, **kwargs)
        self.filepath = filepath
        self.on_open_video = on_open_video
        self.height = dp(125)

        # Video Header Box
        header_box = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(36))
        video_tag = Label(
            text="[VIDEO]",
            color=COLOR_TELEGRAM_ACCENT,
            font_size="12sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(58), dp(36))
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
        self.size_label = Label(
            text=f"{size_kb} KB",
            color=COLOR_TEXT_MUTED,
            font_size="11sp",
            halign="left"
        )
        self.size_label.bind(size=lambda *_: setattr(self.size_label, 'text_size', self.size_label.size))

        meta_box.add_widget(name_label)
        meta_box.add_widget(self.size_label)
        header_box.add_widget(meta_box)
        self.add_widget(header_box)

        # Progress bar
        self.progress_bar = ProgressBar(max=100, value=100, size_hint_y=None, height=dp(10))
        self.add_widget(self.progress_bar)

        # Action button (Open / Watch Video)
        self.action_btn = Button(
            text="Play Video",
            size_hint_y=None,
            height=dp(30),
            background_normal="",
            background_color=COLOR_TELEGRAM_ACCENT,
            color=(1, 1, 1, 1),
            font_size="12sp",
            bold=True
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

    def set_progress(self, percent: float, speed_kbps: float = 0.0):
        self.progress_bar.value = percent
        if percent < 100:
            speed_txt = f" ({int(speed_kbps)} KB/s)" if speed_kbps > 0 else ""
            self.action_btn.text = f"Transferring {int(percent)}%{speed_txt}"
            self.action_btn.disabled = True
        else:
            self.action_btn.text = "Play Video"
            self.action_btn.disabled = False
