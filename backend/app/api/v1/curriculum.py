import os
import json
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db, AsyncSessionLocal
from app.core.config import settings
from app.api.deps import require_role
from app.models.user import User
from app.models.curriculum import (
    Subject,
    Book,
    Chapter,
    Section,
    Topic,
    Concept,
    LearningObjective,
    ContentChunk,
    CurriculumDocument,
)
from app.schemas.curriculum import (
    SubjectOut,
    ChapterOut,
    TopicOut,
    ConceptOut,
    DocumentUploadResponse,
    DocumentStatusResponse,
    DocumentOut,
    ConceptUpdateIn,
)
from app.services.curriculum_ingestion.validator import DocumentValidator, IngestionValidationError
from app.services.curriculum_ingestion.pipeline import IngestionPipeline
from app.services.curriculum_ingestion.publisher import CurriculumPublisher
from app.services.ai import get_ai_provider

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


async def _run_ingestion_in_background(document_id: str):
    """Background worker for asynchronous document ingestion."""
    async with AsyncSessionLocal() as session:
        ai_provider = get_ai_provider()
        pipeline = IngestionPipeline(session, ai_provider)
        try:
            await pipeline.process_document(document_id)
        except Exception as e:
            print(f"[BACKGROUND INGESTION ERROR] Doc {document_id}: {e}")


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_curriculum_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject_name: str = Form("Science"),
    book_title: str = Form("NCERT Science Class 8"),
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Secure textbook upload endpoint:
    - Verifies parent/admin authorization
    - Validates MIME type, extension, and magic bytes (%PDF-)
    - Enforces file size limits
    - Prevents path traversal
    - Deduplicates by content SHA-256 hash
    - Dispatches asynchronous ingestion pipeline
    """
    content = await file.read()

    try:
        sanitized_filename, content_hash = DocumentValidator.validate_file_content(
            content=content,
            filename=file.filename or "textbook.pdf",
            content_type=file.content_type,
        )
    except IngestionValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Duplicate check
    duplicate_doc = await DocumentValidator.check_duplicate(db, content_hash)
    if duplicate_doc:
        return DocumentUploadResponse(
            document_id=duplicate_doc.id,
            filename=duplicate_doc.original_filename,
            status=duplicate_doc.status,
            message="Document with identical content has already been uploaded.",
            content_hash=duplicate_doc.content_hash,
            is_duplicate=True,
        )

    # Save to safe local storage
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_internal_name = f"{uuid.uuid4().hex}.pdf"
    storage_path = os.path.join(settings.UPLOAD_DIR, safe_internal_name)

    with open(storage_path, "wb") as f:
        f.write(content)

    doc = CurriculumDocument(
        original_filename=sanitized_filename,
        storage_path=storage_path,
        file_size=len(content),
        content_hash=content_hash,
        mime_type=file.content_type or "application/pdf",
        status="UPLOADED",
        processing_stage="upload_complete",
        uploader_id=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Dispatch background ingestion task
    background_tasks.add_task(_run_ingestion_in_background, doc.id)

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        status=doc.status,
        message="Textbook uploaded successfully. Processing pipeline started.",
        content_hash=doc.content_hash,
        is_duplicate=False,
    )


@router.get("/documents", response_model=List[DocumentOut])
async def list_curriculum_documents(
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Lists all uploaded documents with their current processing status and metrics."""
    stmt = select(CurriculumDocument).order_by(CurriculumDocument.created_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()

    output = []
    for d in docs:
        metrics = None
        if d.metrics_json:
            try:
                metrics = json.loads(d.metrics_json)
            except Exception:
                pass

        output.append(DocumentOut(
            id=d.id,
            original_filename=d.original_filename,
            file_size=d.file_size,
            mime_type=d.mime_type,
            status=d.status,
            processing_stage=d.processing_stage,
            page_count=d.page_count,
            warnings=d.warnings,
            error_message=d.error_message,
            created_at=d.created_at.isoformat() if d.created_at else "",
            metrics=metrics,
        ))
    return output


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight polling endpoint for ingestion state."""
    stmt = select(CurriculumDocument).where(CurriculumDocument.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    metrics = None
    if doc.metrics_json:
        try:
            metrics = json.loads(doc.metrics_json)
        except Exception:
            pass

    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status,
        processing_stage=doc.processing_stage,
        page_count=doc.page_count,
        warnings=doc.warnings,
        error_message=doc.error_message,
        metrics=metrics,
    )


@router.post("/documents/{document_id}/approve", response_model=DocumentStatusResponse)
async def approve_document(
    document_id: str,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Approves an ingested document, marking it as REVIEWED."""
    doc = await CurriculumPublisher.approve_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status,
        processing_stage=doc.processing_stage,
        page_count=doc.page_count,
        warnings=doc.warnings,
        error_message=doc.error_message,
    )


@router.post("/documents/{document_id}/publish", response_model=DocumentStatusResponse)
async def publish_document(
    document_id: str,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Publishes an ingested document, making its content live to the AI Tutor & RAG."""
    doc = await CurriculumPublisher.publish_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status,
        processing_stage=doc.processing_stage,
        page_count=doc.page_count,
        warnings=doc.warnings,
        error_message=doc.error_message,
    )


@router.patch("/concepts/{concept_id}", response_model=ConceptOut)
async def update_concept(
    concept_id: str,
    payload: ConceptUpdateIn,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Allows an administrator or parent to edit or disable a concept before publishing."""
    stmt = select(Concept).where(Concept.id == concept_id)
    res = await db.execute(stmt)
    concept = res.scalars().first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found.")

    if payload.name is not None:
        concept.name = payload.name
    if payload.summary is not None:
        concept.summary = payload.summary
    if payload.difficulty_tier is not None:
        concept.difficulty_tier = payload.difficulty_tier
    if payload.status is not None:
        concept.status = payload.status

    await db.commit()
    await db.refresh(concept)
    return concept


# Existing read endpoints
@router.get("/subjects", response_model=List[SubjectOut])
async def get_subjects(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Subject)
        .options(
            selectinload(Subject.books)
            .selectinload(Book.chapters)
            .selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.concepts),
            selectinload(Subject.books)
            .selectinload(Book.chapters)
            .selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.learning_objectives),
        )
    )
    result = await db.execute(stmt)
    subjects = result.scalars().all()
    return subjects


@router.get("/chapters/{chapter_id}", response_model=ChapterOut)
async def get_chapter_details(chapter_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(
            selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.concepts),
            selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.learning_objectives),
        )
    )
    result = await db.execute(stmt)
    chapter = result.scalars().first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.get("/topics/{topic_id}", response_model=TopicOut)
async def get_topic_details(topic_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Topic)
        .where(Topic.id == topic_id)
        .options(
            selectinload(Topic.concepts),
            selectinload(Topic.learning_objectives),
        )
    )
    result = await db.execute(stmt)
    topic = result.scalars().first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic
