from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class VoiceMode(str, Enum):
    TEACH = "teach"
    SOCRATIC = "socratic"
    QUIZ = "quiz"
    EXPLAIN_IT_BACK = "explain_it_back"


class VoiceTurnState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class VoiceInteractionRequest(BaseModel):
    session_id: str
    transcript: str
    mode: VoiceMode = VoiceMode.TEACH
    concept_id: Optional[str] = None
    question_id: Optional[str] = None


class VoiceInteractionResponse(BaseModel):
    session_id: str
    mode: VoiceMode
    turn_state: VoiceTurnState = VoiceTurnState.SPEAKING
    tutor_text_response: str
    audio_synthesis_instructions: Dict[str, Any]
    fallback_to_text: bool = False
    next_mode: VoiceMode


class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        pass


class TextToSpeechProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> Dict[str, Any]:
        pass


class StandardWebSpeechTTS(TextToSpeechProvider):
    """Generates speech synthesis control directives for the frontend client."""
    async def synthesize(self, text: str) -> Dict[str, Any]:
        return {
            "engine": "web_speech_synthesis",
            "rate": 0.95,
            "pitch": 1.05,
            "voice_name": "Friendly Educational Tutor",
            "clean_speech_text": text.replace("*", "").replace("#", "").strip(),
        }
