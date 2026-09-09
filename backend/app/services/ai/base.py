from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="Score between 0.0 and 1.0")
    is_correct: bool = Field(description="True if student achieved threshold score")
    missing_concepts: List[str] = Field(default_factory=list, description="Crucial concepts omitted")
    misconception_detected: Optional[str] = Field(default=None, description="Identified misconception pattern if any")
    detailed_feedback: str = Field(description="Educational feedback tailored for Class 8 student")
    recommended_action: str = Field(description="advance, retry_with_hint, or reinforce")


class TutorResponse(BaseModel):
    message: str = Field(description="Tutor conversational explanation or prompt")
    pedagogical_intent: str = Field(description="Intent: explain, socratic_check, practice, hint, remediation, completion")
    hint_level: int = Field(default=0, ge=0, le=5)
    strategy: Optional[str] = Field(default=None, description="Teaching strategy used if applicable")
    is_terminal: bool = Field(default=False, description="True if tutor declares session objective accomplished")
    suggested_quick_replies: List[str] = Field(default_factory=list)


class AIProvider(ABC):
    @abstractmethod
    async def generate_explanation(
        self,
        concept_name: str,
        learning_objective: str,
        curriculum_context: str,
        student_name: str = "Krish",
    ) -> TutorResponse:
        pass

    @abstractmethod
    async def generate_strategy_explanation(
        self,
        concept_name: str,
        learning_objective: str,
        curriculum_context: str,
        strategy: str,
        student_name: str = "Krish",
        prior_misconception: Optional[str] = None,
    ) -> TutorResponse:
        pass

    @abstractmethod
    async def generate_socratic_check(
        self,
        concept_name: str,
        curriculum_context: str,
        prior_explanation: str,
    ) -> TutorResponse:
        pass

    @abstractmethod
    async def evaluate_socratic_response(
        self,
        concept_name: str,
        socratic_question: str,
        student_response: str,
        curriculum_context: str,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_misconception_remediation(
        self,
        concept_name: str,
        misconception_text: str,
        curriculum_context: str,
        student_name: str = "Krish",
    ) -> TutorResponse:
        pass

    @abstractmethod
    async def evaluate_student_answer(
        self,
        question_prompt: str,
        student_answer: str,
        expected_concepts: List[str],
        required_points: List[str],
        misconception_traps: Dict[str, str],
        curriculum_context: str,
    ) -> EvaluationResult:
        pass

    @abstractmethod
    async def evaluate_explain_it_back(
        self,
        concept_name: str,
        student_explanation: str,
        key_points: Optional[List[str]] = None,
        curriculum_context: str = "",
        concept_explanation: str = "",
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_hint(
        self,
        question_prompt: str,
        student_previous_attempts: List[str],
        hint_level: int,
        curriculum_context: str,
    ) -> TutorResponse:
        pass

    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        pass

    @abstractmethod
    async def extract_concepts_and_objectives(
        self,
        topic_title: str,
        topic_text: str,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_candidate_questions(
        self,
        concept_name: str,
        concept_summary: str,
        source_text: str,
    ) -> List[Dict[str, Any]]:
        pass
