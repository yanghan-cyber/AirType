# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AirType is a Windows-only voice input application that sits in the system tray. The user holds a configurable hotkey (default Ctrl+Win) to record, releases to transcribe via Qwen3-ASR, and the recognized text is injected into the foreground application. An optional LLM refinement step fixes homophone errors before injection.

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
User presses hotkey → _HotkeyRelay (WH_KEYBOARD_LL hook via ctypes/user32)
  → key_pressed signal → AirTypeApp._start_recording()
    → save_target_window()     # remembers the foreground window
    → AudioCapture.start()     # sounddevice InputStream, collects PCM + emits rms_updated
    → FloatingCapsule.show_entry()  # animated capsule overlay with waveform bars

User releases hotkey → key_released signal → AirTypeApp._stop_recording()
  → AudioCapture.stop() → returns raw PCM bytes
  → ASREngine.transcribe(pcm)  # Qwen3-ASR in a background thread
    → final_text signal
      → (if LLM enabled) LLMRefiner.refine() → OpenAI-compatible API in QThread
        → refined signal → inject_text()
      → (else) → inject_text() directly
    → inject_text()  # clipboard Ctrl+V or unicode SendInput, handles CJK IME switching
```

### Module Responsibilities

| Module | Role |
|---|---|
| `main.py` | `AirTypeApp` controller + `_HotkeyRelay` (WH_KEYBOARD_LL hook). Wires all signals. |
| `config.py` | Constants (audio, animation, VK codes, CJK layouts), `load_settings`/`save_settings`. |
| `audio_capture.py` | `sounddevice.InputStream` callback: buffers PCM, per-bar RMS with attack/release envelope. |
| `asr_engine.py` | Loads Qwen3-ASR model on a background thread, transcribes PCM → text. |
| `llm_refiner.py` | Optional post-processing via OpenAI-compatible API in `QThread`. |
| `text_injector.py` | Dual injection: clipboard (Ctrl+V/Shift+Insert) and unicode (SendInput + KEYEVENTF_UNICODE). CJK IME layout switching. |
| `floating_capsule.py` | Frameless always-on-top widget with waveform bars, spinner, live text. `QPainter` + `QPropertyAnimation`. |
| `tray_icon.py` | `QSystemTrayIcon` with context menu: LLM toggle, settings, quit. |
| `settings_dialog.py` | 5-page settings dialog (ASR, LLM, Hotkey, Appearance, About) with sidebar nav. Hotkey recording uses a temporary WH_KEYBOARD_LL hook. |
| `watchdog.py` | GUI thread hang monitor: heartbeat QTimer + background thread, dumps stacks to log. |

### Key Technical Details

- **Windows-only**: Uses `ctypes.windll.user32` for keyboard hooks, window focus, layout switching, simulated keystrokes. Not portable.
- **Threading**: ASR and LLM run on background threads/`QThread`. All UI updates via Qt signals with `QueuedConnection`.
- **CJK IME handling**: `text_injector` temporarily switches to English US layout before injection to prevent IME interference.
- **Config paths**: Settings → `%APPDATA%/AirType/settings.json`, Watchdog log → `%APPDATA%/AirType/watchdog.log`.
- **ASR model**: Default at `models/Qwen/Qwen3-ASR-1___7B` relative to project root.

## Win32/ctypes Gotchas

- **WH_KEYBOARD_LL reports specific VK codes**: Physical Ctrl key → `VK_LCONTROL` (0xA2), not `VK_CONTROL` (0x11). Same for Alt (`0xA4`/`0xA5` vs `0x12`). Always use the specific codes in hook logic and blocked combo checks.
- **SendInput `_INPUT` struct must be 40 bytes on x64**: The union must be padded to 32 bytes (MOUSEINPUT size) with a `c_byte * 32` member. `dwExtraInfo` must be `c_size_t` (not `POINTER(c_ulong)`), otherwise SendInput returns 0.
- **Hook blocking condition**: Only block target keys when `_active` (full combo held). Blocking when any target key is held locks Ctrl system-wide.
- **`_wait(ms)` for delays**: Uses `QEventLoop` + `QTimer` instead of `time.sleep` to keep the Qt event loop alive during Win32 operations (text injection, IME switching).
- **Hotkey recording**: Temporarily pauses the main hook (`_HotkeyRelay.pause()`) and installs a separate WH_KEYBOARD_LL hook to capture keys. Must clean up on dialog close.

## Dependencies

PySide6, torch (CUDA), torchaudio, transformers, accelerate, qwen-asr, sounddevice, numpy, openai. Managed via `uv` + `pyproject.toml`. PyInstaller for exe build.
