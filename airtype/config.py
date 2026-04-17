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

# Unicode injection
UNICODE_CHAR_DELAY_MS = 10

# Model directory (local path from ModelScope download)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MODEL_DIR = _PROJECT_ROOT / "models" / "Qwen" / "Qwen3-ASR-1___7B"

# Win32 virtual-key codes and flags
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_CONTROL = 0x11
VK_V = 0x56
VK_SHIFT = 0x10
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_MENU = 0x12
VK_INSERT = 0x2D
KEYEVENTF_KEYUP = 0x0002
CONSOLE_WINDOW_CLASS = "ConsoleWindowClass"

# CJK keyboard layout IDs
CJK_LAYOUTS = {
    0x0804, 0x0404, 0x0411, 0x0412,
    0x0C04, 0x1004, 0x1404,
}
ENGLISH_US_LAYOUT = 0x0409

# Virtual-key code to display name mapping
_VK_NAMES = {
    VK_LCONTROL: "Ctrl", VK_RCONTROL: "Ctrl",
    VK_LWIN: "Win", VK_RWIN: "Win",
    VK_SHIFT: "Shift", VK_LSHIFT: "Shift", VK_RSHIFT: "Shift",
    VK_MENU: "Alt",
    0x41: "A", 0x42: "B", 0x43: "C", 0x44: "D", 0x45: "E",
    0x46: "F", 0x47: "G", 0x48: "H", 0x49: "I", 0x4A: "J",
    0x4B: "K", 0x4C: "L", 0x4D: "M", 0x4E: "N", 0x4F: "O",
    0x50: "P", 0x51: "Q", 0x52: "R", 0x53: "S", 0x54: "T",
    0x55: "U", 0x56: "V", 0x57: "W", 0x58: "X", 0x59: "Y",
    0x5A: "Z",
    0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4",
    0x35: "5", 0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9",
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Esc",
    0x20: "Space",
    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4",
    0x74: "F5", 0x75: "F6", 0x76: "F7", 0x77: "F8",
    0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",
    VK_CONTROL: "Ctrl",
}

BLOCKED_HOTKEY_COMBOS = [
    frozenset({VK_LCONTROL, 0x43}),   # Ctrl+C
    frozenset({VK_RCONTROL, 0x43}),
    frozenset({VK_LCONTROL, 0x56}),   # Ctrl+V
    frozenset({VK_RCONTROL, 0x56}),
    frozenset({VK_LCONTROL, 0x58}),   # Ctrl+X
    frozenset({VK_RCONTROL, 0x58}),
    frozenset({VK_LCONTROL, 0x5A}),   # Ctrl+Z
    frozenset({VK_RCONTROL, 0x5A}),
    frozenset({VK_LCONTROL, 0x41}),   # Ctrl+A
    frozenset({VK_RCONTROL, 0x41}),
    frozenset({VK_LCONTROL, 0x53}),   # Ctrl+S
    frozenset({VK_RCONTROL, 0x53}),
    frozenset({VK_LCONTROL, 0x57}),   # Ctrl+W
    frozenset({VK_RCONTROL, 0x57}),
    frozenset({VK_LCONTROL, 0x51}),   # Ctrl+Q
    frozenset({VK_RCONTROL, 0x51}),
    frozenset({VK_LCONTROL, 0x50}),   # Ctrl+P
    frozenset({VK_RCONTROL, 0x50}),
    frozenset({VK_LCONTROL, 0x4E}),   # Ctrl+N
    frozenset({VK_RCONTROL, 0x4E}),
    frozenset({VK_LCONTROL, 0x4F}),   # Ctrl+O
    frozenset({VK_RCONTROL, 0x4F}),
    frozenset({VK_LCONTROL, 0x46}),   # Ctrl+F
    frozenset({VK_RCONTROL, 0x46}),
    frozenset({VK_LCONTROL, 0x48}),   # Ctrl+H
    frozenset({VK_RCONTROL, 0x48}),
    frozenset({VK_LCONTROL, 0x52}),   # Ctrl+R
    frozenset({VK_RCONTROL, 0x52}),
    frozenset({VK_LCONTROL, 0x4C}),   # Ctrl+L
    frozenset({VK_RCONTROL, 0x4C}),
    frozenset({VK_LCONTROL, 0x54}),   # Ctrl+T
    frozenset({VK_RCONTROL, 0x54}),
    frozenset({0xA4, VK_V}),          # Alt+V
    frozenset({0xA5, VK_V}),
    frozenset({0xA4, 0x73}),          # Alt+F4
    frozenset({0xA5, 0x73}),
]


def vk_combo_to_display(vk_codes: list[int]) -> str:
    """Convert virtual-key codes to human-readable display names."""
    names = []
    for vk in sorted(vk_codes):
        name = _VK_NAMES.get(vk, f"0x{vk:02X}")
        if name not in names:
            names.append(name)
    return " + ".join(names)


# ISO 639-1 → Qwen ASR full language name
_LANGUAGE_ALIASES = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
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

# Default settings
DEFAULTS = {
    # ASR
    "language": "Chinese",
    "audio_device": None,
    "asr_model": str(LOCAL_MODEL_DIR),
    "injection_method": "clipboard",

    # LLM
    "llm_enabled": False,
    "api_base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "llm_system_prompt": LLM_SYSTEM_PROMPT,
    "hotwords": [],

    # Hotkey
    "hotkey": "ctrl+win",
    "hotkey_vk_codes": [VK_LCONTROL, VK_LWIN],
}


def load_settings() -> dict:
    """Load settings from JSON config file, merging with defaults."""
    settings = dict(DEFAULTS)
    try:
        saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        settings.update(saved)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    # Normalize ISO language codes to Qwen ASR full names
    lang = settings.get("language", "Chinese")
    settings["language"] = _LANGUAGE_ALIASES.get(lang, lang)
    return settings


def save_settings(settings: dict) -> None:
    """Persist settings to JSON config file."""
    CONFIG_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
