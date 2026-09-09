import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, Float, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="LESSON_START", nullable=False)
    lesson_phase: Mapped[str] = mapped_column(String(50), default="OBJECTIVE", nullable=False)
    session_goal: Mapped[str] = mapped_column(String(255), default="Concept Mastery", nullable=False)
    current_concept_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    hint_level: Mapped[int] = mapped_column(Integer, default=0)
    starting_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    ending_mastery: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pre_test_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    post_test_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strategy_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    attempted_question_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    questions_attempted_count: Mapped[int] = mapped_column(Integer, default=0)
    hints_used_count: Mapped[int] = mapped_column(Integer, default=0)
    learning_gain: Mapped[float] = mapped_column(Float, default=0.0)
    next_recommended_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    student: Mapped["Student"] = relationship("Student", back_populates="sessions")
    events: Mapped[list["LearningEvent"]] = relationship("LearningEvent", back_populates="session", cascade="all, delete-orphan")


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    session: Mapped["LearningSession"] = relationship("LearningSession", back_populates="events")


class ConceptMastery(Base):
    __tablename__ = "concept_mastery"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[str] = mapped_column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0.00 to 1.00
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)  # "LOW", "MEDIUM", "HIGH"
    difficulty_exposure: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retention_stage: Mapped[str] = mapped_column(String(32), default="INITIAL_MASTERY", nullable=False)  # INITIAL_MASTERY, RETAINED_MASTERY
    confirmed_mastery: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consecutive_correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0)
    recent_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    historical_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    last_assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_studied_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    next_revision_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    student: Mapped["Student"] = relationship("Student", back_populates="masteries")
    misconceptions: Mapped[list["Misconception"]] = relationship("Misconception", back_populates="mastery")


class Misconception(Base):
    __tablename__ = "misconceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[str] = mapped_column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    mastery_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("concept_mastery.id", ondelete="CASCADE"), nullable=True)
    misconception_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    remediation_attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_remediated: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    mastery: Mapped[Optional["ConceptMastery"]] = relationship("ConceptMastery", back_populates="misconceptions")
