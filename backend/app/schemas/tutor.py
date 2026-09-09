from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class LessonStartRequest(BaseModel):
    topic_id: str
    concept_id: Optional[str] = None


class LessonStartResponse(BaseModel):
    session_id: str
    state: str
    concept_id: str
    concept_name: str
    learning_objective: str
    message: str
    hint_level: int
    suggested_replies: List[str] = []
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
