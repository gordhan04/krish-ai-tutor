import json
import httpx
from typing import Dict, Any, List, Optional
from app.services.ai.base import AIProvider, TutorResponse, EvaluationResult
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.prompts.tutor_v1 import (
    build_lesson_explanation_prompt,
    build_socratic_check_prompt,
)
from app.services.ai.prompts.evaluation_v1 import build_evaluation_prompt
from app.core.config import settings


class GeminiProvider(AIProvider):
    """
    Google Gemini Provider for generative tutoring and structured rubric evaluation.
    Falls back gracefully to MockAIProvider if GEMINI_API_KEY is not configured or in case of network error.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.fallback = MockAIProvider()

    async def generate_explanation(
        self,
        concept_name: str,
        learning_objective: str,
        curriculum_context: str,
        student_name: str = "Krish",
    ) -> TutorResponse:
        if not self.api_key:
            return await self.fallback.generate_explanation(
                concept_name, learning_objective, curriculum_context, student_name
            )

        prompt = build_lesson_explanation_prompt(
            concept_name, learning_objective, curriculum_context, student_name
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL_FAST}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800},
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return TutorResponse(
                    message=text,
                    pedagogical_intent="explain",
                    hint_level=0,
                    suggested_quick_replies=["I understand! Let's practice.", "Could you give another example?"]
                )
        except Exception:
            return await self.fallback.generate_explanation(
                concept_name, learning_objective, curriculum_context, student_name
            )

    async def generate_socratic_check(
        self,
        concept_name: str,
        curriculum_context: str,
        prior_explanation: str,
    ) -> TutorResponse:
        if not self.api_key:
            return await self.fallback.generate_socratic_check(
                concept_name, curriculum_context, prior_explanation
            )

        prompt = build_socratic_check_prompt(concept_name, curriculum_context, prior_explanation)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL_FAST}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 400},
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return TutorResponse(
                    message=text,
                    pedagogical_intent="socratic_check",
                    hint_level=0,
                )
        except Exception:
            return await self.fallback.generate_socratic_check(
                concept_name, curriculum_context, prior_explanation
            )

    async def evaluate_student_answer(
        self,
        question_prompt: str,
        student_answer: str,
        expected_concepts: List[str],
        required_points: List[str],
        misconception_traps: Dict[str, str],
        curriculum_context: str,
    ) -> EvaluationResult:
        if not self.api_key:
            return await self.fallback.evaluate_student_answer(
                question_prompt, student_answer, expected_concepts, required_points, misconception_traps, curriculum_context
            )

        prompt = build_evaluation_prompt(
            question_prompt, student_answer, expected_concepts, required_points, misconception_traps, curriculum_context
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL_ADVANCED}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            },
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                clean_text = text.strip()
                if clean_text.startswith("```"):
                    clean_text = clean_text.split("\n", 1)[1] if "\n" in clean_text else clean_text
                    if clean_text.endswith("```"):
                        clean_text = clean_text.rsplit("```", 1)[0]
                parsed = json.loads(clean_text.strip())
                parsed["score"] = max(0.0, min(1.0, float(parsed.get("score", 0.0))))
                return EvaluationResult(**parsed)
        except Exception:
            return await self.fallback.evaluate_student_answer(
                question_prompt, student_answer, expected_concepts, required_points, misconception_traps, curriculum_context
            )

    async def generate_hint(
        self,
        question_prompt: str,
        student_previous_attempts: List[str],
        hint_level: int,
        curriculum_context: str,
    ) -> TutorResponse:
        return await self.fallback.generate_hint(
            question_prompt, student_previous_attempts, hint_level, curriculum_context
        )
