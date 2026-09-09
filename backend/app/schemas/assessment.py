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
    retest_remediated: bool = False
    mastery_score: float
    confidence: Optional[str] = None
    evidence_count: int = 0
    consecutive_correct: int = 0
    retention_stage: Optional[str] = None
    comeback_bonus_awarded: bool = False
    xp_awarded: int
    total_xp: int
    current_level: int
    leveled_up: bool


class ExplainItBackRequest(BaseModel):
    session_id: str
    student_answer: str
    concept_id: Optional[str] = None


class ExplainItBackResponse(BaseModel):
    session_id: str
    concept_name: str
    score: float
    accurate: bool
    depth: str
    feedback: str
    criteria_scores: Dict[str, float] = {}
    confirmed_mastery: bool
    mastery_score: float
    retention_stage: Optional[str] = None
    xp_awarded: int
    next_state: str
    suggested_replies: List[str] = []
