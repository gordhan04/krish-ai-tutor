from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ConceptOut(BaseModel):
    id: str
    name: str
    summary: str
    difficulty_tier: int
    status: str = "PUBLISHED"

    model_config = ConfigDict(from_attributes=True)


class LearningObjectiveOut(BaseModel):
    id: str
    statement: str
    bloom_taxonomy_level: str

    model_config = ConfigDict(from_attributes=True)


class TopicOut(BaseModel):
    id: str
    title: str
    order_index: int
    status: str = "PUBLISHED"
    concepts: List[ConceptOut] = []
    learning_objectives: List[LearningObjectiveOut] = []

    model_config = ConfigDict(from_attributes=True)


class SectionOut(BaseModel):
    id: str
    section_number: str
    title: str
    status: str = "PUBLISHED"
    topics: List[TopicOut] = []

    model_config = ConfigDict(from_attributes=True)


class ChapterOut(BaseModel):
    id: str
    chapter_number: int
    title: str
    description: Optional[str] = None
    status: str = "PUBLISHED"
    sections: List[SectionOut] = []

    model_config = ConfigDict(from_attributes=True)


class BookOut(BaseModel):
    id: str
    title: str
    publisher: str
    edition: str
    chapters: List[ChapterOut] = []

    model_config = ConfigDict(from_attributes=True)


class SubjectOut(BaseModel):
    id: str
    name: str
    grade_level: int
    icon: str
    books: List[BookOut] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str
    content_hash: str
    is_duplicate: bool = False


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    processing_stage: str
    page_count: int
    warnings: Optional[str] = None
    error_message: Optional[str] = None
    metrics: Optional[dict] = None


class DocumentOut(BaseModel):
    id: str
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    processing_stage: str
    page_count: int
    warnings: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    metrics: Optional[dict] = None


class ConceptUpdateIn(BaseModel):
    name: Optional[str] = None
    summary: Optional[str] = None
    difficulty_tier: Optional[int] = None
    status: Optional[str] = None
