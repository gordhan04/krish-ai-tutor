import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="student", nullable=False)  # student, parent, admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    student_profile: Mapped["Student"] = relationship("Student", foreign_keys="Student.user_id", back_populates="user", uselist=False, cascade="all, delete-orphan")
    children: Mapped[list["Student"]] = relationship("Student", foreign_keys="Student.parent_id", back_populates="parent")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), default="Krish", nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="student_profile")
    parent: Mapped["User | None"] = relationship("User", foreign_keys=[parent_id], back_populates="children")
    xp_record: Mapped["StudentXP"] = relationship("StudentXP", back_populates="student", uselist=False, cascade="all, delete-orphan")
    streak_record: Mapped["Streak"] = relationship("Streak", back_populates="student", uselist=False, cascade="all, delete-orphan")
    sessions: Mapped[list["LearningSession"]] = relationship("LearningSession", back_populates="student")
    masteries: Mapped[list["ConceptMastery"]] = relationship("ConceptMastery", back_populates="student")
