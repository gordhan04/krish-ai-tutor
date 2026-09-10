import pytest
import os
import uuid
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.curriculum import (
    CurriculumDocument,
    Book,
    Chapter,
    Section,
    Topic,
    Concept,
    ContentChunk,
    CurriculumActivity,
    CurriculumFigure,
)
from app.services.curriculum_ingestion.pipeline import IngestionPipeline
from app.services.curriculum_ingestion.publisher import CurriculumPublisher
from app.services.curriculum_ingestion.db_rebuilder import RAGIndexDiagnostics
from app.services.rag.retriever import CurriculumRetriever, CurriculumScope, RetrievalResult
from app.services.ai.mock_provider import MockAIProvider


@pytest.mark.asyncio
async def test_hard_provenance_invariant_rejects_impossible_pages(db_session: AsyncSession):
    """
    Hard Provenance Invariant:
    If any chunk claims a PDF page > document.page_count or printed page > document.printed_page_end,
    the retriever MUST reject it, log a provenance fault, and refuse to return it as source evidence.
    """
    db = db_session
    doc = CurriculumDocument(
        id=str(uuid.uuid4()),
        original_filename="test_bounds.pdf",
        storage_path="test_bounds.pdf",
        file_size=1024,
        content_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        status="PUBLISHED",
        page_count=96,
        printed_page_start=1,
        printed_page_end=84,
        uploader_id=str(uuid.uuid4()),
    )
    db.add(doc)

    book = Book(id=str(uuid.uuid4()), subject_id=str(uuid.uuid4()), title="Science")
    db.add(book)
    chap = Chapter(id=str(uuid.uuid4()), book_id=book.id, chapter_number=1, title="Test Chapter")
    db.add(chap)

    # 1. Valid chunk
    valid_chunk = ContentChunk(
        id=str(uuid.uuid4()),
        book_id=book.id,
        chapter_id=chap.id,
        document_id=doc.id,
        pdf_page_number=45,
        printed_page_number=33,
        content_type="TEXT",
        chunk_text="Valid chunk about combustion and chemical reaction of oxygen.",
        status="PUBLISHED",
    )
    db.add(valid_chunk)

    # 2. Corrupt chunk with impossible PDF page (106 > 96)
    corrupt_chunk_pdf = ContentChunk(
        id=str(uuid.uuid4()),
        book_id=book.id,
        chapter_id=chap.id,
        document_id=doc.id,
        pdf_page_number=106,  # IMPOSSIBLE
        printed_page_number=94,  # IMPOSSIBLE
        content_type="TEXT",
        chunk_text="Corrupt chunk about cell structure, cell membrane, and nucleus.",
        status="PUBLISHED",
    )
    db.add(corrupt_chunk_pdf)
    await db.commit()

    retriever = CurriculumRetriever(db)
    scope = CurriculumScope(document_id=doc.id)

    # Query for the corrupt chunk content
    res = await retriever.scoped_retrieval("cell structure cell membrane nucleus", scope=scope)
    # The corrupt chunk MUST be rejected due to impossible page
    assert res.grounded is False
    assert res.source_available is False
    assert res.reason == "PROVENANCE_INVARIANT_VIOLATION"
    assert len(res.chunks) == 0
    assert len(res.provenance_errors) > 0
    assert any("Impossible PDF page 106" in err for err in res.provenance_errors)

    # Query for the valid chunk
    res_valid = await retriever.scoped_retrieval("combustion chemical reaction oxygen", scope=scope)
    assert res_valid.grounded is True
    assert res_valid.source_available is True
    assert len(res_valid.chunks) == 1
    assert res_valid.chunks[0].id == valid_chunk.id
    assert res_valid.chunks[0].pdf_page_number == 45


