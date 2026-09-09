import pytest
import os
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.curriculum import CurriculumDocument, Topic, Concept, ContentChunk
from app.services.curriculum_ingestion.pipeline import IngestionPipeline
from app.services.curriculum_ingestion.publisher import CurriculumPublisher
from app.services.rag.retriever import CurriculumRetriever
from app.services.ai.mock_provider import MockAIProvider
from tests.fixtures.ncert_pdf_generator import generate_class_8_combustion_textbook_pdf
from app.core.config import settings


@pytest.mark.asyncio
async def test_draft_chunks_not_retrieved_until_published(db_session: AsyncSession):
    """
    Verifies Requirement 25:
    Only PUBLISHED curriculum content is accessible to RAG and the AI Tutor.
    Draft / unreviewed chunks must never leak into live student queries.
    """
    db = db_session
    if True:
        # 1. Resolve an admin user
        u_stmt = select(User).where(User.role == "admin")
        u_res = await db.execute(u_stmt)
        admin_user = u_res.scalars().first()
        if not admin_user:
            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin_rag@test.com",
                hashed_password="hash",
                role="admin",
            )
            db.add(admin_user)
            await db.commit()

        # 2. Write PDF to temporary storage
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        pdf_bytes = generate_class_8_combustion_textbook_pdf()
        temp_path = os.path.join(settings.UPLOAD_DIR, f"test_rag_{uuid.uuid4().hex}.pdf")
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)

        # 3. Create document record
        doc = CurriculumDocument(
            id=str(uuid.uuid4()),
            original_filename="ncert_ch4_combustion.pdf",
            storage_path=temp_path,
            file_size=len(pdf_bytes),
            content_hash=uuid.uuid4().hex,
            mime_type="application/pdf",
            status="UPLOADED",
            uploader_id=admin_user.id,
        )
        db.add(doc)
        await db.commit()

        # 4. Run ingestion pipeline
        ai_provider = MockAIProvider()
        pipeline = IngestionPipeline(db, ai_provider)
        processed_doc = await pipeline.process_document(doc.id)
        assert processed_doc.status == "READY_FOR_REVIEW"

        # 5. Resolve newly created topic
        chunks_stmt = select(ContentChunk).where(ContentChunk.document_id == doc.id)
        c_res = await db.execute(chunks_stmt)
        ingested_chunks = c_res.scalars().all()
        assert len(ingested_chunks) > 0

        target_topic_id = ingested_chunks[0].topic_id
        assert target_topic_id is not None

        # Verify all ingested chunks start with status READY_FOR_REVIEW
        for chunk in ingested_chunks:
            assert chunk.status == "READY_FOR_REVIEW"

        # 6. Query RAG retriever before publishing -> MUST RETURN 0 CHUNKS
        retriever = CurriculumRetriever(db)
        retrieved_before = await retriever.get_topic_chunks(
            topic_id=target_topic_id,
            query_text="What is combustion?",
        )
        assert len(retrieved_before) == 0, "Draft/unreviewed chunks leaked into retriever!"

        # 7. Approve document
        approved_doc = await CurriculumPublisher.approve_document(db, doc.id)
        assert approved_doc.status == "REVIEWED"

        # Still not published -> should still return 0 chunks
        retrieved_mid = await retriever.get_topic_chunks(
            topic_id=target_topic_id,
            query_text="What is combustion?",
        )
        assert len(retrieved_mid) == 0

        # 8. Publish document
        published_doc = await CurriculumPublisher.publish_document(db, doc.id)
        assert published_doc.status == "PUBLISHED"

        # 9. Query RAG retriever after publishing -> MUST RETURN GROUNDED CHUNKS
        retrieved_after = await retriever.get_topic_chunks(
            topic_id=target_topic_id,
            query_text="What is combustion?",
        )
        assert len(retrieved_after) > 0
        top_chunk = retrieved_after[0]
        assert top_chunk.status == "PUBLISHED"
        assert top_chunk.page_number >= 1

        # Check prompt formatting includes source citations
        formatted = retriever.format_context_for_prompt(retrieved_after)
        assert f"Page {top_chunk.page_number}" in formatted
        assert "Combustion" in formatted
