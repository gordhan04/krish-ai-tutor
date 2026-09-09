import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Text, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[str] = mapped_column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), default="mcq")  # mcq, true_false, short_answer, rubric_explanation
    cognitive_level: Mapped[int] = mapped_column(Integer, default=2)  # 1: Recall, 2: Understanding, 3: Application, 4: Reasoning, 5: Challenge
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="textbook_exercise")  # textbook_exercise, generated_practice
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)

    concept: Mapped["Concept"] = relationship("Concept", back_populates="questions")
    options: Mapped[List["QuestionOption"]] = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    rubric: Mapped[Optional["QuestionRubric"]] = relationship("QuestionRubric", back_populates="question", uselist=False, cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    option_key: Mapped[str] = mapped_column(String(10), nullable=False)  # "A", "B", "C", "D"
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    question: Mapped["Question"] = relationship("Question", back_populates="options")


class QuestionRubric(Base):
    __tablename__ = "question_rubrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), unique=True, nullable=False)
    expected_concepts: Mapped[List[str]] = mapped_column(JSON, default=list)
    required_points: Mapped[List[str]] = mapped_column(JSON, default=list)
    misconception_traps: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    max_score: Mapped[float] = mapped_column(Float, default=1.0)

    question: Mapped["Question"] = relationship("Question", back_populates="rubric")
