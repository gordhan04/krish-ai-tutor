import uuid
from datetime import datetime, timezone, date
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class StudentXP(Base):
    __tablename__ = "student_xp"

    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    student: Mapped["Student"] = relationship("Student", back_populates="xp_record")


class Streak(Base):
    __tablename__ = "streaks"

    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_study_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    planned_days_target: Mapped[int] = mapped_column(Integer, default=16)
    days_completed_count: Mapped[int] = mapped_column(Integer, default=1)
    grace_days_available: Mapped[int] = mapped_column(Integer, default=2)

    student: Mapped["Student"] = relationship("Student", back_populates="streak_record")


class DailyMission(Base):
    __tablename__ = "daily_missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    mission_date: Mapped[date] = mapped_column(Date, default=lambda: datetime.now(timezone.utc).date(), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(100), default="Science")
    chapter_name: Mapped[str] = mapped_column(String(255), default="Chemical Effects of Electric Current")
    target_concepts_count: Mapped[int] = mapped_column(Integer, default=2)
    completed_concepts_count: Mapped[int] = mapped_column(Integer, default=0)
    target_questions_count: Mapped[int] = mapped_column(Integer, default=5)
    completed_questions_count: Mapped[int] = mapped_column(Integer, default=0)
    target_weak_remedies_count: Mapped[int] = mapped_column(Integer, default=1)
    completed_weak_remedies_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=12)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=100)


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    badge_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="award")
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
