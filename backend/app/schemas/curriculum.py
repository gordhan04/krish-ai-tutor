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
    pdf_page_start: Optional[int] = None
    pdf_page_end: Optional[int] = None
    printed_page_start: Optional[int] = None
    printed_page_end: Optional[int] = None
    topics: List[TopicOut] = []

    model_config = ConfigDict(from_attributes=True)


class ChapterOut(BaseModel):
    id: str
    chapter_number: int
    title: str
    description: Optional[str] = None
    status: str = "PUBLISHED"
    pdf_page_start: Optional[int] = None
    pdf_page_end: Optional[int] = None
    printed_page_start: Optional[int] = None
    printed_page_end: Optional[int] = None
    sections: List[SectionOut] = []

    model_config = ConfigDict(from_attributes=True)


class ActivityOut(BaseModel):
    id: str
    activity_number: str
    title: str
    instructions: str
    expected_observation: Optional[str] = None
    safety_notes: Optional[str] = None
    pdf_page: int
    printed_page: Optional[int] = None
    source_sequence: int = 0
    section_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FigureOut(BaseModel):
    id: str
    figure_number: str
    caption: str
    image_reference: Optional[str] = None
    pdf_page: int
    printed_page: Optional[int] = None
    source_sequence: int = 0
    section_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChapterEntitiesOut(BaseModel):
    chapter_id: str
    activities: List[ActivityOut] = []
    figures: List[FigureOut] = []


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
    part: Optional[str] = None
    grade_level: Optional[int] = 8
    document_scope: Optional[dict] = None
    printed_page_start: Optional[int] = None
    printed_page_end: Optional[int] = None
    validation_results: Optional[dict] = None


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
    part: Optional[str] = None
    grade_level: int = 8
    document_scope: Optional[dict] = None
    printed_page_start: Optional[int] = None
    printed_page_end: Optional[int] = None
    validation_results: Optional[dict] = None


class ChunkDetailOut(BaseModel):
    id: str
    content_type: str
    chunk_text: str
    page_number: int
    pdf_page_number: int
    printed_page_number: Optional[int] = None
    source_sequence: int = 0
    heading_path: Optional[str] = None
    chapter_id: str
    chapter_title: Optional[str] = None
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    status: str
    prev_chunk_text: Optional[str] = None
    next_chunk_text: Optional[str] = None


class ConceptUpdateIn(BaseModel):
    name: Optional[str] = None
    summary: Optional[str] = None
    difficulty_tier: Optional[int] = None
    status: Optional[str] = None


class DocumentIntegrityOut(BaseModel):
    document_id: str
    filename: str
    status: str
    healthy: bool
    total_physical_pages: int
    printed_page_range: str
    chunks_count: int
    embeddings_count: int
    missing_embeddings_count: int
    orphan_chunks_in_doc: int
    global_orphan_chunks: int
    invalid_pdf_page_references: int
    invalid_printed_page_references: int
    details: Optional[dict] = None


class RAGQueryIn(BaseModel):
    query: str
    document_id: Optional[str] = None
    chapter_id: Optional[str] = None
    section_id: Optional[str] = None
    allow_document_fallback: bool = False
    include_front_matter: bool = False
    limit: int = 4


class RAGQueryOut(BaseModel):
    grounded: bool
    source_available: bool
    reason: Optional[str] = None
    citations: List[str] = []
    formatted_context: str = ""
    chunks_count: int = 0
    provenance_errors: List[str] = []
    debug_metadata: Optional[dict] = None
    chunks: List[ChunkDetailOut] = []

