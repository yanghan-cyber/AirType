"""AirType main entry point — wires all modules together."""

import ctypes
import ctypes.wintypes
import sys

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QObject, Signal, Qt

from .config import (
    load_settings, VK_LCONTROL, VK_LWIN, KEYEVENTF_KEYUP,
    CJK_LAYOUTS, ENGLISH_US_LAYOUT, CONSOLE_WINDOW_CLASS,
    vk_combo_to_display,
)
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
STATUS_NOT_READY = "ASR 模型尚未就绪..."

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


_HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long, ctypes.c_int,
    ctypes.c_size_t, ctypes.c_size_t,
)

user32.CallNextHookEx.argtypes = [
    ctypes.c_size_t, ctypes.c_int,
    ctypes.c_size_t, ctypes.c_size_t,
]
user32.CallNextHookEx.restype = ctypes.c_long
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int, _HOOKPROC, ctypes.c_size_t, ctypes.wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = ctypes.c_size_t
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_size_t]
user32.UnhookWindowsHookEx.restype = ctypes.c_int


class _HotkeyRelay(QObject):
    """Tracks a configurable key combo via a native WH_KEYBOARD_LL hook.

    Key events for target keys are blocked (not forwarded to Windows) whenever
    the combo is partially held, so the system does not trigger unwanted actions.
    """

    key_pressed = Signal()
    key_released = Signal()

    def __init__(self):
        super().__init__()
        self._active = False
        self._target_keys: set[int] = {VK_LCONTROL, VK_LWIN}
        self._held_keys: set[int] = set()
        self._hook_handle = None
        self._cb = None

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

                if vk in relay._target_keys:
                    if is_down:
                        relay._held_keys.add(vk)
                    else:
                        relay._held_keys.discard(vk)

                combo = relay._held_keys == relay._target_keys
                if combo and not relay._active:
                    relay._active = True
                    relay.key_pressed.emit()
                elif not combo and relay._active:
                    relay._active = False
                    relay.key_released.emit()
                    for held_vk in list(relay._held_keys):
                        user32.keybd_event(held_vk, 0, KEYEVENTF_KEYUP, 0)
                    relay._held_keys.clear()

                if vk in relay._target_keys and relay._held_keys:
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

    def update_keys(self, vk_codes: list[int]):
        self._target_keys = set(vk_codes)


class AirTypeApp:
    """Main application controller."""

    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        self._settings = load_settings()

        self._capture = AudioCapture()
        self._asr = ASREngine(
            model_name=self._settings.get("asr_model"),
            language=self._settings.get("language", "Chinese"),
        )
        self._llm = LLMRefiner()
        self._capsule = FloatingCapsule()
        self._tray = TrayIcon(self._settings)
        self._hotkey_relay = _HotkeyRelay()
        self._watchdog = Watchdog()

        self._recording = False

        self._llm.configure(
            self._settings.get("api_base_url", ""),
            self._settings.get("api_key", ""),
            self._settings.get("model", ""),
            system_prompt=self._settings.get("llm_system_prompt"),
            hotwords=self._settings.get("hotwords"),
        )

        self._connect_signals()

    def _connect_signals(self):
        self._hotkey_relay.key_pressed.connect(
            self._start_recording, Qt.QueuedConnection,
        )
        self._hotkey_relay.key_released.connect(
            self._stop_recording, Qt.QueuedConnection,
        )

        self._capture.rms_updated.connect(self._capsule.update_waveform)

        self._asr.partial_text.connect(self._on_partial_text)
        self._asr.final_text.connect(self._on_final_text)
        self._asr.model_loaded.connect(self._on_model_loaded)
        self._asr.error.connect(self._on_error)

        self._llm.refined.connect(self._on_refined_text)
        self._llm.error.connect(self._on_error)

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
            self._tray.set_status(STATUS_NOT_READY)
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
        pcm = self._capture.stop()
        self._tray.set_status(STATUS_PROCESSING)
        self._capsule.set_processing()
        self._asr.transcribe(pcm)

    def _on_partial_text(self, text: str):
        self._capsule.update_text(text)

    def _on_final_text(self, text: str):
        if not text:
            self._capsule.show_exit()
            self._tray.set_status(STATUS_READY)
            return

        method = self._settings.get("injection_method", "clipboard")

        if self._settings.get("llm_enabled", False):
            self._capsule.update_text(STATUS_REFINING)
            self._tray.set_status(STATUS_REFINING)
            self._llm.refine(text)
        else:
            self._capsule.show_exit()
            inject_text(text, method)
            self._tray.set_status(STATUS_READY)

    def _on_refined_text(self, text: str):
        self._capsule.show_exit()
        inject_text(text, self._settings.get("injection_method", "clipboard"))
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
        old = dict(self._settings)
        self._settings.update(settings)

        if settings.get("language") and settings["language"] != old.get("language"):
            self._asr.update_language(settings["language"])

        if "audio_device" in settings:
            self._capture.update_device(settings["audio_device"])

        if "hotkey_vk_codes" in settings and settings["hotkey_vk_codes"]:
            self._hotkey_relay.update_keys(settings["hotkey_vk_codes"])

        self._llm.configure(
            settings.get("api_base_url", ""),
            settings.get("api_key", ""),
            settings.get("model", ""),
            system_prompt=settings.get("llm_system_prompt"),
            hotwords=settings.get("hotwords"),
        )

        if settings.get("asr_model") and settings["asr_model"] != old.get("asr_model"):
            QMessageBox.information(
                None, "AirType",
                "ASR 模型路径已更改，需要重启应用后生效。",
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
