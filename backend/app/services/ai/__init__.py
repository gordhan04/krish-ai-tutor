from app.core.config import settings
from app.services.ai.base import AIProvider, TutorResponse, EvaluationResult
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.gemini_provider import GeminiProvider


def get_ai_provider() -> AIProvider:
    """Factory returning the active AI Provider based on settings."""
    if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider(api_key=settings.GEMINI_API_KEY)
    # Default to robust Mock Provider for offline dev and tests
    return MockAIProvider()


__all__ = ["AIProvider", "TutorResponse", "EvaluationResult", "MockAIProvider", "GeminiProvider", "get_ai_provider"]
