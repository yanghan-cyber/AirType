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

    def start(self):
        """Start recording audio."""
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
        )
        self._stream.start()

    def stop(self) -> bytes:
        """Stop recording audio and return the captured PCM data.

        Returns:
            Raw PCM bytes (16-bit signed integers, 16kHz mono).
        """
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
        """sounddevice stream callback — runs on audio thread."""
        if not self._recording:
            return

        # Accumulate raw audio for ASR
        pcm = (indata * 32767).astype(np.int16).tobytes()
        self._audio_buffer.extend(pcm)

        # Compute RMS
        rms = np.sqrt(np.mean(indata ** 2))

        # Normalize to 0-1 range — 0.08 threshold makes bars responsive to normal speech
        level = min(1.0, rms / 0.05)

        # Generate per-bar levels from the mono signal
        chunk_samples = indata[:, 0]
        n = len(chunk_samples)
        segment_size = max(1, n // BAR_COUNT)

        bar_levels = []
        for i in range(BAR_COUNT):
            seg = chunk_samples[i * segment_size : (i + 1) * segment_size]
            seg_rms = np.sqrt(np.mean(seg ** 2)) if len(seg) > 0 else 0.0
            bar_levels.append(min(1.0, seg_rms / 0.05) * BAR_WEIGHTS[i])

        # Apply attack/release envelope and jitter
        rng = np.random.default_rng()
        for i in range(BAR_COUNT):
            target = bar_levels[i]
            if target > self._envelope[i]:
                # Attack
                self._envelope[i] += (target - self._envelope[i]) * ATTACK_FACTOR
            else:
                # Release
                self._envelope[i] += (target - self._envelope[i]) * RELEASE_FACTOR

            # Jitter
            jitter = rng.uniform(-JITTER_RANGE, JITTER_RANGE)
            bar_levels[i] = max(0.0, min(1.0, self._envelope[i] + jitter))

        self.rms_updated.emit(bar_levels)
