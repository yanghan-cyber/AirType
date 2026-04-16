"""Floating capsule-shaped recording UI with waveform animation and live transcription text."""

import ctypes

from PySide6.QtCore import (
    Qt, QTimer, QRectF, Property, QPropertyAnimation,
    QEasingCurve, Signal,
)
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QPainterPath,
    QLinearGradient,
)
from PySide6.QtWidgets import QWidget, QApplication, QHBoxLayout, QLabel

from .config import (
    BAR_COUNT, BAR_WEIGHTS, SPRING_DURATION, TEXT_TRANSITION_DURATION, EXIT_DURATION,
)


def _disable_dwm_shadow(hwnd: int):
    """Tell DWM not to draw any non-client area (shadows, rounded corners)."""
    try:
        dwmapi = ctypes.windll.dwmapi
        DWMWA_NCRENDERING_POLICY = 2
        DWMNCRP_DISABLED = 1
        policy = ctypes.c_int(DWMNCRP_DISABLED)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_NCRENDERING_POLICY,
            ctypes.byref(policy), ctypes.sizeof(policy),
        )
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_DONOTROUND = 1
        corner = ctypes.c_int(DWMWCP_DONOTROUND)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner), ctypes.sizeof(corner),
        )
    except Exception:
        pass


class WaveformWidget(QWidget):
    """Renders 5 vertical bars representing real-time audio RMS levels."""

    BAR_GAP = 4
    MIN_BAR_HEIGHT = 3
    MAX_BAR_HEIGHT = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 30)
        self._levels = [0.0] * BAR_COUNT

    def update_levels(self, levels: list[float]):
        self._levels = levels[:BAR_COUNT]
        self.update()

    def reset(self):
        self._levels = [0.0] * BAR_COUNT
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        total_gap = (BAR_COUNT - 1) * self.BAR_GAP
        bar_width = (self.width() - total_gap) / BAR_COUNT

        for i in range(BAR_COUNT):
            level = self._levels[i] if i < len(self._levels) else 0.0
            bar_height = self.MIN_BAR_HEIGHT + level * (self.MAX_BAR_HEIGHT - self.MIN_BAR_HEIGHT)
            x = i * (bar_width + self.BAR_GAP)
            y = (self.height() - bar_height) / 2

            # Gradient per bar: deep blue bottom → bright cyan top
            grad = QLinearGradient(x, y + bar_height, x, y)
            grad.setColorAt(0.0, QColor(60, 120, 220, 230))
            grad.setColorAt(0.5, QColor(70, 160, 240, 245))
            grad.setColorAt(1.0, QColor(120, 210, 255, 255))

            # Glow behind bar (wider, transparent)
            glow = QColor(80, 170, 255, int(40 + level * 60))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            glow_rect = QRectF(x - 1, y - 1, bar_width + 2, bar_height + 2)
            painter.drawRoundedRect(glow_rect, (bar_width + 2) / 2, (bar_width + 2) / 2)

            # Main bar
            painter.setBrush(QBrush(grad))
            rect = QRectF(x, y, bar_width, bar_height)
            painter.drawRoundedRect(rect, bar_width / 2, bar_width / 2)

        painter.end()


