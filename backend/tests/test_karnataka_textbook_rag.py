import pytest
import os
import uuid
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.curriculum import (
    CurriculumDocument,
    Chapter,
    Section,
    ContentChunk,
    CurriculumActivity,
    CurriculumFigure,
)
from app.services.curriculum_ingestion.pipeline import IngestionPipeline
from app.services.curriculum_ingestion.publisher import CurriculumPublisher
from app.services.rag.retriever import CurriculumRetriever
from app.services.ai.mock_provider import MockAIProvider


@pytest.mark.asyncio
async def test_karnataka_class_8_textbook_ingestion_and_rag(db_session: AsyncSession):
    """
    Acceptance Test for Karnataka Class 8 Science Part-I (96 pages):
    1. Ingestion: 96 pages, 12 front matter, 84 content pages.
    2. Chapters: Exactly 6 chapters (1, 2, 3, 4, 8, 9).
    3. Status: VALID NON-CONTIGUOUS VOLUME.
    4. Dual page mapping: delta = 12 (PDF p. 13 -> Printed p. 1, etc.).
    5. Activities and Figures first-class records created.
    6. Chunks: > 100 meaningful chunks (never 1 chunk).
    7. Review & Publication.
    8. RAG Smoke Tests: 14 queries verified with source provenance citations.
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

    # 1. Setup Admin user
    u_stmt = select(User).where(User.role == "admin")
    u_res = await db.execute(u_stmt)
    admin_user = u_res.scalars().first()
    if not admin_user:
        admin_user = User(
            id=str(uuid.uuid4()),
            email="admin_karnataka@test.com",
            hashed_password="hash",
            role="admin",
        )
        db.add(admin_user)
        await db.flush()

    file_size = os.path.getsize(pdf_path)
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    doc = CurriculumDocument(
        id=str(uuid.uuid4()),
        original_filename="8th Eng Science Part - 1 2025-26.pdf",
        storage_path=pdf_path,
        file_size=file_size,
        content_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        status="UPLOADED",
        uploader_id=admin_user.id,
    )
    db.add(doc)
    await db.commit()

    # 2. Process through Ingestion Pipeline
    ai_provider = MockAIProvider()
    pipeline = IngestionPipeline(db, ai_provider)
    ingested_doc = await pipeline.process_document(doc.id)

    # 3. Assert Ingestion Quality Gates
    assert ingested_doc.status == "READY_FOR_REVIEW"
    assert ingested_doc.page_count == 96
    assert ingested_doc.part == "Part I"
    assert ingested_doc.grade_level == 8

    # Check validation report
    assert ingested_doc.validation_results is not None
    val_report = json.loads(ingested_doc.validation_results)
    assert val_report["physical_pages"] == 96
    assert val_report["front_matter_pages"] == 12
    assert val_report["content_pages"] == 84
    assert val_report["detected_chapters_count"] == 6
    assert val_report["chapter_numbers"] == [1, 2, 3, 4, 8, 9]
    assert val_report["missing_chapter_numbers"] == [5, 6, 7]
    assert val_report["non_contiguous_status"] == "VALID NON-CONTIGUOUS VOLUME"
    assert val_report["section_detection"] == "PASS"
    assert val_report["page_mapping"] == "PASS"
    assert val_report["page_offset"] == 12
    assert val_report["chunks_count"] > 100

    # 4. Verify Database Records
    # Chapters
    ch_stmt = select(Chapter).where(Chapter.book_id == ingested_doc.book_id).order_by(Chapter.chapter_number)
    ch_res = await db.execute(ch_stmt)
    chapters = list(ch_res.scalars().all())
    assert len(chapters) == 6
    ch_nums = [c.chapter_number for c in chapters]
    assert ch_nums == [1, 2, 3, 4, 8, 9]

    # Verify Chapter 1 boundaries
    ch1 = chapters[0]
    assert ch1.chapter_number == 1
    assert "CROP PRODUCTION" in ch1.title.upper()
    assert ch1.pdf_page_start == 13
    assert ch1.printed_page_start == 1

    # Verify Chapter 9 boundaries
    ch9 = chapters[5]
    assert ch9.chapter_number == 9
    assert "FRICTION" in ch9.title.upper()
    assert ch9.pdf_page_start == 84
    assert ch9.printed_page_start == 72

    # Activities
    act_stmt = select(CurriculumActivity)
    act_res = await db.execute(act_stmt)
    activities = list(act_res.scalars().all())
    assert len(activities) >= 20
    # Activity 1.1 should exist
    act_11 = next((a for a in activities if "1.1" in a.activity_number), None)
    assert act_11 is not None
    assert act_11.pdf_page in (15, 16)
    assert act_11.printed_page in (3, 4)

    # Figures
    fig_stmt = select(CurriculumFigure)
    fig_res = await db.execute(fig_stmt)
    figures = list(fig_res.scalars().all())
    assert len(figures) >= 30

    # Chunks
    chk_stmt = select(ContentChunk).where(ContentChunk.document_id == doc.id)
    chk_res = await db.execute(chk_stmt)
    chunks = list(chk_res.scalars().all())
    assert len(chunks) > 100

    # 5. Review & Publish
    await CurriculumPublisher.approve_document(db, doc.id)
    published_doc = await CurriculumPublisher.publish_document(db, doc.id)
    assert published_doc.status == "PUBLISHED"

    # 6. RAG Retrieval Smoke Test Suite (14 Questions)
    retriever = CurriculumRetriever(db)

    test_queries = [
        ("Why do damaged seeds float on water?", [1], ["hollow", "float", "lighter", "seeds"]),
        ("What is sowing?", [1], ["sowing", "seed", "tool"]),
        ("What are the basic agricultural practices?", [1], ["agricultural", "practices", "preparation", "crop"]),
        ("What is a cultivator used for?", [1], ["cultivator", "tractor", "plough"]),
        ("Where do microorganisms live?", [2], ["microorganisms", "live", "water", "air", "soil"]),
        ("Name some useful microorganisms.", [2], ["useful", "curd", "bacteria", "yeast", "antibiotics"]),
        ("What is fermentation?", [2], ["fermentation", "sugar", "alcohol", "yeast"]),
        ("What are inexhaustible natural resources?", [3], ["inexhaustible", "resources", "sunlight", "air"]),
        ("What is combustion?", [4], ["combustion", "chemical", "heat", "oxygen"]),
        ("What is a fuel?", [4], ["fuel", "combustible", "substance"]),
        ("What is force?", [8], ["force", "push", "pull", "action"]),
        ("What is friction?", [9], ["friction", "opposes", "motion", "surface"]),
        ("Why does a moving ball slow down?", [9], ["slow", "ball", "force", "friction"]),
        ("What does Activity 9.1 demonstrate?", [9], ["9.1", "activity", "friction", "table", "book"]),
    ]

    passed_queries = 0
    for query, expected_chapters, expected_keywords in test_queries:
        retrieved = await retriever.search_textbook_chunks(query, limit=3, status_filter="PUBLISHED")
        assert len(retrieved) > 0, f"Query '{query}' returned no chunks!"

        top_chunk = retrieved[0]
        # Check that top chunk cites printed page and PDF page
        assert top_chunk.pdf_page_number is not None
        assert top_chunk.chapter is not None
        retrieved_ch_num = top_chunk.chapter.chapter_number

        # Format context for prompt and ensure provenance citation is clean
        formatted = retriever.format_context_for_prompt(retrieved[:2])
        assert "Printed Page" in formatted or "PDF Page" in formatted
        assert top_chunk.chapter.title in formatted

        # Check chapter match
        ch_match = retrieved_ch_num in expected_chapters
        # Check keyword match
        combined_text = " ".join(c.chunk_text.lower() for c in retrieved)
        kw_match = any(kw.lower() in combined_text for kw in expected_keywords)

        assert ch_match or kw_match, f"Query '{query}' failed: retrieved ch {retrieved_ch_num}, text: {combined_text[:100]}"
        passed_queries += 1

    assert passed_queries == 14
