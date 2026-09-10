from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class PracticeStartRequest(BaseModel):
    session_id: str


class PracticeStartResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    current_question_id: str
    question_prompt: str
    bloom_level: Optional[int] = None
    difficulty: Optional[float] = None
    concept_id: str
    next_action: str
    feedback: Optional[str] = None
    question_type: Optional[str] = "mcq"
    source_page: Optional[int] = None
    options: List[Dict[str, Any]] = []


class PracticeAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str
    request_id: Optional[str] = None


class PracticeAnswerResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    next_action: str
    feedback: Optional[str] = None
    current_question_id: Optional[str] = None
    mastery_score: Optional[float] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None
    explanation: Optional[str] = None
    confidence: Optional[str] = None
    evidence_count: Optional[int] = 0
    consecutive_correct: Optional[int] = 0
    misconception_detected: Optional[str] = None
    retest_remediated: Optional[bool] = False
    xp_awarded: Optional[int] = 0


class ExplainItBackRequest(BaseModel):
    session_id: str
    response: str
    request_id: Optional[str] = None


class ExplainItBackResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    next_action: str
    feedback: Optional[str] = None
    mastery_score: Optional[float] = None
    score: Optional[float] = None
    accurate: Optional[bool] = None
    depth: Optional[str] = None
    confirmed_mastery: Optional[bool] = None
    retention_stage: Optional[str] = None
    xp_awarded: Optional[int] = 0
    criteria_scores: Optional[Dict[str, Any]] = None
