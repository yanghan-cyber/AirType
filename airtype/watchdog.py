"""UI thread watchdog — detects and logs main thread hangs."""

import sys
import threading
import time
import traceback
from datetime import datetime

from PySide6.QtCore import QTimer, QCoreApplication

from .config import CONFIG_DIR

_LOG_FILE = CONFIG_DIR / "watchdog.log"
_CHECK_INTERVAL_MS = 500
_HANG_THRESHOLD_S = 3.0
_MAX_LOG_SIZE = 1 * 1024 * 1024  # 1MB rotation limit


class Watchdog:
    """Monitors the main (GUI) thread for hangs.

    Uses a heartbeat mechanism: the main thread updates a timestamp
    periodically via QTimer. A background thread checks freshness.
    If it stalls beyond the threshold, the main thread's stack is dumped to a log.
    """

    def __init__(self):
        self._heartbeat_time = time.monotonic()
        self._running = False
        self._watcher_thread = None
        self._log_path = _LOG_FILE
        self._stop_event = threading.Event()

    def start(self):
        self._running = True

        self._timer = QTimer()
        self._timer.timeout.connect(self._beat)
        self._timer.start(_CHECK_INTERVAL_MS)

        self._watcher_thread = threading.Thread(
            target=self._monitor_loop, daemon=True,
        )
        self._watcher_thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if hasattr(self, "_timer"):
            self._timer.stop()

    def _beat(self):
        self._heartbeat_time = time.monotonic()

    def _monitor_loop(self):
        while self._running:
            self._stop_event.wait(_CHECK_INTERVAL_MS / 1000.0)
            self._stop_event.clear()
            if not self._running:
                break

            elapsed = time.monotonic() - self._heartbeat_time
            if elapsed > _HANG_THRESHOLD_S:
                self._dump_hang(elapsed)
                self._stop_event.wait(2.0)
                self._stop_event.clear()

    def _dump_hang(self, elapsed: float):
        try:
            if self._log_path.exists() and self._log_path.stat().st_size > _MAX_LOG_SIZE:
                self._log_path.write_text("")

            frames = sys._current_frames()
            main_thread = threading.main_thread()
            frame = frames.get(main_thread.ident)
            if not frame:
                return

            stack = traceback.format_stack(frame)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"[{timestamp}] UI thread hang detected ({elapsed:.1f}s)\n")
                f.write(f"{'=' * 60}\n")
                f.write("Main thread stack:\n")
                f.write("".join(stack))
                f.write("\n")
        except Exception:
            pass
