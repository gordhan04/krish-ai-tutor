from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any


class OptionOut(BaseModel):
    id: str
    option_key: str
    option_text: str

    model_config = ConfigDict(from_attributes=True)


class QuestionOut(BaseModel):
    id: str
    concept_id: str
    topic_id: str
    question_type: str
    cognitive_level: int
    prompt: str
    source_page: Optional[int] = None
    options: List[OptionOut] = []

    model_config = ConfigDict(from_attributes=True)


class AnswerSubmitRequest(BaseModel):
    question_id: str
    student_answer: str
    selected_option_key: Optional[str] = None
    session_id: Optional[str] = None


class AnswerSubmitResponse(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    explanation: str
    missing_concepts: List[str] = []
    misconception_detected: Optional[str] = None
    mastery_score: float
    xp_awarded: int
    total_xp: int
    current_level: int
    leveled_up: bool
