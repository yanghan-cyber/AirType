"""System tray icon with context menu."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from .settings_dialog import SettingsDialog
from .config import save_settings


def _create_default_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(QColor(0, 0, 0, 0))
    painter.setBrush(QColor(70, 130, 250))
    painter.drawRoundedRect(22, 8, 20, 28, 10, 10)

    painter.setPen(QPen(QColor(70, 130, 250), 3))
    painter.setBrush(QColor(0, 0, 0, 0))
    painter.drawArc(18, 18, 28, 28, 30 * 16, 120 * 16)

    painter.drawLine(32, 46, 32, 56)
    painter.drawLine(24, 56, 40, 56)

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    """System tray icon with right-click menu.

    Signals:
        llm_toggled(bool): Emitted when LLM refinement toggle changes.
        settings_changed(dict): Emitted when settings are updated and saved.
        quit_requested(): Emitted when the user selects Quit.
    """

    llm_toggled = Signal(bool)
    settings_changed = Signal(dict)
    quit_requested = Signal()

    def __init__(self, settings: dict, pause_hook=None, resume_hook=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._pause_hook = pause_hook
        self._resume_hook = resume_hook

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(_create_default_icon())
        self._tray.setToolTip("AirType - Voice Input")

        self._menu = QMenu()

        self._llm_action = QAction("LLM Refinement", self)
        self._llm_action.setCheckable(True)
        self._llm_action.setChecked(self._settings.get("llm_enabled", False))
        self._llm_action.toggled.connect(self._on_llm_toggle)
        self._menu.addAction(self._llm_action)

        self._menu.addSeparator()

        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self._show_settings)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(quit_action)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    def show(self):
        self._tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_settings()

    def _on_llm_toggle(self, checked: bool):
        self._settings["llm_enabled"] = checked
        save_settings(self._settings)
        self.llm_toggled.emit(checked)

    def _show_settings(self):
        dlg = SettingsDialog(self._settings, self._pause_hook, self._resume_hook)
        if dlg.exec() == SettingsDialog.Accepted:
            self._settings.update(dlg.get_changed_settings())
            save_settings(self._settings)
            self.settings_changed.emit(dict(self._settings))

    def _on_quit(self):
        self.quit_requested.emit()

    def set_status(self, text: str):
        """Update the tray icon tooltip."""
        self._tray.setToolTip(f"AirType - {text}")
