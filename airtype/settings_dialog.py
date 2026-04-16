"""Settings dialog for AirType."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QMessageBox, QGroupBox,
)
from PySide6.QtGui import QFont

from .config import load_settings, save_settings


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AirType Settings")
        self.setFixedSize(440, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._settings = load_settings()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        # API Settings Group
        api_group = QGroupBox("LLM API Configuration")
        form = QFormLayout(api_group)
        form.setSpacing(10)

        self._base_url = QLineEdit(self._settings.get("api_base_url", ""))
        self._base_url.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("API Base URL:", self._base_url)

        self._api_key = QLineEdit(self._settings.get("api_key", ""))
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setPlaceholderText("sk-...")
        form.addRow("API Key:", self._api_key)

        self._model = QLineEdit(self._settings.get("model", ""))
        self._model.setPlaceholderText("gpt-4o-mini")
        form.addRow("Model:", self._model)

        layout.addWidget(api_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        test_btn = QPushButton("Test & Save")
        test_btn.setDefault(True)
        test_btn.clicked.connect(self._test_and_save)
        btn_layout.addWidget(test_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addStretch()
        layout.addLayout(btn_layout)

    def _test_and_save(self):
        """Test the API connection and save settings."""
        base_url = self._base_url.text().strip().rstrip("/")
        api_key = self._api_key.text().strip()
        model = self._model.text().strip()

        if not base_url or not model:
            QMessageBox.warning(self, "Validation", "API Base URL and Model are required.")
            return

        # Test connection
        try:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key=api_key)
            client.models.list()
        except Exception as e:
            result = QMessageBox.question(
                self,
                "Connection Failed",
                f"API test failed:\n{e}\n\nSave settings anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if result == QMessageBox.No:
                return
        else:
            QMessageBox.information(self, "Success", "API connection successful!")

        # Save
        self._settings["api_base_url"] = base_url
        self._settings["api_key"] = api_key
        self._settings["model"] = model
        save_settings(self._settings)
        self.accept()

    def get_settings(self) -> dict:
        """Return the updated settings."""
        self._settings["api_base_url"] = self._base_url.text().strip().rstrip("/")
        self._settings["api_key"] = self._api_key.text().strip()
        self._settings["model"] = self._model.text().strip()
        return dict(self._settings)
