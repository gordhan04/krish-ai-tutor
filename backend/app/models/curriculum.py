import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, JSON
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
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHED")  # DRAFT, REVIEWED, PUBLISHED
    pdf_page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pdf_page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    printed_page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    printed_page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_sequence: Mapped[int] = mapped_column(Integer, default=0)

    book: Mapped["Book"] = relationship("Book", back_populates="chapters")
    sections: Mapped[List["Section"]] = relationship("Section", back_populates="chapter", cascade="all, delete-orphan")
    chunks: Mapped[List["ContentChunk"]] = relationship("ContentChunk", back_populates="chapter")
    activities: Mapped[List["CurriculumActivity"]] = relationship("CurriculumActivity", back_populates="chapter", cascade="all, delete-orphan")
    figures: Mapped[List["CurriculumFigure"]] = relationship("CurriculumFigure", back_populates="chapter", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    section_number: Mapped[str] = mapped_column(String(20), default="1.0")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHED")
    start_pdf_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_pdf_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_printed_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_printed_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_sequence: Mapped[int] = mapped_column(Integer, default=0)

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="sections")
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="section", cascade="all, delete-orphan")
    activities: Mapped[List["CurriculumActivity"]] = relationship("CurriculumActivity", back_populates="section", cascade="all, delete-orphan")
    figures: Mapped[List["CurriculumFigure"]] = relationship("CurriculumFigure", back_populates="section", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    section_id: Mapped[str] = mapped_column(String(36), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHED")

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
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHED")

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


class CurriculumDocument(Base):
    __tablename__ = "curriculum_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED", index=True)
    # Statuses: UPLOADED, VALIDATING, EXTRACTING, STRUCTURING, CHUNKING, EMBEDDING, GENERATING_CONTENT, READY_FOR_REVIEW, PUBLISHED, FAILED, OCR_REQUIRED
    processing_stage: Mapped[str] = mapped_column(String(50), default="upload")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warnings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    uploader_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    book_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    chapter_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    metrics_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    part: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer, default=8)
    document_scope: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    printed_page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    printed_page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    validation_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    subject: Mapped[Optional["Subject"]] = relationship("Subject")
    book: Mapped[Optional["Book"]] = relationship("Book")
    chapter: Mapped[Optional["Chapter"]] = relationship("Chapter")
    chunks: Mapped[List["ContentChunk"]] = relationship("ContentChunk", back_populates="document")


class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    book_id: Mapped[str] = mapped_column(String(36), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    concept_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("curriculum_documents.id", ondelete="SET NULL"), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    pdf_page_number: Mapped[int] = mapped_column(Integer, default=1)
    printed_page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_sequence: Mapped[int] = mapped_column(Integer, default=0)
    heading_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    parent_block_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    content_type: Mapped[str] = mapped_column(String(50), default="text")  # definition, explanation, example, experiment, table, exercise, summary, activity, figure, front_matter
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHED")  # DRAFT, REVIEWED, PUBLISHED
    embedding: Mapped[Optional[List[float]]] = mapped_column(PortableVector, nullable=True)

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="chunks")
    section: Mapped[Optional["Section"]] = relationship("Section")
    concept: Mapped[Optional["Concept"]] = relationship("Concept", back_populates="chunks")
    document: Mapped[Optional["CurriculumDocument"]] = relationship("CurriculumDocument", back_populates="chunks")


class CurriculumActivity(Base):
    __tablename__ = "curriculum_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    activity_number: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Activity 1.1"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    expected_observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    safety_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_page: Mapped[int] = mapped_column(Integer, default=1)
    printed_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_sequence: Mapped[int] = mapped_column(Integer, default=0)

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="activities")
    section: Mapped[Optional["Section"]] = relationship("Section", back_populates="activities")


class CurriculumFigure(Base):
    __tablename__ = "curriculum_figures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    figure_number: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Fig. 1.1(a)"
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    image_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pdf_page: Mapped[int] = mapped_column(Integer, default=1)
    printed_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_sequence: Mapped[int] = mapped_column(Integer, default=0)

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="figures")
    section: Mapped[Optional["Section"]] = relationship("Section", back_populates="figures")
