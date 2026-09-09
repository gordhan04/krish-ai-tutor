from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ConceptMasteryReport(BaseModel):
    concept_id: str
    concept_name: str
    topic_name: str
    chapter_name: str
    mastery_score: float
    total_attempts: int
    correct_attempts: int
    recent_accuracy: float
    status: str  # "Mastered", "Practicing", "Needs Review"


class MisconceptionReport(BaseModel):
    concept_name: str
    misconception_text: str
    evidence_quote: Optional[str] = None
    occurrence_count: int
    is_remediated: bool
    detected_at: datetime


class ParentDashboardOut(BaseModel):
    student_name: str
    grade_level: int
    total_study_time_minutes: int
    questions_attempted: int
    overall_accuracy: float
    learning_gain_percentage: float
    strong_concepts: List[str]
    weak_concepts: List[str]
    concept_masteries: List[ConceptMasteryReport]
    active_misconceptions: List[MisconceptionReport]
    actionable_insight: str
