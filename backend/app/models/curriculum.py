import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, PortableVector


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="atom")

    books: Mapped[List["Book"]] = relationship("Book", back_populates="subject", cascade="all, delete-orphan")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str] = mapped_column(String(100), default="NCERT")
    edition: Mapped[str] = mapped_column(String(50), default="Latest Edition")

    subject: Mapped["Subject"] = relationship("Subject", back_populates="books")
    chapters: Mapped[List["Chapter"]] = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    book_id: Mapped[str] = mapped_column(String(36), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    book: Mapped["Book"] = relationship("Book", back_populates="chapters")
    sections: Mapped[List["Section"]] = relationship("Section", back_populates="chapter", cascade="all, delete-orphan")
    chunks: Mapped[List["ContentChunk"]] = relationship("ContentChunk", back_populates="chapter")


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    section_number: Mapped[str] = mapped_column(String(20), default="1.0")
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="sections")
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="section", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    section_id: Mapped[str] = mapped_column(String(36), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1)

    section: Mapped["Section"] = relationship("Section", back_populates="topics")
    concepts: Mapped[List["Concept"]] = relationship("Concept", back_populates="topic", cascade="all, delete-orphan")
    learning_objectives: Mapped[List["LearningObjective"]] = relationship("LearningObjective", back_populates="topic", cascade="all, delete-orphan")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty_tier: Mapped[int] = mapped_column(Integer, default=2)  # 1 to 5

    topic: Mapped["Topic"] = relationship("Topic", back_populates="concepts")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="concept")
    chunks: Mapped[List["ContentChunk"]] = relationship("ContentChunk", back_populates="concept")


class LearningObjective(Base):
    __tablename__ = "learning_objectives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    bloom_taxonomy_level: Mapped[str] = mapped_column(String(50), default="Understanding")

    topic: Mapped["Topic"] = relationship("Topic", back_populates="learning_objectives")


class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    book_id: Mapped[str] = mapped_column(String(36), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    concept_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    content_type: Mapped[str] = mapped_column(String(50), default="text")  # definition, explanation, example, experiment
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(PortableVector, nullable=True)

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="chunks")
    concept: Mapped[Optional["Concept"]] = relationship("Concept", back_populates="chunks")
