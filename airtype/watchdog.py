"""UI thread watchdog — detects and logs main thread hangs."""

import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, QCoreApplication

from .config import CONFIG_DIR

_LOG_FILE = CONFIG_DIR / "watchdog.log"
_CHECK_INTERVAL_MS = 500   # Check every 500ms
_HANG_THRESHOLD_S = 3.0    # Report hang if main thread blocked > 3s


class Watchdog:
    """Monitors the main (GUI) thread for hangs.

    Uses a simple heartbeat mechanism: the main thread updates a timestamp
    periodically via QTimer. A background thread checks that the timestamp
    stays fresh. If it stalls beyond the threshold, the watchdog dumps the
    main thread's stack to a log file.
    """

    def __init__(self):
        self._heartbeat_time = datetime.now()
        self._running = False
        self._watcher_thread = None
        self._log_path = _LOG_FILE

    def start(self):
        """Start the watchdog heartbeat and monitor thread."""
        self._running = True

        # Main-thread heartbeat timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._beat)
        self._timer.start(_CHECK_INTERVAL_MS)

        # Background monitor thread
        self._watcher_thread = threading.Thread(
            target=self._monitor_loop, daemon=True,
        )
        self._watcher_thread.start()

    def stop(self):
        """Stop the watchdog."""
        self._running = False
        if hasattr(self, "_timer"):
            self._timer.stop()

    def _beat(self):
        """Called on the main thread by QTimer — updates heartbeat timestamp."""
        self._heartbeat_time = datetime.now()

    def _monitor_loop(self):
        """Background thread — checks heartbeat freshness."""
        while self._running:
            threading.Event().wait(_CHECK_INTERVAL_MS / 1000.0)
            if not self._running:
                break

            elapsed = (datetime.now() - self._heartbeat_time).total_seconds()
            if elapsed > _HANG_THRESHOLD_S:
                self._dump_hang(elapsed)
                # Wait extra before checking again to avoid log spam
                threading.Event().wait(2.0)

    def _dump_hang(self, elapsed: float):
        """Dump the main thread's stack to the watchdog log."""
        try:
            main_thread = threading.main_thread()
            stack = traceback.format_stack(main_thread.__dict__.get("sys_frame"))
            # Fallback: get frame from sys._current_frames()
            frames = sys._current_frames()
            frame = frames.get(main_thread.ident)
            if frame:
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
