import asyncio
import io
import threading
from typing import Optional
from faster_whisper import WhisperModel


class STTEngine:
    def __init__(self, model_size: str = "base", device: str = "auto", compute_type: str = "auto"):
        """
        Initialize faster-whisper model.
        
        Args:
            model_size: tiny, base, small, medium, large-v3
            device: cpu, cuda, auto
            compute_type: int8, int8_float16, float16, float32, auto
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._model_lock = threading.Lock()

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type
                    )
        return self._model

    async def transcribe(self, audio_file: io.BytesIO, language: str = "en") -> str:
        """Transcribe audio file to text."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, audio_file, language)

    def _transcribe_sync(self, audio_file: io.BytesIO, language: str) -> str:
        model = self._get_model()
        
        # Save to temp file for faster-whisper
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_file.read())
            temp_path = f.name
        
        try:
            segments, info = model.transcribe(temp_path, language=language, beam_size=5)
            text = " ".join([seg.text for seg in segments])
            return text.strip()
        finally:
            import os
            try:
                os.unlink(temp_path)
            except Exception:
                pass


# Global instance
stt_engine = STTEngine()