@pytest.mark.asyncio
async def test_cross_document_isolation_and_database_contamination(db_session: AsyncSession):
    """
    Database Contamination Test:
    Populate Document A (Science Part I), Document B (Alternative Science), Document C (Part II).
    When Document A is selected, retrieval MUST return ONLY Document A chunks.
    When Document A is disabled/deleted, retrieval returns NO SOURCE, never leaks B or C.
    """
    db = db_session

    doc_a = CurriculumDocument(
        id=str(uuid.uuid4()),
        original_filename="Science_Part_I.pdf",
        storage_path="path_a.pdf",
        file_size=1000,
        content_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        status="PUBLISHED",
        page_count=96,
        uploader_id=str(uuid.uuid4()),
    )
    doc_b = CurriculumDocument(
        id=str(uuid.uuid4()),
        original_filename="Alternative_Physics.pdf",
        storage_path="path_b.pdf",
        file_size=2000,
        content_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        status="PUBLISHED",
        page_count=150,
        uploader_id=str(uuid.uuid4()),
    )
    doc_c = CurriculumDocument(
        id=str(uuid.uuid4()),
        original_filename="Science_Part_II.pdf",
        storage_path="path_c.pdf",
        file_size=3000,
        content_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        status="PUBLISHED",
        page_count=120,
        uploader_id=str(uuid.uuid4()),
    )
    db.add_all([doc_a, doc_b, doc_c])

    book_a = Book(id=str(uuid.uuid4()), subject_id=str(uuid.uuid4()), title="Part I")
    book_b = Book(id=str(uuid.uuid4()), subject_id=str(uuid.uuid4()), title="Alt Physics")
    book_c = Book(id=str(uuid.uuid4()), subject_id=str(uuid.uuid4()), title="Part II")
    db.add_all([book_a, book_b, book_c])

    ch_a = Chapter(id=str(uuid.uuid4()), book_id=book_a.id, chapter_number=8, title="Force & Pressure")
    ch_b = Chapter(id=str(uuid.uuid4()), book_id=book_b.id, chapter_number=2, title="Newtonian Mechanics")
    ch_c = Chapter(id=str(uuid.uuid4()), book_id=book_c.id, chapter_number=11, title="Sound Vibrations")
    db.add_all([ch_a, ch_b, ch_c])

    # Overlapping concept: "force"
    chunk_a = ContentChunk(
        id=str(uuid.uuid4()),
        book_id=book_a.id,
        chapter_id=ch_a.id,
        document_id=doc_a.id,
        pdf_page_number=65,
        printed_page_number=53,
        content_type="TEXT",
        chunk_text="A push or a pull on an object is called a force. Force can change state of motion.",
        status="PUBLISHED",
    )
    chunk_b = ContentChunk(
        id=str(uuid.uuid4()),
        book_id=book_b.id,
        chapter_id=ch_b.id,
        document_id=doc_b.id,
        pdf_page_number=20,
        printed_page_number=20,
        content_type="TEXT",
        chunk_text="Newton's second law defines force as mass times acceleration, F = m * a.",
        status="PUBLISHED",
    )
    chunk_c = ContentChunk(
        id=str(uuid.uuid4()),
        book_id=book_c.id,
        chapter_id=ch_c.id,
        document_id=doc_c.id,
        pdf_page_number=10,
        printed_page_number=10,
        content_type="TEXT",
        chunk_text="Sound force travels as longitudinal pressure waves vibrating the air medium.",
        status="PUBLISHED",
    )
    db.add_all([chunk_a, chunk_b, chunk_c])
    await db.commit()

    retriever = CurriculumRetriever(db)

    # 1. Query with Document A scope
    scope_a = CurriculumScope(document_id=doc_a.id)
    res_a = await retriever.scoped_retrieval("force push or pull motion", scope=scope_a)
    assert res_a.grounded is True
    assert len(res_a.chunks) == 1
    assert res_a.chunks[0].document_id == doc_a.id
    assert res_a.chunks[0].id == chunk_a.id

    # 2. Query asking for Newton's second law (exists ONLY in Document B)
    res_cross = await retriever.scoped_retrieval("Newton's second law F = m * a mass times acceleration", scope=scope_a)
    # MUST NOT retrieve Document B!
    assert res_cross.grounded is False
    assert res_cross.source_available is False
    assert len(res_cross.chunks) == 0

    # 3. Disable Document A
    doc_a.status = "FAILED"
    await db.commit()

    res_disabled = await retriever.scoped_retrieval("force push or pull motion", scope=scope_a)
    # Must fail safely rather than falling back to Document B or C
    assert res_disabled.grounded is False
    assert res_disabled.source_available is False
    assert res_disabled.reason == "DOCUMENT_NOT_PUBLISHED"
    assert len(res_disabled.chunks) == 0


