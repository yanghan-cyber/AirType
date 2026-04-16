"""Text injection via clipboard + Ctrl+V with CJK IME handling."""

import ctypes
import ctypes.wintypes

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

user32 = ctypes.windll.user32

VK_CONTROL = 0x11
VK_V = 0x56
VK_LWIN = 0x5B
VK_SHIFT = 0x10
VK_INSERT = 0x2D
KEYEVENTF_KEYUP = 0x0002

_target_hwnd = None

CJK_LAYOUTS = {
    0x0804, 0x0404, 0x0411, 0x0412,
    0x0C04, 0x1004, 0x1404,
}

ENGLISH_US_LAYOUT = 0x0409


def _wait(ms: int):
    """Wait while keeping the Qt event loop alive (animations continue)."""
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
    return buf.value == "ConsoleWindowClass"


def inject_text(text: str):
    if not text:
        return

    if _target_hwnd:
        user32.SetForegroundWindow(_target_hwnd)
        _wait(50)

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
