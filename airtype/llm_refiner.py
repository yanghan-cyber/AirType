"""LLM refinement pipeline for conservative post-processing of ASR output."""

from PySide6.QtCore import QObject, Signal, QThread

from .config import LLM_SYSTEM_PROMPT


class _RefinementWorker(QThread):
    """Background thread that calls the LLM API."""

    finished = Signal(str)  # refined text
    error = Signal(str)

    def __init__(self, text: str, api_base: str, api_key: str, model: str):
        super().__init__()
        self._text = text
        self._api_base = api_base
        self._api_key = api_key
        self._model = model

    def run(self):
        try:
            from openai import OpenAI

            client = OpenAI(base_url=self._api_base, api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": self._text},
                ],
                temperature=0.0,
                max_tokens=4096,
            )
            result = response.choices[0].message.content.strip()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class LLMRefiner(QObject):
    """Manages LLM refinement requests with conservative homophone correction.

    Signals:
        refined(str): Emitted with the refined text.
        error(str): Emitted on API errors.
    """

    refined = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._worker: _RefinementWorker | None = None
        self._api_base = ""
        self._api_key = ""
        self._model = ""

    def configure(self, api_base: str, api_key: str, model: str):
        """Update API configuration."""
        self._api_base = api_base
        self._api_key = api_key
        self._model = model

    def refine(self, text: str):
        """Submit text for refinement. Results come via the `refined` signal."""
        if not text.strip():
            self.refined.emit(text)
            return

        # Cancel any in-flight request
        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self._worker = _RefinementWorker(text, self._api_base, self._api_key, self._model)
        self._worker.finished.connect(self.refined.emit)
        self._worker.error.connect(self.error.emit)
        self._worker.start()
