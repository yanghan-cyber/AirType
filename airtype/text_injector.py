"""Text injection via clipboard + Ctrl+V or unicode SendInput, with CJK IME handling."""

import ctypes
import ctypes.wintypes
import time as _time

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from .config import (
    VK_CONTROL, VK_V, VK_LWIN, VK_SHIFT, VK_INSERT,
    KEYEVENTF_KEYUP, CONSOLE_WINDOW_CLASS,
    CJK_LAYOUTS, ENGLISH_US_LAYOUT,
)

user32 = ctypes.windll.user32

# ── ctypes declarations for SendInput (unicode character injection) ──────────

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT)]

    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _U),
    ]


_SendInput = user32.SendInput
_SendInput.argtypes = [ctypes.wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
_SendInput.restype = ctypes.wintypes.UINT

# ── imm32 declarations for IME control ──────────────────────────────────────

imm32 = ctypes.windll.imm32
imm32.ImmSetOpenStatus.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.BOOL]
imm32.ImmSetOpenStatus.restype = ctypes.wintypes.BOOL
imm32.ImmGetContext.argtypes = [ctypes.wintypes.HWND]
imm32.ImmGetContext.restype = ctypes.wintypes.HWND
imm32.ImmReleaseContext.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HWND]
imm32.ImmReleaseContext.restype = ctypes.wintypes.BOOL

_target_hwnd = None


# ── IME helper functions ─────────────────────────────────────────────────────


def _close_ime():
    """Close the IME composition window for the current foreground window."""
    hwnd = user32.GetForegroundWindow()
    himc = imm32.ImmGetContext(hwnd)
    if himc:
        imm32.ImmSetOpenStatus(himc, 0)
        imm32.ImmReleaseContext(hwnd, himc)


def _prepare_ime():
    """Close IME and switch to English layout if currently CJK.

    Returns (original_layout, was_cjk) for later restoration.
    """
    _close_ime()
    original_layout = _get_keyboard_layout()
    was_cjk = original_layout in CJK_LAYOUTS
    if was_cjk:
        _activate_layout(ENGLISH_US_LAYOUT)
        _wait(30)
    return original_layout, was_cjk


def _restore_ime(original_layout, was_cjk):
    """Restore the original keyboard layout if it was CJK."""
    if was_cjk:
        _activate_layout(original_layout)


def _wait(ms: int):
    """Wait while keeping the Qt event loop alive."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def save_target_window():
    global _target_hwnd
    _target_hwnd = user32.GetForegroundWindow()


def _get_keyboard_layout() -> int:
    hwnd = user32.GetForegroundWindow()
    thread_id = user32.GetWindowThreadProcessId(hwnd, None)
    hkl = user32.GetKeyboardLayout(thread_id)
    return hkl & 0xFFFF


def _activate_layout(layout_id: int):
    user32.ActivateKeyboardLayout(layout_id, 0)


def _clipboard_set(text: str) -> bool:
    app = QApplication.instance()
    if not app:
        return False
    cb = app.clipboard()
    cb.setText(text)
    return True


def _clipboard_get() -> str | None:
    app = QApplication.instance()
    if not app:
        return None
    cb = app.clipboard()
    text = cb.text()
    return text if text else None


def _send_paste():
    user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
    _wait(10)
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def _send_shift_insert():
    user32.keybd_event(VK_SHIFT, 0, 0, 0)
    user32.keybd_event(VK_INSERT, 0, 0, 0)
    user32.keybd_event(VK_INSERT, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)


def _needs_shift_insert(hwnd: int) -> bool:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value == CONSOLE_WINDOW_CLASS


# ── Unicode character-by-character injection ─────────────────────────────────


def _inject_unicode(text: str):
    """Inject text character-by-character using SendInput with KEYEVENTF_UNICODE."""
    for ch in text:
        inp = _INPUT()
        inp.type = INPUT_KEYBOARD
        # Key down
        inp.union.ki.wVk = 0
        inp.union.ki.wScan = ord(ch)
        inp.union.ki.dwFlags = KEYEVENTF_UNICODE
        inp.union.ki.time = 0
        inp.union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

        # Key up
        inp.union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

        _time.sleep(0.010)


# ── Main injection entry point ──────────────────────────────────────────────


def inject_text(text: str, method: str = "clipboard"):
    if not text:
        return

    if _target_hwnd:
        user32.SetForegroundWindow(_target_hwnd)
        _wait(50)

    if method == "unicode":
        original_layout, was_cjk = _prepare_ime()
        _inject_unicode(text)
        _restore_ime(original_layout, was_cjk)
    else:
        # Clipboard + Ctrl+V / Shift+Insert
        _close_ime()
        old_clipboard = _clipboard_get()

        original_layout = _get_keyboard_layout()
        was_cjk = original_layout in CJK_LAYOUTS
        if was_cjk:
            _activate_layout(ENGLISH_US_LAYOUT)
            _wait(30)

        _clipboard_set(text)
        _wait(50)

        hwnd = user32.GetForegroundWindow()
        if _needs_shift_insert(hwnd):
            _send_shift_insert()
        else:
            _send_paste()

        _wait(150)
        if was_cjk:
            _activate_layout(original_layout)

        _wait(150)
        if old_clipboard is not None:
            try:
                _clipboard_set(old_clipboard)
            except Exception:
                pass