@pytest.mark.asyncio
async def test_cross_chapter_boundary_enforcement(db_session: AsyncSession):
    """
    Cross-Chapter Test:
    When studying Chapter 1 (Crop Production), asking about 'friction' (which exists only in Chapter 9)
    must NOT retrieve Chapter 9 when chapter isolation is active.
    """
    db = db_session
    doc = CurriculumDocument(
        id=str(uuid.uuid4()),
        original_filename="Science_Class_8.pdf",
        storage_path="path.pdf",
        file_size=1000,
        content_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        status="PUBLISHED",
        page_count=96,
        uploader_id=str(uuid.uuid4()),
    )
    db.add(doc)

    book = Book(id=str(uuid.uuid4()), subject_id=str(uuid.uuid4()), title="Science")
    db.add(book)

    ch1 = Chapter(id=str(uuid.uuid4()), book_id=book.id, chapter_number=1, title="Crop Production")
    ch9 = Chapter(id=str(uuid.uuid4()), book_id=book.id, chapter_number=9, title="Friction")
    db.add_all([ch1, ch9])

    chunk1 = ContentChunk(
        id=str(uuid.uuid4()),
        book_id=book.id,
        chapter_id=ch1.id,
        document_id=doc.id,
        pdf_page_number=14,
        printed_page_number=2,
        content_type="TEXT",
        chunk_text="Agricultural practices include preparation of soil, sowing seeds, and irrigation.",
        status="PUBLISHED",
    )
    chunk9 = ContentChunk(
        id=str(uuid.uuid4()),
        book_id=book.id,
        chapter_id=ch9.id,
        document_id=doc.id,
        pdf_page_number=85,
        printed_page_number=73,
        content_type="TEXT",
        chunk_text="Friction opposes the relative motion between two surfaces in contact. Friction produces heat.",
        status="PUBLISHED",
    )
    db.add_all([chunk1, chunk9])
    await db.commit()

    retriever = CurriculumRetriever(db)

    # Lesson is scoped to Chapter 1 with allow_document_fallback = False
    scope_ch1 = CurriculumScope(document_id=doc.id, chapter_id=ch1.id, allow_document_fallback=False)

    # Student asks about friction while in Chapter 1
    res = await retriever.scoped_retrieval("What is friction and why does it oppose motion?", scope=scope_ch1)

    assert res.grounded is False
    assert res.source_available is False
    assert len(res.chunks) == 0
    assert res.reason in ("NO_RELEVANT_SOURCE_IN_SELECTED_CURRICULUM", "NO_CHUNKS_IN_REQUESTED_SCOPE")


