"""AirType main entry point — wires all modules together."""

import ctypes
import ctypes.wintypes
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Qt

from .config import load_settings
from .audio_capture import AudioCapture
from .asr_engine import ASREngine
from .llm_refiner import LLMRefiner
from .text_injector import inject_text, save_target_window
from .floating_capsule import FloatingCapsule
from .tray_icon import TrayIcon
from .watchdog import Watchdog

user32 = ctypes.windll.user32

STATUS_READY = "就绪 — 长按 Ctrl+Win 录音"
STATUS_LOADING = "正在加载 ASR 模型..."
STATUS_RECORDING = "录音中..."
STATUS_PROCESSING = "处理中..."
STATUS_REFINING = "正在优化..."

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
VK_LCONTROL = 0xA2
VK_LWIN = 0x5B
KEYEVENTF_KEYUP = 0x0002


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


# Callback type — use CFUNCTYPE (cdecl), same as the working debug script
_HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long, ctypes.c_int,
    ctypes.c_size_t, ctypes.c_size_t,
)

# Fix CallNextHookEx argument types for 64-bit Windows
user32.CallNextHookEx.argtypes = [
    ctypes.c_size_t,   # HHOOK
    ctypes.c_int,      # nCode
    ctypes.c_size_t,   # WPARAM
    ctypes.c_size_t,   # LPARAM
]
user32.CallNextHookEx.restype = ctypes.c_long
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int, _HOOKPROC, ctypes.c_size_t, ctypes.wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = ctypes.c_size_t
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_size_t]
user32.UnhookWindowsHookEx.restype = ctypes.c_int


class _HotkeyRelay(QObject):
    """Tracks left-Ctrl + left-Win via a native WH_KEYBOARD_LL hook.

    The Win key event is *blocked* (not forwarded to Windows) whenever
    Ctrl is held, so the Start Menu never opens. All other keys pass
    through unconditionally.
    """

    key_pressed = Signal()
    key_released = Signal()

    def __init__(self):
        super().__init__()
        self._active = False
        self._lctrl_down = False
        self._lwin_down = False
        self._hook_handle = None
        self._cb = None  # prevent GC of the ctypes callback

    def hook(self):
        relay = self

        @_HOOKPROC
        def _proc(nCode, wParam, lParam):
            if nCode >= 0:
                kb = ctypes.cast(
                    ctypes.c_void_p(lParam),
                    ctypes.POINTER(_KBDLLHOOKSTRUCT),
                ).contents
                vk = kb.vkCode
                is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)

                # Track left Ctrl
                if vk == VK_LCONTROL:
                    relay._lctrl_down = is_down

                # Track left Win
                if vk == VK_LWIN:
                    relay._lwin_down = is_down

                # Detect combo (before blocking, so we always catch it)
                combo = relay._lctrl_down and relay._lwin_down
                if combo and not relay._active:
                    relay._active = True
                    relay.key_pressed.emit()
                elif not combo and relay._active:
                    relay._active = False
                    relay.key_released.emit()
                    user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

                # Block Win key when Ctrl is held (suppresses Start Menu)
                if vk == VK_LWIN and relay._lctrl_down:
                    return 1

            return user32.CallNextHookEx(relay._hook_handle, nCode, wParam, lParam)

        self._cb = _proc
        self._hook_handle = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, _proc, 0, 0,
        )

    def unhook(self):
        if self._hook_handle:
            user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None
            self._cb = None


class AirTypeApp:
    """Main application controller."""

    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        self._settings = load_settings()

        self._capture = AudioCapture()
        self._asr = ASREngine(
            model_name=self._settings.get("asr_model"),
            language="Chinese",
        )
        self._llm = LLMRefiner()
        self._capsule = FloatingCapsule()
        self._tray = TrayIcon()
        self._hotkey_relay = _HotkeyRelay()
        self._watchdog = Watchdog()

        self._recording = False

        self._llm.configure(
            self._settings.get("api_base_url", ""),
            self._settings.get("api_key", ""),
            self._settings.get("model", ""),
        )

        self._connect_signals()

    def _connect_signals(self):
        # Hotkey relay -> recording control
        # QueuedConnection: defer slot execution out of the keyboard hook callback
        self._hotkey_relay.key_pressed.connect(
            self._start_recording, Qt.QueuedConnection,
        )
        self._hotkey_relay.key_released.connect(
            self._stop_recording, Qt.QueuedConnection,
        )

        # Audio -> Waveform only (RMS levels for visualization)
        self._capture.rms_updated.connect(self._capsule.update_waveform)

        # ASR -> Capsule text
        self._asr.partial_text.connect(self._on_partial_text)
        self._asr.final_text.connect(self._on_final_text)
        self._asr.model_loaded.connect(self._on_model_loaded)
        self._asr.error.connect(self._on_error)

        # LLM
        self._llm.refined.connect(self._on_refined_text)
        self._llm.error.connect(self._on_error)

        # Tray
        self._tray.llm_toggled.connect(self._on_llm_toggle)
        self._tray.settings_changed.connect(self._on_settings_changed)
        self._tray.quit_requested.connect(self._quit)

    def run(self):
        self._tray.show()
        self._tray.set_status(STATUS_LOADING)
        self._watchdog.start()
        self._asr.load_model()
        self._hotkey_relay.hook()
        return self._app.exec()

    def _on_model_loaded(self):
        self._tray.set_status(STATUS_READY)

    def _start_recording(self):
        if not self._asr.is_loaded:
            self._tray.set_status("ASR 模型尚未就绪...")
            return
        self._recording = True
        save_target_window()
        self._tray.set_status(STATUS_RECORDING)
        self._capsule.show_entry()
        self._capture.start()

    def _stop_recording(self):
        if not self._recording:
            return
        self._recording = False

        # Get accumulated audio and stop capture
        pcm = self._capture.stop()

        self._tray.set_status(STATUS_PROCESSING)
        self._capsule.set_processing()

        # Send to ASR for transcription
        self._asr.transcribe(pcm)

    def _on_partial_text(self, text: str):
        self._capsule.update_text(text)

    def _on_final_text(self, text: str):
        if not text:
            self._capsule.show_exit()
            self._tray.set_status(STATUS_READY)
            return

        if self._settings.get("llm_enabled", False):
            self._capsule.update_text(STATUS_REFINING)
            self._tray.set_status(STATUS_REFINING)
            self._llm.refine(text)
        else:
            self._capsule.show_exit()
            inject_text(text)
            self._tray.set_status(STATUS_READY)

    def _on_refined_text(self, text: str):
        self._capsule.show_exit()
        inject_text(text)
        self._tray.set_status(STATUS_READY)

    def _on_error(self, msg: str):
        self._tray.set_status(f"Error: {msg[:50]}")
        if self._recording:
            self._recording = False
            self._capture.stop()
        self._capsule.show_exit()

    def _on_llm_toggle(self, enabled: bool):
        self._settings["llm_enabled"] = enabled

    def _on_settings_changed(self, settings: dict):
        self._settings.update(settings)
        self._llm.configure(
            settings.get("api_base_url", ""),
            settings.get("api_key", ""),
            settings.get("model", ""),
        )

    def _quit(self):
        self._watchdog.stop()
        self._hotkey_relay.unhook()
        self._capture.stop()
        self._app.quit()


def main():
    app = AirTypeApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
