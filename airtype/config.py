"""Global configuration and constants for AirType."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "AirType"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION_MS = 160  # 10 chunks per second
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)

# Waveform settings
BAR_COUNT = 5
BAR_WEIGHTS = [0.5, 0.8, 1.0, 0.75, 0.55]
ATTACK_FACTOR = 0.40
RELEASE_FACTOR = 0.15
JITTER_RANGE = 0.04

# Animation timings (ms)
SPRING_DURATION = 350
TEXT_TRANSITION_DURATION = 250
EXIT_DURATION = 220

# Model directory (local path from ModelScope download)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MODEL_DIR = _PROJECT_ROOT / "models" / "Qwen" / "Qwen3-ASR-1___7B"

# Default settings
DEFAULTS = {
    "hotkey": "ctrl+win",
    "language": "zh",
    "llm_enabled": False,
    "api_base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "asr_model": str(LOCAL_MODEL_DIR),
}

# LLM system prompt
LLM_SYSTEM_PROMPT = (
    "You are a conservative text post-processor for speech recognition output in mixed Chinese-English. "
    "Your ONLY job is to fix OBVIOUS errors:\n"
    "- Homophone errors that make no semantic sense (e.g., 配森→Python, 杰森→JSON, 派森→Python).\n"
    "- English technical terms incorrectly transliterated into Chinese characters.\n"
    "\n"
    "CRITICAL RULES:\n"
    "- If the text is semantically coherent, return it EXACTLY as-is.\n"
    "- NEVER polish, rewrite, rephrase, or improve the text.\n"
    "- NEVER add punctuation, remove words, or change word order.\n"
    "- NEVER translate between languages.\n"
    "- When in doubt, return the original text unchanged.\n"
    "- Output ONLY the corrected text, nothing else."
)


def load_settings() -> dict:
    """Load settings from JSON config file, merging with defaults."""
    settings = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save_settings(settings: dict) -> None:
    """Persist settings to JSON config file."""
    CONFIG_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
