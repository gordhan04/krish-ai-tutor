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
    CurriculumActivity,
    CurriculumFigure,
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
    ChunkDetailOut,
    ActivityOut,
    FigureOut,
    ChapterEntitiesOut,
    DocumentIntegrityOut,
    RAGQueryIn,
    RAGQueryOut,
)
from app.services.curriculum_ingestion.validator import DocumentValidator, IngestionValidationError
from app.services.curriculum_ingestion.pipeline import IngestionPipeline
from app.services.curriculum_ingestion.publisher import CurriculumPublisher
from app.services.curriculum_ingestion.db_rebuilder import RAGIndexDiagnostics
from app.services.rag.retriever import CurriculumRetriever, CurriculumScope
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

        val_res = None
        if d.validation_results:
            try:
                val_res = json.loads(d.validation_results)
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
            part=d.part,
            grade_level=d.grade_level,
            document_scope=d.document_scope,
            printed_page_start=d.printed_page_start,
            printed_page_end=d.printed_page_end,
            validation_results=val_res,
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

    val_res = None
    if doc.validation_results:
        try:
            val_res = json.loads(doc.validation_results)
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
        part=doc.part,
        grade_level=doc.grade_level,
        document_scope=doc.document_scope,
        printed_page_start=doc.printed_page_start,
        printed_page_end=doc.printed_page_end,
        validation_results=val_res,
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


@router.get("/documents/{document_id}/chunks", response_model=List[ChunkDetailOut])
async def get_document_chunks(
    document_id: str,
    chapter_id: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns ordered content chunks for an ingested document, including
    chapter/section names and adjacent previous/next chunk previews for inspection.
    """
    stmt = (
        select(ContentChunk)
        .where(ContentChunk.document_id == document_id)
        .options(
            selectinload(ContentChunk.chapter),
            selectinload(ContentChunk.section),
        )
        .order_by(ContentChunk.source_sequence.asc(), ContentChunk.pdf_page_number.asc())
    )
    if chapter_id:
        stmt = stmt.where(ContentChunk.chapter_id == chapter_id)
    if content_type:
        stmt = stmt.where(ContentChunk.content_type == content_type)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    chunks = res.scalars().all()

    output = []
    for idx, c in enumerate(chunks):
        prev_text = chunks[idx - 1].chunk_text if idx > 0 else None
        next_text = chunks[idx + 1].chunk_text if idx < len(chunks) - 1 else None
        output.append(
            ChunkDetailOut(
                id=c.id,
                content_type=c.content_type,
                chunk_text=c.chunk_text,
                page_number=c.page_number,
                pdf_page_number=c.pdf_page_number,
                printed_page_number=c.printed_page_number,
                source_sequence=c.source_sequence,
                heading_path=c.heading_path,
                chapter_id=c.chapter_id,
                chapter_title=c.chapter.title if c.chapter else None,
                section_id=c.section_id,
                section_title=c.section.title if c.section else None,
                status=c.status,
                prev_chunk_text=prev_text,
                next_chunk_text=next_text,
            )
        )
    return output


@router.get("/chapters/{chapter_id}/entities", response_model=ChapterEntitiesOut)
async def get_chapter_entities(
    chapter_id: str,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all first-class entities (activities, figures) extracted for a specific chapter.
    """
    act_stmt = (
        select(CurriculumActivity)
        .where(CurriculumActivity.chapter_id == chapter_id)
        .order_by(CurriculumActivity.source_sequence.asc(), CurriculumActivity.pdf_page.asc())
    )
    act_res = await db.execute(act_stmt)
    activities = act_res.scalars().all()

    fig_stmt = (
        select(CurriculumFigure)
        .where(CurriculumFigure.chapter_id == chapter_id)
        .order_by(CurriculumFigure.source_sequence.asc(), CurriculumFigure.pdf_page.asc())
    )
    fig_res = await db.execute(fig_stmt)
    figures = fig_res.scalars().all()

    return ChapterEntitiesOut(
        chapter_id=chapter_id,
        activities=[
            ActivityOut.model_validate(a) for a in activities
        ],
        figures=[
            FigureOut.model_validate(f) for f in figures
        ],
    )


@router.get("/documents/{document_id}/integrity", response_model=DocumentIntegrityOut)
async def get_document_integrity(
    document_id: str,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Audits RAG index integrity for a specific document."""
    diag = RAGIndexDiagnostics(db)
    res = await diag.check_document_index_integrity(document_id)
    if res.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentIntegrityOut(**res)


@router.post("/documents/{document_id}/reset-index", response_model=DocumentIntegrityOut)
async def reset_document_index(
    document_id: str,
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Safely resets and rebuilds all embeddings for a document."""
    diag = RAGIndexDiagnostics(db)
    try:
        res = await diag.reset_and_rebuild_document_index(document_id)
        return DocumentIntegrityOut(**res)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rag/query", response_model=RAGQueryOut)
async def execute_scoped_rag_query(
    payload: RAGQueryIn,
    current_user: User = Depends(require_role(["parent", "admin", "student"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes scoped RAG query with strict curriculum isolation, chapter boundary checking,
    and hard provenance bounds verification.
    """
    retriever = CurriculumRetriever(db)
    scope = CurriculumScope(
        document_id=payload.document_id,
        chapter_id=payload.chapter_id,
        section_id=payload.section_id,
        allow_document_fallback=payload.allow_document_fallback,
    )
    result = await retriever.scoped_retrieval(
        query_text=payload.query,
        scope=scope,
        limit=payload.limit,
        status_filter="PUBLISHED",
        include_front_matter=payload.include_front_matter,
    )

    chunk_outs = [
        ChunkDetailOut(
            id=c.id,
            content_type=c.content_type,
            chunk_text=c.chunk_text,
            page_number=c.page_number,
            pdf_page_number=c.pdf_page_number,
            printed_page_number=c.printed_page_number,
            source_sequence=c.source_sequence,
            heading_path=c.heading_path,
            chapter_id=c.chapter_id,
            chapter_title=c.chapter.title if c.chapter else None,
            section_id=c.section_id,
            section_title=c.section.title if c.section else None,
            status=c.status,
        )
        for c in result.chunks
    ]

    return RAGQueryOut(
        grounded=result.grounded,
        source_available=result.source_available,
        reason=result.reason,
        citations=result.citations,
        formatted_context=result.formatted_context,
        chunks_count=len(result.chunks),
        provenance_errors=result.provenance_errors,
        debug_metadata=result.debug_metadata,
        chunks=chunk_outs,
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