class SpinnerWidget(QWidget):
    """A rotating arc spinner shown during processing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._running = False

    def _tick(self):
        self._angle = (self._angle + 12) % 360
        self.update()

    def start(self):
        if not self._running:
            self._running = True
            self._angle = 0
            self._timer.start(30)
            self.show()

    def stop(self):
        self._running = False
        self._timer.stop()
        self.hide()

    def paintEvent(self, event):
        if not self._running:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QBrush(QColor(80, 160, 240, 210)), 2.5, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        margin = 3
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        painter.drawArc(rect, int(self._angle * 16), 270 * 16)
        painter.end()


class FloatingCapsule(QWidget):
    """Frameless capsule-shaped floating window."""

    MIN_WIDTH = 96
    MAX_WIDTH = 520
    HEIGHT = 42
    RADIUS = 21

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._scale = 0.0
        self._opacity = 0.0
        self._processing = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        self.waveform = WaveformWidget(self)
        layout.addWidget(self.waveform)

        self._spinner = SpinnerWidget(self)
        self._spinner.hide()
        layout.addWidget(self._spinner)

        self._sep = _Separator(self)
        self._sep.hide()
        layout.addWidget(self._sep)

        self._label = QLabel(self)
        self._label.setFont(QFont("Segoe UI", 9))
        self._label.setStyleSheet("color: rgba(30, 30, 30, 220); background: transparent;")
        self._label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._label.setFixedWidth(0)
        self._label.hide()
        self._label.setWordWrap(False)
        layout.addWidget(self._label)

        self.setFixedHeight(self.HEIGHT)
        self.setFixedWidth(self.MIN_WIDTH)
        self._center_at_bottom()

    def _center_at_bottom(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2 + geo.x()
            y = geo.height() - self.height() - 48 + geo.y()
            self.move(x, y)

    def get_scale(self):
        return self._scale

    def set_scale(self, s):
        self._scale = s
        w = int(self._base_width * s)
        h = int(self.HEIGHT * s)
        self.setFixedSize(w, h)
        if s > 0.01:
            self._center_at_bottom()

    scale = Property(float, get_scale, set_scale)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, o):
        self._opacity = o
        self.update()

    opacity = Property(float, get_opacity, set_opacity)

    @property
    def _base_width(self):
        if not self._label.text() or self._processing:
            return self.MIN_WIDTH
        text_width = self._label.fontMetrics().horizontalAdvance(self._label.text()) + 16
        label_w = min(480, max(60, text_width))
        return min(self.MAX_WIDTH, max(self.MIN_WIDTH, label_w + 80))

    def show_entry(self):
        self._processing = False
        self._spinner.stop()
        self._spinner.hide()
        self._label.hide()
        self._sep.hide()
        self.waveform.show()
        self._scale = 0.5
        self._opacity = 0.0
        self.waveform.reset()
        self._label.setText("")
        self._label.setFixedWidth(0)
        self.setFixedWidth(self.MIN_WIDTH)
        self._center_at_bottom()
        self.show()

        self._anim_opacity = QPropertyAnimation(self, b"opacity")
        self._anim_opacity.setDuration(SPRING_DURATION)
        self._anim_opacity.setStartValue(0.0)
        self._anim_opacity.setEndValue(1.0)
        self._anim_opacity.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_opacity.start()

        self._anim_scale = QPropertyAnimation(self, b"scale")
        self._anim_scale.setDuration(SPRING_DURATION)
        self._anim_scale.setStartValue(0.6)
        self._anim_scale.setEndValue(1.0)
        self._anim_scale.setEasingCurve(QEasingCurve.OutBack)
        self._anim_scale.start()

    def set_processing(self):
        """Shrink to spinner-only mode — no text, just loading animation."""
        self._processing = True
        self.waveform.hide()
        self._label.hide()
        self._sep.hide()
        self._spinner.start()
        self._spinner.show()
        # Shrink capsule to just fit the spinner
        target_w = 66
        if self.width() != target_w:
            self._animate_width(self, self.width(), target_w)

    def show_exit(self):
        self._spinner.stop()

        self._anim_exit = QPropertyAnimation(self, b"scale")
        self._anim_exit.setDuration(EXIT_DURATION)
        self._anim_exit.setStartValue(1.0)
        self._anim_exit.setEndValue(0.0)
        self._anim_exit.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim_exit.finished.connect(self._on_exit_done)
        self._anim_exit.start()

        self._anim_exit_opacity = QPropertyAnimation(self, b"opacity")
        self._anim_exit_opacity.setDuration(EXIT_DURATION)
        self._anim_exit_opacity.setStartValue(1.0)
        self._anim_exit_opacity.setEndValue(0.0)
        self._anim_exit_opacity.start()

    def _on_exit_done(self):
        self._processing = False
        self._spinner.stop()
        self.waveform.show()
        self._label.hide()
        self._sep.hide()
        self.hide()
        self.closed.emit()

    def update_waveform(self, levels: list[float]):
        if not self._processing:
            self.waveform.update_levels(levels)

    def update_text(self, text: str):
        self._label.setText(text)
        self._label.show()
        self._sep.show()

        text_width = self._label.fontMetrics().horizontalAdvance(text) + 16
        label_w = min(480, max(60, text_width))
        new_width = min(self.MAX_WIDTH, max(self.MIN_WIDTH, label_w + 80))

        if self.width() == new_width and self._label.width() == label_w:
            return

        self._animate_width(self, self.width(), new_width)
        self._animate_width(self._label, self._label.width(), label_w)
        self._center_at_bottom()

    def _animate_width(self, target, start, end):
        for prop in (b"minimumWidth", b"maximumWidth"):
            anim = QPropertyAnimation(target, prop)
            anim.setDuration(TEXT_TRANSITION_DURATION)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            setattr(self, f"_aw_{prop.decode()}_{id(target)}", anim)

    def paintEvent(self, event):
        if self._opacity < 0.01:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background — paint only within the rounded rect
        bg = QColor(252, 252, 252, int(235 * self._opacity))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(self.rect()), self.RADIUS, self.RADIUS)

        # Thin border (inset 0.5px to stay within the rounded shape)
        border = QColor(210, 210, 210, int(160 * self._opacity))
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(Qt.NoBrush)
        inner = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.drawRoundedRect(inner, self.RADIUS - 0.5, self.RADIUS - 0.5)

        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        _disable_dwm_shadow(int(self.winId()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_at_bottom()


class _Separator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(1)
        self.setFixedHeight(14)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(200, 200, 200, 160), 1))
        painter.drawLine(0, 0, 0, self.height())
        painter.end()
