"""Settings dialog with left sidebar navigation."""

import ctypes
import ctypes.wintypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QMessageBox, QGroupBox,
    QListWidget, QListWidgetItem, QStackedWidget, QWidget,
    QComboBox, QTextEdit, QRadioButton, QButtonGroup,
    QCheckBox, QFileDialog,
)

import sounddevice as sd

from .config import (
    LLM_SYSTEM_PROMPT, BLOCKED_HOTKEY_COMBOS, vk_combo_to_display,
)

# ── Native keyboard hook declarations for hotkey recording ──────────────────

_user32 = ctypes.windll.user32

_HK_WH_KEYBOARD_LL = 13
_HK_WM_KEYDOWN = 0x0100
_HK_WM_SYSKEYDOWN = 0x0104


class _HK_KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


_HK_HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long, ctypes.c_int,
    ctypes.c_size_t, ctypes.c_size_t,
)

_user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int, _HK_HOOKPROC, ctypes.c_size_t, ctypes.wintypes.DWORD,
]
_user32.SetWindowsHookExW.restype = ctypes.c_size_t
_user32.UnhookWindowsHookEx.argtypes = [ctypes.c_size_t]
_user32.UnhookWindowsHookEx.restype = ctypes.c_int
_user32.CallNextHookEx.argtypes = [
    ctypes.c_size_t, ctypes.c_int,
    ctypes.c_size_t, ctypes.c_size_t,
]
_user32.CallNextHookEx.restype = ctypes.c_long


