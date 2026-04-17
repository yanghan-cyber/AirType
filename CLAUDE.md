# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AirType is a Windows-only voice input application that sits in the system tray. The user holds Ctrl+Win to record, releases to transcribe via Qwen3-ASR, and the recognized text is injected into the foreground application. An optional LLM refinement step fixes homophone errors before injection.

## Commands

```bash
# Run the app (requires activated .venv)
python -m airtype

# Set up environment (installs CUDA PyTorch + all deps, no exe)
powershell -File build.ps1 -NoExe

# Full build (venv + deps + PyInstaller exe)
powershell -File build.ps1

# Clean rebuild
powershell -File build.ps1 -Clean
```

PyTorch must be installed separately via `--index-url` for CUDA wheels (see `build.ps1` step 2/4). The `pyproject.toml` explicitly excludes torch from its dependency list for this reason.

## Architecture

All source code lives in `airtype/`. The application is a single-process PySide6 (Qt) app with no separate server or service.

### Signal Flow (recording lifecycle)

```
User presses Ctrl+Win → _HotkeyRelay (low-level keyboard hook via ctypes/user32)
  → key_pressed signal → AirTypeApp._start_recording()
    → save_target_window()     # remembers the foreground window
    → AudioCapture.start()     # sounddevice InputStream, collects PCM + emits rms_updated
    → FloatingCapsule.show_entry()  # animated capsule overlay with waveform bars

User releases Ctrl+Win → key_released signal → AirTypeApp._stop_recording()
  → AudioCapture.stop() → returns raw PCM bytes
  → ASREngine.transcribe(pcm)  # Qwen3-ASR in a background thread
    → final_text signal
      → (if LLM enabled) LLMRefiner.refine() → OpenAI-compatible API in QThread
        → refined signal → inject_text()
      → (else) → inject_text() directly
    → inject_text()  # clipboard → Ctrl+V / Shift+Insert, handles CJK IME switching
```

### Module Responsibilities

| Module | Role |
|---|---|
| `main.py` | `AirTypeApp` controller + `_HotkeyRelay` (WH_KEYBOARD_LL hook via ctypes). Wires all signals. |
| `config.py` | Constants (audio params, animation timings, VK codes, CJK layouts), `load_settings`/`save_settings` for `%APPDATA%/AirType/settings.json`. |
| `audio_capture.py` | `sounddevice.InputStream` callback: buffers PCM, computes per-bar RMS with attack/release envelope for waveform visualization. |
| `asr_engine.py` | Loads Qwen3-ASR model on a background thread, transcribes PCM → text. Requires `qwen_asr` package. |
| `llm_refiner.py` | Optional post-processing via OpenAI-compatible API. Uses `QThread` worker. Conservative homophone-fix-only prompt in `config.LLM_SYSTEM_PROMPT`. |
| `text_injector.py` | Clipboard-based text injection: saves clipboard, sets text, sends Ctrl+V (or Shift+Insert for console windows), restores clipboard. Handles CJK→English keyboard layout switching to avoid IME interference. |
| `floating_capsule.py` | Frameless, always-on-top Qt widget with waveform bars, spinner, and live transcription text. Custom painted with `QPainter`, animated via `QPropertyAnimation`. |
| `tray_icon.py` | `QSystemTrayIcon` with context menu: LLM toggle, settings dialog, quit. Programmatically drawn icon (no image files). |
| `settings_dialog.py` | `QDialog` for API base URL, API key, model name. Tests connection on save. |
| `watchdog.py` | Monitors GUI thread for hangs (heartbeat QTimer + background thread), dumps stack traces to `%APPDATA%/AirType/watchdog.log`. |

### Key Technical Details

- **Windows-only**: Uses `ctypes.windll.user32` for keyboard hooks, window focus, keyboard layout switching, and simulated keystrokes. Not portable.
- **Threading model**: ASR and LLM run on background threads/`QThread`. All UI updates go through Qt signals with `QueuedConnection` to stay on the main thread.
- **Hotkey suppression**: The keyboard hook blocks the Win key event when Ctrl is held (returns 1), preventing the Start Menu from opening.
- **CJK IME handling**: `text_injector` temporarily switches to English US layout before pasting to prevent IME composition from corrupting the injected text.
- **ASR model path**: Default model is at `models/Qwen/Qwen3-ASR-1___7B` relative to project root (local download from ModelScope).

## Dependencies

Key packages: PySide6, torch (CUDA), transformers, qwen-asr, sounddevice, numpy, openai. Managed via `uv` + `pyproject.toml`.
