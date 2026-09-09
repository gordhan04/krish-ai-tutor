from typing import List, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.services.curriculum_ingestion.parser import ParsedChapter
from app.services.curriculum_ingestion.chunker import SemanticChunker
from app.services.ai.base import AIProvider


class CurriculumBuilder:
    """
    Constructs normalized database entities from parsed curriculum structures
    while maintaining strict hierarchy and source traceability.
    """

    def __init__(self, db: AsyncSession, ai_provider: AIProvider):
        self.db = db
        self.ai_provider = ai_provider

    async def build_curriculum(
        self,
        document: CurriculumDocument,
        parsed_chapters: List[ParsedChapter],
        target_subject_name: str = "Science",
        target_book_title: str = "NCERT Science Class 8",
    ) -> Tuple[List[Chapter], List[ContentChunk]]:
        """
        Builds and inserts database hierarchy for the document.
        All new entities are initialized with status='READY_FOR_REVIEW'.
        """
        # 1. Resolve or create Subject
        stmt = select(Subject).where(Subject.name == target_subject_name)
        res = await self.db.execute(stmt)
        subject = res.scalars().first()
        if not subject:
            subject = Subject(name=target_subject_name, grade_level=8, icon="atom")
            self.db.add(subject)
            await self.db.flush()

        document.subject_id = subject.id

        # 2. Resolve or create Book
        b_stmt = select(Book).where(Book.subject_id == subject.id, Book.title == target_book_title)
        b_res = await self.db.execute(b_stmt)
        book = b_res.scalars().first()
        if not book:
            book = Book(
                subject_id=subject.id,
                title=target_book_title,
                publisher="NCERT",
                edition="2024-25 Edition",
            )
            self.db.add(book)
            await self.db.flush()

        document.book_id = book.id

        created_chapters: List[Chapter] = []
        created_chunks: List[ContentChunk] = []
        created_concepts: List[Concept] = []

        # 3. Build Chapters and Sections
        for p_ch in parsed_chapters:
            chapter = Chapter(
                book_id=book.id,
                chapter_number=p_ch.chapter_number,
                title=p_ch.title,
                description=p_ch.raw_intro_text[:300] if p_ch.raw_intro_text else f"Chapter {p_ch.chapter_number}: {p_ch.title}",
                status="READY_FOR_REVIEW",
            )
            self.db.add(chapter)
            await self.db.flush()
            created_chapters.append(chapter)

            if not document.chapter_id:
                document.chapter_id = chapter.id

            for s_idx, p_sec in enumerate(p_ch.sections, 1):
                section = Section(
                    chapter_id=chapter.id,
                    section_number=p_sec.section_number,
                    title=p_sec.title,
                    status="READY_FOR_REVIEW",
                )
                self.db.add(section)
                await self.db.flush()

                topic = Topic(
                    section_id=section.id,
                    title=p_sec.title,
                    order_index=s_idx,
                    status="READY_FOR_REVIEW",
                )
                self.db.add(topic)
                await self.db.flush()

                # Extract concepts & learning objectives
                combined_sec_text = " ".join(p_sec.raw_text_blocks)
                extracted_data = await self.ai_provider.extract_concepts_and_objectives(topic.title, combined_sec_text)

                concept_objs = []
                for c_data in extracted_data.get("concepts", []):
                    c_obj = Concept(
                        topic_id=topic.id,
                        name=c_data.get("name", topic.title),
                        summary=c_data.get("summary", f"Key insights into {topic.title}"),
                        difficulty_tier=c_data.get("difficulty_tier", 2),
                        status="READY_FOR_REVIEW",
                    )
                    self.db.add(c_obj)
                    concept_objs.append(c_obj)
                    created_concepts.append(c_obj)

                await self.db.flush()
                primary_concept = concept_objs[0] if concept_objs else None

                for o_data in extracted_data.get("learning_objectives", []):
                    obj = LearningObjective(
                        topic_id=topic.id,
                        concept_id=primary_concept.id if primary_concept else None,
                        statement=o_data.get("statement", f"Understand {topic.title}"),
                        bloom_taxonomy_level=o_data.get("bloom_taxonomy_level", "Understanding"),
                    )
                    self.db.add(obj)

                # Generate Semantic Content Chunks
                raw_chunks = SemanticChunker.chunk_section_text(
                    text_lines=p_sec.raw_text_blocks,
                    start_page=p_sec.start_page,
                    section_number=p_sec.section_number,
                )

                for r_chunk in raw_chunks:
                    chunk = ContentChunk(
                        book_id=book.id,
                        chapter_id=chapter.id,
                        section_id=section.id,
                        topic_id=topic.id,
                        concept_id=primary_concept.id if primary_concept else None,
                        document_id=document.id,
                        page_number=r_chunk.page_number,
                        content_type=r_chunk.content_type,
                        chunk_text=r_chunk.chunk_text,
                        status="READY_FOR_REVIEW",
                    )
                    self.db.add(chunk)
                    created_chunks.append(chunk)

                await self.db.flush()

        return created_chapters, created_chunks, created_concepts
