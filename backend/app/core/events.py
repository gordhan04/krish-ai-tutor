from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid


class LearningEventType(str, Enum):
    LESSON_STARTED = "lesson_started"
    CONCEPT_OPENED = "concept_opened"
    EXPLANATION_COMPLETED = "explanation_completed"
    QUESTION_SHOWN = "question_shown"
    ANSWER_SUBMITTED = "answer_submitted"
    ANSWER_CORRECT = "answer_correct"
    ANSWER_INCORRECT = "answer_incorrect"
    HINT_REQUESTED = "hint_requested"
    HINT_PROVIDED = "hint_provided"
    ANSWER_REVEALED = "answer_revealed"
    MISCONCEPTION_DETECTED = "misconception_detected"
    CONFIDENCE_RECORDED = "confidence_recorded"
    QUIZ_COMPLETED = "quiz_completed"
    REVISION_STARTED = "revision_started"
    REVISION_COMPLETED = "revision_completed"
    MASTERY_CHANGED = "mastery_changed"
    CHAPTER_COMPLETED = "chapter_completed"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    DAILY_MISSION_COMPLETED = "daily_mission_completed"


class LearningEventPayload:
    def __init__(
        self,
        event_type: LearningEventType,
        session_id: Optional[str] = None,
        student_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.session_id = session_id
        self.student_id = student_id
        self.payload = payload or {}
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }
