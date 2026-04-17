"""LLM refinement pipeline for conservative post-processing of ASR output."""

from PySide6.QtCore import QObject, Signal, QThread

from .config import LLM_SYSTEM_PROMPT


class _RefinementWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, text: str, api_base: str, api_key: str,
                 model: str, system_prompt: str):
        super().__init__()
        self._text = text
        self._api_base = api_base
        self._api_key = api_key
        self._model = model
        self._system_prompt = system_prompt

    def run(self):
        try:
            from openai import OpenAI

            client = OpenAI(base_url=self._api_base, api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
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
    refined = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._worker: _RefinementWorker | None = None
        self._api_base = ""
        self._api_key = ""
        self._model = ""
        self._system_prompt = LLM_SYSTEM_PROMPT
        self._hotwords: list[str] = []

    def configure(self, api_base: str, api_key: str, model: str,
                  system_prompt: str | None = None,
                  hotwords: list[str] | None = None):
        self._api_base = api_base
        self._api_key = api_key
        self._model = model
        if system_prompt is not None:
            self._system_prompt = system_prompt
        if hotwords is not None:
            self._hotwords = list(hotwords)

    def _build_prompt(self) -> str:
        prompt = self._system_prompt or LLM_SYSTEM_PROMPT
        if self._hotwords:
            prompt += (
                "\n\nPay special attention to these commonly misrecognized terms:\n"
                + ", ".join(self._hotwords)
            )
        return prompt

    def refine(self, text: str):
        if not text.strip():
            self.refined.emit(text)
            return

        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self._worker = _RefinementWorker(
            text, self._api_base, self._api_key,
            self._model, self._build_prompt(),
        )
        self._worker.finished.connect(self.refined.emit)
        self._worker.error.connect(self.error.emit)
        self._worker.start()