"""Audio capture and real-time RMS calculation for waveform visualization."""

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal

from .config import SAMPLE_RATE, CHANNELS, CHUNK_SIZE, BAR_COUNT, BAR_WEIGHTS, ATTACK_FACTOR, RELEASE_FACTOR, JITTER_RANGE


class AudioCapture(QObject):
    """Captures audio in chunks and emits RMS-level data for waveform visualization.

    Signals:
        rms_updated(list): Emits a list of 5 float values (0.0-1.0) for the waveform bars.
    """

    rms_updated = Signal(list)

    def __init__(self):
        super().__init__()
        self._stream = None
        self._envelope = [0.0] * BAR_COUNT
        self._recording = False
        self._audio_buffer = bytearray()
        self._rng = np.random.default_rng()
        self._device = None

    def update_device(self, device_name: str | None):
        self._device = device_name if device_name else None

    def start(self):
        if self._recording:
            return
        self._recording = True
        self._envelope = [0.0] * BAR_COUNT
        self._audio_buffer.clear()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=CHUNK_SIZE,
            dtype="float32",
            callback=self._audio_callback,
            device=self._device,
        )
        self._stream.start()

    def stop(self) -> bytes:
        """Stop recording and return the captured PCM data (16-bit signed, 16kHz mono)."""
        if not self._recording:
            return b""
        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        pcm = bytes(self._audio_buffer)
        self._audio_buffer.clear()
        return pcm

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if not self._recording:
            return

        self._audio_buffer.extend((indata * 32767).astype(np.int16).tobytes())

        chunk_samples = indata[:, 0]
        n = len(chunk_samples)
        segment_size = max(1, n // BAR_COUNT)

        bar_levels = []
        for i in range(BAR_COUNT):
            seg = chunk_samples[i * segment_size : (i + 1) * segment_size]
            seg_rms = np.sqrt(np.mean(seg ** 2)) if len(seg) > 0 else 0.0
            bar_levels.append(min(1.0, seg_rms / 0.05) * BAR_WEIGHTS[i])

        for i in range(BAR_COUNT):
            target = bar_levels[i]
            if target > self._envelope[i]:
                self._envelope[i] += (target - self._envelope[i]) * ATTACK_FACTOR
            else:
                self._envelope[i] += (target - self._envelope[i]) * RELEASE_FACTOR

            jitter = self._rng.uniform(-JITTER_RANGE, JITTER_RANGE)
            bar_levels[i] = max(0.0, min(1.0, self._envelope[i] + jitter))

        self.rms_updated.emit(bar_levels)
