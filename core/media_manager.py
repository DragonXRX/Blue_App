"""
Media manager for BlueChat:
Handles recording audio (Voice Notes), playing audio, and managing received videos.
Works across both Desktop (simulation) and Android platforms.
"""
import os
import time
import wave
import struct
import math
from config import MEDIA_DIR

# Kivy sound loader
try:
    from kivy.core.audio import SoundLoader
    HAS_KIVY_SOUND = True
except ImportError:
    SoundLoader = None
    HAS_KIVY_SOUND = False

# Try importing Android Audio Recorder via Pyjnius
try:
    from jnius import autoclass
    MediaRecorder = autoclass("android.media.MediaRecorder")
    AudioSource = autoclass("android.media.MediaRecorder$AudioSource")
    OutputFormat = autoclass("android.media.MediaRecorder$OutputFormat")
    AudioEncoder = autoclass("android.media.MediaRecorder$AudioEncoder")
    HAS_ANDROID_RECORDER = True
except Exception:
    HAS_ANDROID_RECORDER = False


class MediaManager:
    def __init__(self):
        self.is_recording = False
        self.record_start_time = 0.0
        self.current_record_path = ""
        self._android_recorder = None
        self._current_sound = None

    def start_voice_recording(self) -> str:
        """Starts recording a voice note. Returns the target file path."""
        file_id = f"voice_{int(time.time())}"
        self.current_record_path = os.path.join(MEDIA_DIR, f"{file_id}.wav")
        self.record_start_time = time.time()
        self.is_recording = True

        if HAS_ANDROID_RECORDER:
            try:
                self._android_recorder = MediaRecorder()
                self._android_recorder.setAudioSource(AudioSource.MIC)
                self._android_recorder.setOutputFormat(OutputFormat.THREE_GPP)
                self._android_recorder.setOutputFile(self.current_record_path)
                self._android_recorder.setAudioEncoder(AudioEncoder.AMR_NB)
                self._android_recorder.prepare()
                self._android_recorder.start()
                return self.current_record_path
            except Exception as e:
                print(f"[MediaManager] Android recorder error: {e}")
                self._android_recorder = None

        # Desktop / Fallback mode: recording simulated or standard WAV header
        return self.current_record_path

    def stop_voice_recording(self) -> tuple[str, float]:
        """Stops recording and returns (filepath, duration_in_seconds)."""
        if not self.is_recording:
            return "", 0.0

        duration = max(1.0, round(time.time() - self.record_start_time, 1))
        self.is_recording = False

        if HAS_ANDROID_RECORDER and self._android_recorder:
            try:
                self._android_recorder.stop()
                self._android_recorder.release()
            except Exception as e:
                print(f"[MediaManager] Error stopping Android recorder: {e}")
            self._android_recorder = None
        else:
            # Generate a clean audio WAV file if on desktop simulator without native mic
            if not os.path.exists(self.current_record_path) or os.path.getsize(self.current_record_path) == 0:
                self._generate_tone_wav(self.current_record_path, duration)

        return self.current_record_path, duration

    def _generate_tone_wav(self, filepath: str, duration: float):
        """Generates a pleasant voice-tone WAV file for desktop testing."""
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        with wave.open(filepath, "w") as wav_file:
            wav_file.setnchannels(1)        # Mono
            wav_file.setsampwidth(2)        # 16-bit
            wav_file.setframerate(sample_rate)
            raw_data = bytearray()
            for i in range(num_samples):
                # Harmonic tone mimicking a voice message
                t = float(i) / sample_rate
                value = int(12000 * math.sin(2 * math.pi * 440 * t) * math.exp(-t / (duration + 0.1)))
                raw_data.extend(struct.pack("<h", value))
            wav_file.writeframes(raw_data)

    def play_audio(self, filepath: str, on_complete_callback=None):
        """Plays an audio file using Kivy SoundLoader."""
        if not os.path.exists(filepath):
            return False

        if self._current_sound:
            self._current_sound.stop()

        if HAS_KIVY_SOUND and SoundLoader:
            sound = SoundLoader.load(filepath)
            if sound:
                self._current_sound = sound
                sound.play()
                return True
        return False

    def stop_audio(self):
        if self._current_sound:
            self._current_sound.stop()
            self._current_sound = None
