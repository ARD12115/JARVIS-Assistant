import asyncio
import io
import edge_tts


class TTSEngine:
    def __init__(self, default_voice: str = "en-US-AriaNeural"):
        self.default_voice = default_voice
        # Available voices: https://github.com/rany2/edge-tts/blob/master/VOICES.md
        self.voices = {
            "aria": "en-US-AriaNeural",
            "guy": "en-US-GuyNeural",
            "jenny": "en-US-JennyNeural",
            "davis": "en-US-DavisNeural",
            "jane": "en-US-JaneNeural",
            "jason": "en-US-JasonNeural",
            "sara": "en-US-SaraNeural",
            "tony": "en-US-TonyNeural",
            "nancy": "en-US-NancyNeural",
        }

    async def synthesize(self, text: str, voice: str = None) -> bytes:
        """Convert text to speech using edge-tts."""
        voice = voice or self.default_voice
        
        # Validate voice
        if voice not in self.voices.values() and voice not in self.voices:
            voice = self.default_voice
        
        communicate = edge_tts.Communicate(text, voice)
        
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        return audio_data.getvalue()

    def get_available_voices(self) -> dict:
        """Return available voice mappings."""
        return self.voices.copy()


# Global instance
tts_engine = TTSEngine()