class HotwordTag(QWidget):
    """A single hotword tag with remove button."""

    remove_requested = Signal(str)

    def __init__(self, word: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(word)
        label.setStyleSheet(
            "background:#e0e7ff; color:#3730a3; padding:2px 8px; "
            "border-radius:10px; font-size:12px;"
        )
        layout.addWidget(label)

        btn = QPushButton("✕")
        btn.setFixedSize(18, 18)
        btn.setStyleSheet(
            "QPushButton{border:none;color:#6366f1;font-size:11px;"
            "background:transparent;} QPushButton:hover{color:#ef4444;}"
        )
        btn.clicked.connect(lambda: self.remove_requested.emit(word))
        layout.addWidget(btn)


class ASRSettingsPage(QWidget):
    """语音识别 settings: language, device, model path, injection method."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._language = QComboBox()
        self._languages = self._get_languages()
        self._language.addItems(self._languages)
        lang = self._settings.get("language", "Chinese")
        idx = self._languages.index(lang) if lang in self._languages else 0
        self._language.setCurrentIndex(idx)
        form.addRow("识别语言", self._language)

        self._device = QComboBox()
        self._device.addItem("系统默认", None)
        self._populate_devices()
        saved_dev = self._settings.get("audio_device")
        if saved_dev:
            for i in range(self._device.count()):
                if self._device.itemText(i) == saved_dev:
                    self._device.setCurrentIndex(i)
                    break
        form.addRow("录音设备", self._device)

        layout.addLayout(form)

        model_group = QGroupBox("ASR 模型")
        model_layout = QHBoxLayout(model_group)
        self._model_path = QLineEdit(self._settings.get("asr_model", ""))
        self._model_path.setPlaceholderText("模型目录路径...")
        model_layout.addWidget(self._model_path)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_model)
        model_layout.addWidget(browse_btn)
        layout.addWidget(model_group)

        inj_group = QGroupBox("上屏方式")
        inj_layout = QVBoxLayout(inj_group)
        self._inj_group = QButtonGroup(self)
        self._clipboard_rb = QRadioButton("剪贴板粘贴（默认，速度快）")
        self._unicode_rb = QRadioButton("逐字输入（像打字一样出现）")
        self._inj_group.addButton(self._clipboard_rb)
        self._inj_group.addButton(self._unicode_rb)
        if self._settings.get("injection_method", "clipboard") == "unicode":
            self._unicode_rb.setChecked(True)
        else:
            self._clipboard_rb.setChecked(True)
        inj_layout.addWidget(self._clipboard_rb)
        inj_layout.addWidget(self._unicode_rb)
        layout.addWidget(inj_group)

        layout.addStretch()

    def _get_languages(self) -> list[str]:
        try:
            from qwen_asr.inference.utils import SUPPORTED_LANGUAGES
            return list(SUPPORTED_LANGUAGES)
        except ImportError:
            return ["Chinese", "English", "Japanese", "Korean"]

    def _populate_devices(self):
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    self._device.addItem(dev["name"], i)
        except Exception:
            pass

    def _browse_model(self):
        path = QFileDialog.getExistingDirectory(self, "选择 ASR 模型目录")
        if path:
            self._model_path.setText(path)

    def get_settings(self) -> dict:
        return {
            "language": self._language.currentText(),
            "audio_device": self._device.currentText() if self._device.currentIndex() > 0 else None,
            "asr_model": self._model_path.text().strip(),
            "injection_method": "unicode" if self._unicode_rb.isChecked() else "clipboard",
        }


class LLMSettingsPage(QWidget):
    """LLM 精炼 settings: toggle, API, prompt, hotwords."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._hotwords = list(settings.get("hotwords", []))
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("LLM 精炼")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        self._enabled = QCheckBox("启用")
        self._enabled.setChecked(self._settings.get("llm_enabled", False))
        header.addWidget(self._enabled)
        layout.addLayout(header)

        api_group = QGroupBox("API 配置")
        api_form = QFormLayout(api_group)
        api_form.setSpacing(8)

        self._base_url = QLineEdit(self._settings.get("api_base_url", ""))
        self._base_url.setPlaceholderText("https://api.openai.com/v1")
        api_form.addRow("API 地址", self._base_url)

        self._api_key = QLineEdit(self._settings.get("api_key", ""))
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setPlaceholderText("sk-...")
        api_form.addRow("API Key", self._api_key)

        self._model = QLineEdit(self._settings.get("model", ""))
        self._model.setPlaceholderText("gpt-4o-mini")
        api_form.addRow("模型", self._model)

        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        api_form.addRow("", test_btn)

        layout.addWidget(api_group)

        prompt_label = QHBoxLayout()
        prompt_label.addWidget(QLabel("System Prompt"))
        prompt_label.addStretch()
        reset_btn = QPushButton("恢复默认")
        reset_btn.setStyleSheet("color:#2563eb; border:none; font-size:11px;")
        reset_btn.clicked.connect(self._reset_prompt)
        prompt_label.addWidget(reset_btn)
        layout.addLayout(prompt_label)

        self._prompt_edit = QTextEdit()
        self._prompt_edit.setFont(QFont("Consolas", 10))
        self._prompt_edit.setPlainText(self._settings.get("llm_system_prompt", LLM_SYSTEM_PROMPT))
        self._prompt_edit.setMaximumHeight(140)
        layout.addWidget(self._prompt_edit)

        hint = QLabel("热词会自动追加到 Prompt 末尾，无需手动编辑")
        hint.setStyleSheet("color:#999; font-size:11px;")
        layout.addWidget(hint)

        layout.addWidget(QLabel("热词列表"))

        self._hotword_container = QWidget()
        self._hotword_layout = QHBoxLayout(self._hotword_container)
        self._hotword_layout.setContentsMargins(0, 0, 0, 0)
        self._hotword_layout.setSpacing(4)
        self._hotword_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._rebuild_hotword_tags()

        hotword_input_row = QHBoxLayout()
        self._hotword_input = QLineEdit()
        self._hotword_input.setPlaceholderText("输入热词后按 Enter 添加...")
        self._hotword_input.returnPressed.connect(self._add_hotword)
        hotword_input_row.addWidget(self._hotword_input)
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_hotword)
        hotword_input_row.addWidget(add_btn)
        layout.addWidget(self._hotword_container)
        layout.addLayout(hotword_input_row)

        hotword_hint = QLabel("添加容易识别错的专业术语、人名等，LLM 会在后处理时重点纠正")
        hotword_hint.setStyleSheet("color:#999; font-size:11px;")
        layout.addWidget(hotword_hint)

        layout.addStretch()

    def _rebuild_hotword_tags(self):
        while self._hotword_layout.count():
            item = self._hotword_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for word in self._hotwords:
            tag = HotwordTag(word)
            tag.remove_requested.connect(self._remove_hotword)
            self._hotword_layout.addWidget(tag)

    def _add_hotword(self):
        text = self._hotword_input.text().strip()
        if not text:
            return
        words = [w.strip() for w in text.replace("\n", ",").split(",") if w.strip()]
        for w in words:
            if w not in self._hotwords and len(self._hotwords) < 50:
                self._hotwords.append(w)
        self._hotword_input.clear()
        self._rebuild_hotword_tags()

    def _remove_hotword(self, word: str):
        if word in self._hotwords:
            self._hotwords.remove(word)
            self._rebuild_hotword_tags()

    def _reset_prompt(self):
        self._prompt_edit.setPlainText(LLM_SYSTEM_PROMPT)

    def _test_connection(self):
        base_url = self._base_url.text().strip().rstrip("/")
        api_key = self._api_key.text().strip()
        model = self._model.text().strip()
        if not base_url or not model:
            QMessageBox.warning(self, "验证", "API 地址和模型不能为空")
            return
        try:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key=api_key)
            client.models.list()
        except Exception as e:
            result = QMessageBox.question(
                self, "连接失败",
                f"API 测试失败:\n{e}\n\n仍然保存设置？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if result == QMessageBox.No:
                return
        else:
            QMessageBox.information(self, "成功", "API 连接成功！")

    def get_settings(self) -> dict:
        return {
            "llm_enabled": self._enabled.isChecked(),
            "api_base_url": self._base_url.text().strip().rstrip("/"),
            "api_key": self._api_key.text().strip(),
            "model": self._model.text().strip(),
            "llm_system_prompt": self._prompt_edit.toPlainText(),
            "hotwords": list(self._hotwords),
        }


class HotkeySettingsPage(QWidget):
    """快捷键 settings: key recording with native WH_KEYBOARD_LL hook."""

    def __init__(self, settings: dict, pause_hook=None, resume_hook=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._recording = False
        self._recorded_keys = set()
        self._vk_codes = list(settings.get("hotkey_vk_codes", [0xA2, 0x5B]))
        self._pause_hook = pause_hook
        self._resume_hook = resume_hook
        self._temp_hook_handle = None
        self._temp_cb = None
        self._timeout_timer = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("快捷键")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self._hotkey_label = QLabel(vk_combo_to_display(self._vk_codes))
        self._hotkey_label.setStyleSheet(
            "background:#fff; border:2px solid #2563eb; border-radius:6px; "
            "padding:8px 16px; font-size:14px; font-weight:600; color:#2563eb;"
        )
        self._hotkey_label.setAlignment(Qt.AlignCenter)
        self._hotkey_label.setMinimumWidth(200)

        btn_row = QHBoxLayout()
        self._record_btn = QPushButton("录制")
        self._record_btn.clicked.connect(self._toggle_recording)
        btn_row.addWidget(self._record_btn)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)

        hotkey_row = QHBoxLayout()
        hotkey_row.addWidget(self._hotkey_label)
        hotkey_row.addLayout(btn_row)
        form.addRow("录音热键", hotkey_row)

        layout.addLayout(form)

        hint = QLabel("按下「录制」后按下你想要的组合键，至少 2 个键")
        hint.setStyleSheet("color:#999; font-size:11px;")
        layout.addWidget(hint)

        layout.addStretch()

    def _toggle_recording(self):
        if self._recording:
            self._cancel_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self._recording = True
        self._recorded_keys = set()
        self._record_btn.setText("取消")
        self._hotkey_label.setText("按下组合键...")
        self._hotkey_label.setStyleSheet(
            "background:#fef3c7; border:2px solid #f59e0b; border-radius:6px; "
            "padding:8px 16px; font-size:14px; color:#92400e;"
        )

        if self._pause_hook:
            self._pause_hook()

        page = self

        @_HK_HOOKPROC
        def _hook_proc(nCode, wParam, lParam):
            if nCode >= 0:
                kb = ctypes.cast(
                    ctypes.c_void_p(lParam),
                    ctypes.POINTER(_HK_KBDLLHOOKSTRUCT),
                ).contents
                vk = kb.vkCode
                is_down = wParam in (_HK_WM_KEYDOWN, _HK_WM_SYSKEYDOWN)

                if is_down:
                    if vk == 0x1B:
                        QTimer.singleShot(0, page._cancel_recording)
                        return 1

                    page._recorded_keys.add(vk)
                    page._hotkey_label.setText(
                        vk_combo_to_display(list(page._recorded_keys))
                    )

                    if len(page._recorded_keys) >= 2:
                        combo = frozenset(page._recorded_keys)
                        if combo in BLOCKED_HOTKEY_COMBOS:
                            page._hotkey_label.setText("此组合键被系统占用，请换一组")
                            return 1
                        QTimer.singleShot(0, page._finish_recording)

                return 1

            return _user32.CallNextHookEx(
                page._temp_hook_handle, nCode, wParam, lParam
            )

        self._temp_cb = _hook_proc
        self._temp_hook_handle = _user32.SetWindowsHookExW(
            _HK_WH_KEYBOARD_LL, _hook_proc, 0, 0,
        )

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._cancel_recording)
        self._timeout_timer.start(5000)

    def _cancel_recording(self):
        if not self._recording:
            return
        self._cleanup_hook()
        self._recording = False
        self._record_btn.setText("录制")
        self._hotkey_label.setText(vk_combo_to_display(self._vk_codes))
        self._hotkey_label.setStyleSheet(
            "background:#fff; border:2px solid #2563eb; border-radius:6px; "
            "padding:8px 16px; font-size:14px; font-weight:600; color:#2563eb;"
        )

    def _finish_recording(self):
        if not self._recording:
            return
        self._cleanup_hook()
        self._recording = False
        self._record_btn.setText("录制")

        if len(self._recorded_keys) < 2:
            self._cancel_recording()
            return

        self._vk_codes = sorted(self._recorded_keys)
        self._hotkey_label.setText(vk_combo_to_display(self._vk_codes))
        self._hotkey_label.setStyleSheet(
            "background:#fff; border:2px solid #2563eb; border-radius:6px; "
            "padding:8px 16px; font-size:14px; font-weight:600; color:#2563eb;"
        )

    def _cleanup_hook(self):
        if self._timeout_timer:
            self._timeout_timer.stop()
            self._timeout_timer = None
        if self._temp_hook_handle:
            _user32.UnhookWindowsHookEx(self._temp_hook_handle)
            self._temp_hook_handle = None
            self._temp_cb = None
        if self._resume_hook:
            self._resume_hook()

    def _reset(self):
        self._vk_codes = [0xA2, 0x5B]
        self._hotkey_label.setText(vk_combo_to_display(self._vk_codes))

    def cleanup(self):
        if self._recording:
            self._cancel_recording()

    def get_settings(self) -> dict:
        return {
            "hotkey": self._hotkey_label.text(),
            "hotkey_vk_codes": self._vk_codes,
        }