@pytest.mark.asyncio
async def test_karnataka_part1_in_scope_and_out_of_scope_benchmarks(db_session: AsyncSession):
    """
    Comprehensive Real Textbook Acceptance Suite on '8th Eng Science Part - 1 2025-26.pdf':
    1. Ingest the actual PDF (96 pages, Chapters 1, 2, 3, 4, 8, 9).
    2. Negative Benchmark (Out-of-Scope Queries):
       - Cell structure, plant vs animal cell, Red Data Book, Chapter 5/6.
       - Assert 0 valid chunks and source_available == False.
    3. In-Scope Benchmark (20 Queries):
       - 20 queries across Ch 1, 2, 3, 4, 8, 9.
       - Assert 100% valid provenance (pdf_page <= 96, printed_page <= 84, doc_id matches).
    4. Concurrency Test:
       - Simultaneous queries across isolated scopes do not cross-contaminate.
    5. Diagnostic Integrity Check:
       - RAG index status is HEALTHY with 0 invalid references.
    """
    db = db_session
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "uploads", "370a968cba814528929b9fc2e23d5d15.pdf"),
        "backend/uploads/370a968cba814528929b9fc2e23d5d15.pdf",
        "uploads/370a968cba814528929b9fc2e23d5d15.pdf",
    ]
    pdf_path = next((p for p in candidates if os.path.exists(p)), None)
    if not pdf_path:
        pytest.skip("Test PDF not found")

    # Ingest document
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    doc = CurriculumDocument(
        id=str(uuid.uuid4()),
        original_filename="8th Eng Science Part - 1 2025-26.pdf",
        storage_path=pdf_path,
        file_size=len(pdf_bytes),
        content_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        status="UPLOADED",
        uploader_id=str(uuid.uuid4()),
    )
    db.add(doc)
    await db.commit()

    pipeline = IngestionPipeline(db, MockAIProvider())
    processed_doc = await pipeline.process_document(doc.id)
    await CurriculumPublisher.approve_document(db, processed_doc.id)
    published_doc = await CurriculumPublisher.publish_document(db, processed_doc.id)
    assert published_doc.status == "PUBLISHED"

    retriever = CurriculumRetriever(db)
    scope = CurriculumScope(document_id=published_doc.id)

    # -------------------------------------------------------------
    # A. NEGATIVE BENCHMARK: Out-of-Scope Queries (Must return NO SOURCE)
    # -------------------------------------------------------------
    out_of_scope_queries = [
        "What is the cell structure, cell membrane, cytoplasm, and nucleus?",
        "Comparison between plant cell and animal cell, cell wall and chloroplast",
        "What is the Red Data Book and migration of birds?",
        "What are the contents and concepts of Chapter 5?",
        "What are the contents and concepts of Chapter 6?",
        "Deforestation and its causes, conservation of plants and animals",
    ]

    for q in out_of_scope_queries:
        res = await retriever.scoped_retrieval(q, scope=scope)
        # MUST NOT return chunks or citations!
        assert res.source_available is False, f"Out-of-scope query '{q}' should not return source evidence!"
        assert len(res.chunks) == 0, f"Out-of-scope query '{q}' returned {len(res.chunks)} chunks!"

    # -------------------------------------------------------------
    # B. IN-DOCUMENT BENCHMARK: 20 Questions across Ch 1, 2, 3, 4, 8, 9
    # -------------------------------------------------------------
    in_scope_queries = [
        # Chapter 1: Crop Production
        ("Why do damaged seeds float on water?", 1),
        ("What is sowing and how is a traditional tool used?", 1),
        ("What are the basic agricultural practices?", 1),
        ("What is a cultivator used for with a tractor?", 1),
        # Chapter 2: Microorganisms
        ("Where do microorganisms live in nature?", 2),
        ("Name some useful microorganisms used in making curd and bread.", 2),
        ("What is fermentation of sugar into alcohol?", 2),
        ("How does pasteurization preserve milk without boiling?", 2),
        # Chapter 3: Coal and Petroleum
        ("What are inexhaustible natural resources?", 3),
        ("What is coal tar and coal gas?", 3),
        ("Why should fossil fuels be conserved?", 3),
        # Chapter 4: Combustion and Flame
        ("What is combustion and what is a combustible substance?", 4),
        ("What is ignition temperature?", 4),
        ("What are the different zones of a candle flame?", 4),
        # Chapter 8: Force and Pressure
        ("What is force and how does push or pull change state of motion?", 8),
        ("What are non-contact forces like magnetic and electrostatic force?", 8),
        ("What is pressure and how does pressure depend on area of contact?", 8),
        ("Do liquids exert pressure on the walls of containers?", 8),
        # Chapter 9: Friction
        ("What causes friction between interlocking surfaces?", 9),
        ("Why does a moving ball on the ground slow down?", 9),
    ]

    for query, exp_chap in in_scope_queries:
        res = await retriever.scoped_retrieval(query, scope=scope, limit=3)
        assert res.grounded is True, f"In-scope query '{query}' failed retrieval!"
        assert res.source_available is True
        assert len(res.chunks) >= 1
        assert len(res.provenance_errors) == 0

        # Hard Invariant checks on EVERY returned chunk
        for c in res.chunks:
            assert c.document_id == published_doc.id, f"Contaminated document_id: {c.document_id}"
            assert 1 <= c.pdf_page_number <= 96, f"Invalid PDF page {c.pdf_page_number} > 96"
            if c.printed_page_number is not None:
                assert 1 <= c.printed_page_number <= 84, f"Invalid printed page {c.printed_page_number} > 84"

    # -------------------------------------------------------------
    # C. DIAGNOSTIC INTEGRITY CHECK
    # -------------------------------------------------------------
    diag = RAGIndexDiagnostics(db)
    report = await diag.check_document_index_integrity(published_doc.id)
    assert report["healthy"] is True
    assert report["status"] == "HEALTHY"
    assert report["invalid_pdf_page_references"] == 0
    assert report["invalid_printed_page_references"] == 0
    assert report["orphan_chunks_in_doc"] == 0
    assert report["chunks_count"] > 100

    # -------------------------------------------------------------
    # D. CONCURRENCY TEST
    # -------------------------------------------------------------
    # Simulate Student A querying Chapter 1 and Student B querying Chapter 8 concurrently
    async def query_student_a():
        return await retriever.scoped_retrieval("Why do damaged seeds float on water?", scope=scope)

    async def query_student_b():
        return await retriever.scoped_retrieval("What is pressure and area of contact?", scope=scope)

    res_a, res_b = await asyncio.gather(query_student_a(), query_student_b())
    assert res_a.grounded is True
    assert res_b.grounded is True
    assert "seeds" in res_a.chunks[0].chunk_text.lower()
    assert "pressure" in res_b.chunks[0].chunk_text.lower()
