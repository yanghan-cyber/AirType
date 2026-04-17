"""Qwen3-ASR transcription backend (transformers, Windows-compatible).

Uses Qwen3ASRModel.from_pretrained() with the transformers backend since
vLLM (required for streaming) does not support Windows. Audio is collected
during recording and transcribed in a background thread on release.
"""

import threading

import numpy as np
from PySide6.QtCore import QObject, Signal

from .config import SAMPLE_RATE

import logging
logging.getLogger("transformers").setLevel(logging.ERROR)

try:
    from qwen_asr import Qwen3ASRModel
    QWEN3_AVAILABLE = True
except ImportError:
    QWEN3_AVAILABLE = False


class ASREngine(QObject):
    """Manages Qwen3-ASR model lifecycle and transcription.

    Signals:
        partial_text(str): Emitted with status text during recording.
        final_text(str): Emitted with the completed transcription.
        model_loaded(): Emitted after the ASR model has finished loading.
        error(str): Emitted on errors.
    """

    partial_text = Signal(str)
    final_text = Signal(str)
    model_loaded = Signal()
    error = Signal(str)

    def __init__(self, model_name: str = "Qwen/Qwen3-ASR-1.7B", language: str = "Chinese"):
        super().__init__()
        self._model_name = model_name
        self._language = language
        self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def update_language(self, language: str):
        self._language = language

    def load_model(self):
        """Load the ASR model in a background thread."""
        if not QWEN3_AVAILABLE:
            self.error.emit("qwen_asr package not installed. Install from https://github.com/QwenLM/Qwen3-ASR")
            return

        def _load():
            try:
                import torch
                self._model = Qwen3ASRModel.from_pretrained(
                    self._model_name,
                    dtype=torch.bfloat16,
                    device_map="cuda:0",
                    max_new_tokens=4096,
                )
                self.model_loaded.emit()
            except Exception as e:
                self.error.emit(f"Failed to load ASR model: {e}")

        threading.Thread(target=_load, daemon=True).start()

    def transcribe(self, pcm_bytes: bytes):
        """Transcribe PCM audio data in a background thread.

        Args:
            pcm_bytes: Raw PCM data as 16-bit signed integers, 16kHz mono.
        """
        if not pcm_bytes or self._model is None:
            self.final_text.emit("")
            return

        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        model = self._model
        language = self._language

        def _run():
            try:
                results = model.transcribe(
                    audio=(audio, SAMPLE_RATE),
                    language=language,
                )
                text = results[0].text.strip() if results else ""
                self.final_text.emit(text)
            except Exception as e:
                self.error.emit(f"Transcription error: {e}")

        threading.Thread(target=_run, daemon=True).start()
