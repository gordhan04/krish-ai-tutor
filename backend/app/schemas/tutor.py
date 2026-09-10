from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class LessonStartRequest(BaseModel):
    topic_id: str
    concept_id: Optional[str] = None
    strategy: Optional[str] = None


class LessonStartResponse(BaseModel):
    session_id: str
    state: str
    concept_id: str
    concept_name: str
    learning_objective: str
    starting_mastery: float = 0.0
    message: str
    hint_level: int
    suggested_replies: List[str] = []
    lesson_plan: List[Dict[str, Any]] = []
    curriculum_sources: List[Dict[str, Any]] = []


class HintRequest(BaseModel):
    session_id: str
    question_prompt: str


class HintResponse(BaseModel):
    session_id: str
    hint_level: int
    hint_message: str
    suggested_replies: List[str] = []


class SocraticCheckRequest(BaseModel):
    session_id: str


class SocraticCheckResponse(BaseModel):
    session_id: str
    state: str
    socratic_question: str
    suggested_replies: List[str] = []


class SocraticEvaluateRequest(BaseModel):
    session_id: str
    student_response: str


class SocraticEvaluateResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    understanding_confirmed: bool
    feedback: str
    suggested_replies: List[str] = []


class DiagnosticStartRequest(BaseModel):
    session_id: str


class DiagnosticStartResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    diagnostic_questions_count: int
    questions: List[Dict[str, Any]] = []


class DiagnosticEvaluateRequest(BaseModel):
    session_id: str
    diagnostic_score: float


class DiagnosticEvaluateResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    pre_test_score: float
    selected_strategy: str


class RemediateRequest(BaseModel):
    session_id: str
    misconception_id: str


class RemediateResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    misconception_text: str
    remediation_message: str
    suggested_replies: List[str] = []


class MasteryCompleteRequest(BaseModel):
    session_id: str


class MasteryCompleteResponse(BaseModel):
    session_id: str
    state: str
    lesson_phase: str
    is_terminal: bool
    concept_name: str
    mastery_score: float
    confidence: str
    learning_gain: float
    message: str
    next_recommended_action: str


class SessionPauseResponse(BaseModel):
    session_id: str
    state: str
    concept_name: str
    status: str
    message: str
    next_recommended_action: str


class StudentFeedbackRequest(BaseModel):
    session_id: str
    rating: str
    notes: Optional[str] = ""
    topic_id: Optional[str] = None


class StudentFeedbackResponse(BaseModel):
    success: bool
    session_id: str
    rating: str
    message: str