class AppearanceSettingsPage(QWidget):
    """外观 — placeholder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("即将推出...")
        label.setStyleSheet("color:#999; font-size:14px;")
        layout.addWidget(label)


class AboutPage(QWidget):
    """关于 — version and project info."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        name = QLabel("AirType")
        name.setFont(QFont("Segoe UI", 20, QFont.Bold))
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)

        version = QLabel(f"v{self._get_version()}")
        version.setStyleSheet("color:#666; font-size:13px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        info = QLabel("Windows 语音输入工具 · Qwen3-ASR · PySide6")
        info.setStyleSheet("color:#999; font-size:11px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

    def _get_version(self) -> str:
        try:
            pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("version"):
                    return line.split("=")[1].strip().strip('"').strip("'")
        except Exception:
            pass
        return "0.1.0"


class SettingsDialog(QDialog):
    """Main settings dialog with left sidebar navigation."""

    def __init__(self, settings: dict, pause_hook=None, resume_hook=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AirType 设置")
        self.setFixedSize(660, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._settings = dict(settings)
        self._pause_hook = pause_hook
        self._resume_hook = resume_hook
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QListWidget()
        sidebar.setFixedWidth(160)
        sidebar.setCurrentRow(0)
        sidebar.currentRowChanged.connect(self._on_page_changed)
        sidebar.setStyleSheet("""
            QListWidget {
                background: #f8fafc;
                border: none;
                border-right: 1px solid #e2e8f0;
                outline: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px 16px;
                color: #64748b;
            }
            QListWidget::item:selected {
                background: #2563eb;
                color: #ffffff;
                border-radius: 4px;
                margin: 2px 8px;
            }
            QListWidget::item:hover:!selected {
                background: #f1f5f9;
                border-radius: 4px;
                margin: 2px 8px;
            }
        """)

        pages = [
            ("🎙️ 语音识别", ASRSettingsPage(self._settings)),
            ("✨ LLM 精炼", LLMSettingsPage(self._settings)),
            ("⌨️ 快捷键", HotkeySettingsPage(self._settings, self._pause_hook, self._resume_hook)),
            ("🎨 外观", AppearanceSettingsPage()),
            ("ℹ️ 关于", AboutPage()),
        ]

        self._pages = []
        for name, page in pages:
            item = QListWidgetItem(name)
            sidebar.addItem(item)
            self._pages.append(page)

        right = QVBoxLayout()
        right.setContentsMargins(20, 16, 20, 16)
        right.setSpacing(12)

        self._stack = QStackedWidget()
        for page in self._pages:
            self._stack.addWidget(page)
        right.addWidget(self._stack, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:#fff;border:none;"
            "border-radius:6px;padding:8px 24px;font-size:13px;font-weight:500;}"
            "QPushButton:hover{background:#1d4ed8;}"
        )
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(
            "QPushButton{background:#f1f5f9;border:1px solid #d1d5db;"
            "border-radius:6px;padding:8px 24px;font-size:13px;}"
            "QPushButton:hover{background:#e2e8f0;}"
        )
        btn_row.addWidget(cancel_btn)

        right.addLayout(btn_row)

        main_layout.addWidget(sidebar)
        main_layout.addLayout(right, 1)

    def _on_page_changed(self, row: int):
        if 0 <= row < len(self._pages):
            self._stack.setCurrentIndex(row)

    def _save(self):
        self._cleanup_hotkey_page()
        self.accept()

    def reject(self):
        self._cleanup_hotkey_page()
        super().reject()

    def _cleanup_hotkey_page(self):
        hotkey_page = self._pages[2]
        if isinstance(hotkey_page, HotkeySettingsPage):
            hotkey_page.cleanup()

    def get_changed_settings(self) -> dict:
        result = {}
        asr_page = self._pages[0]
        if isinstance(asr_page, ASRSettingsPage):
            result.update(asr_page.get_settings())

        llm_page = self._pages[1]
        if isinstance(llm_page, LLMSettingsPage):
            result.update(llm_page.get_settings())

        hotkey_page = self._pages[2]
        if isinstance(hotkey_page, HotkeySettingsPage):
            result.update(hotkey_page.get_settings())

        return result
