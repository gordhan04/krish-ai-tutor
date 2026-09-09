from typing import Dict, Any, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import (
    CurriculumDocument,
    Chapter,
    Section,
    Topic,
    Concept,
    ContentChunk,
)
from app.models.assessment import Question


class CurriculumPublisher:
    """
    Manages the review and publishing lifecycle:
    DRAFT / READY_FOR_REVIEW -> REVIEWED -> PUBLISHED.
    Ensures that only published curriculum entities are retrieved into live tutoring.
    """

    @classmethod
    async def approve_document(cls, db: AsyncSession, document_id: str) -> Optional[CurriculumDocument]:
        """Marks a document and its child entities as REVIEWED."""
        stmt = select(CurriculumDocument).where(CurriculumDocument.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            return None

        doc.status = "REVIEWED"
        doc.processing_stage = "approved"

        # Update child entities
        if doc.chapter_id:
            await db.execute(update(Chapter).where(Chapter.id == doc.chapter_id).values(status="REVIEWED"))

        await db.execute(update(ContentChunk).where(ContentChunk.document_id == document_id).values(status="REVIEWED"))
        await db.commit()
        await db.refresh(doc)
        return doc

    @classmethod
    async def publish_document(cls, db: AsyncSession, document_id: str) -> Optional[CurriculumDocument]:
        """Atomically flips document and all child hierarchy to PUBLISHED."""
        stmt = select(CurriculumDocument).where(CurriculumDocument.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            return None

        doc.status = "PUBLISHED"
        doc.processing_stage = "completed"

        # Atomically publish child entities
        if doc.chapter_id:
            await db.execute(update(Chapter).where(Chapter.id == doc.chapter_id).values(status="PUBLISHED"))
            # Publish sections
            s_stmt = select(Section).where(Section.chapter_id == doc.chapter_id)
            s_res = await db.execute(s_stmt)
            sections = s_res.scalars().all()
            for s in sections:
                s.status = "PUBLISHED"
                # Publish topics
                t_stmt = select(Topic).where(Topic.section_id == s.id)
                t_res = await db.execute(t_stmt)
                topics = t_res.scalars().all()
                for t in topics:
                    t.status = "PUBLISHED"
                    # Publish concepts
                    c_stmt = select(Concept).where(Concept.topic_id == t.id)
                    c_res = await db.execute(c_stmt)
                    concepts = c_res.scalars().all()
                    for c in concepts:
                        c.status = "PUBLISHED"
                        # Publish generated questions
                        await db.execute(
                            update(Question)
                            .where(Question.concept_id == c.id)
                            .values(is_published=True)
                        )

        # Publish all chunks belonging to this document
        await db.execute(
            update(ContentChunk)
            .where(ContentChunk.document_id == document_id)
            .values(status="PUBLISHED")
        )

        await db.commit()
        await db.refresh(doc)
        return doc
