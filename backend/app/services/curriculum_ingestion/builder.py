from typing import List, Dict, Any, Tuple, Optional
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
    CurriculumActivity,
    CurriculumFigure,
)
from app.services.curriculum_ingestion.parser import (
    ParsedChapter,
    ParsedSection,
    ParsedActivity,
    ParsedFigure,
    ParsedFrontMatter,
)
from app.services.curriculum_ingestion.chunker import SemanticChunker, RawChunkCandidate
from app.services.curriculum_ingestion.page_mapper import PageMapper
from app.services.ai.base import AIProvider


class CurriculumBuilder:
    """
    Constructs normalized database entities from parsed curriculum structures
    while maintaining strict hierarchy, dual page numbers, activities, figures,
    and source traceability.
    """

    def __init__(self, db: AsyncSession, ai_provider: AIProvider):
        self.db = db
        self.ai_provider = ai_provider

    async def build_curriculum(
        self,
        document: CurriculumDocument,
        parsed_chapters: List[ParsedChapter],
        front_matter: Optional[List[ParsedFrontMatter]] = None,
        page_mapper: Optional[PageMapper] = None,
        target_subject_name: str = "Science",
        target_book_title: str = "Class 8 Science Part I",
    ) -> Tuple[List[Chapter], List[ContentChunk], List[Concept]]:
        """
        Builds and inserts database hierarchy for the document.
        All new entities are initialized with status='READY_FOR_REVIEW'.
        """
        mapper = page_mapper or PageMapper(offset=0, front_matter_end_pdf=0)

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
                publisher="Karnataka Textbook Society (KTBS) / NCERT",
                edition="2025-26 Edition",
            )
            self.db.add(book)
            await self.db.flush()

        document.book_id = book.id

        created_chapters: List[Chapter] = []
        created_chunks: List[ContentChunk] = []
        created_concepts: List[Concept] = []
        seq = 1

        # 3. Build Chapters and Sections
        for p_ch in parsed_chapters:
            chapter = Chapter(
                book_id=book.id,
                chapter_number=p_ch.chapter_number,
                title=p_ch.title,
                description=p_ch.raw_intro_text[:300] if p_ch.raw_intro_text else f"Chapter {p_ch.chapter_number}: {p_ch.title}",
                status="READY_FOR_REVIEW",
                pdf_page_start=p_ch.start_page,
                pdf_page_end=p_ch.end_page,
                printed_page_start=p_ch.printed_start_page,
                printed_page_end=p_ch.printed_end_page,
                source_sequence=p_ch.source_sequence or seq,
            )
            seq += 1
            self.db.add(chapter)
            await self.db.flush()
            created_chapters.append(chapter)

            if not document.chapter_id:
                document.chapter_id = chapter.id

            # Save Chapter-level Activities
            for act in p_ch.activities:
                act_obj = CurriculumActivity(
                    chapter_id=chapter.id,
                    activity_number=act.number,
                    title=act.title,
                    instructions=act.instructions,
                    expected_observation=act.expected_observation,
                    safety_notes=act.safety_notes,
                    pdf_page=act.pdf_page,
                    printed_page=act.printed_page,
                    source_sequence=act.source_sequence,
                )
                self.db.add(act_obj)

            # Save Chapter-level Figures
            for fig in p_ch.figures:
                fig_obj = CurriculumFigure(
                    chapter_id=chapter.id,
                    figure_number=fig.number,
                    caption=fig.caption,
                    image_reference=fig.image_reference,
                    pdf_page=fig.pdf_page,
                    printed_page=fig.printed_page,
                    source_sequence=fig.source_sequence,
                )
                self.db.add(fig_obj)

            for s_idx, p_sec in enumerate(p_ch.sections, 1):
                section = Section(
                    chapter_id=chapter.id,
                    section_number=p_sec.section_number,
                    title=p_sec.title,
                    status="READY_FOR_REVIEW",
                    start_pdf_page=p_sec.start_page,
                    end_pdf_page=p_sec.end_page,
                    start_printed_page=p_sec.start_printed_page,
                    end_printed_page=p_sec.end_printed_page,
                    source_sequence=p_sec.source_sequence or seq,
                )
                seq += 1
                self.db.add(section)
                await self.db.flush()

                # Link section activities and figures
                for s_act in p_sec.activities:
                    s_act_obj = CurriculumActivity(
                        chapter_id=chapter.id,
                        section_id=section.id,
                        activity_number=s_act.number,
                        title=s_act.title,
                        instructions=s_act.instructions,
                        expected_observation=s_act.expected_observation,
                        safety_notes=s_act.safety_notes,
                        pdf_page=s_act.pdf_page,
                        printed_page=s_act.printed_page,
                        source_sequence=s_act.source_sequence,
                    )
                    self.db.add(s_act_obj)

                for s_fig in p_sec.figures:
                    s_fig_obj = CurriculumFigure(
                        chapter_id=chapter.id,
                        section_id=section.id,
                        figure_number=s_fig.number,
                        caption=s_fig.caption,
                        image_reference=s_fig.image_reference,
                        pdf_page=s_fig.pdf_page,
                        printed_page=s_fig.printed_page,
                        source_sequence=s_fig.source_sequence,
                    )
                    self.db.add(s_fig_obj)

                topic = Topic(
                    section_id=section.id,
                    title=p_sec.title,
                    order_index=s_idx,
                    status="READY_FOR_REVIEW",
                )
                self.db.add(topic)
                await self.db.flush()

                # Extract concepts & learning objectives
                combined_sec_text = " ".join(t[1] if isinstance(t, tuple) else str(t) for t in p_sec.raw_text_blocks)
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
                if p_sec.raw_text_blocks and isinstance(p_sec.raw_text_blocks[0], tuple):
                    blocks = p_sec.raw_text_blocks
                else:
                    blocks = [(p_sec.start_page, str(l)) for l in p_sec.raw_text_blocks]

                raw_chunks = SemanticChunker.chunk_section_blocks(
                    text_blocks=blocks,
                    chapter_number=p_ch.chapter_number,
                    chapter_title=p_ch.title,
                    section_number=p_sec.section_number,
                    section_title=p_sec.title,
                    page_mapper=mapper,
                    starting_sequence=seq,
                )
                seq += len(raw_chunks)

                for r_chunk in raw_chunks:
                    chunk = ContentChunk(
                        book_id=book.id,
                        chapter_id=chapter.id,
                        section_id=section.id,
                        topic_id=topic.id,
                        concept_id=primary_concept.id if primary_concept else None,
                        document_id=document.id,
                        page_number=r_chunk.pdf_page_start,
                        pdf_page_number=r_chunk.pdf_page_start,
                        printed_page_number=r_chunk.printed_page_start,
                        source_sequence=r_chunk.source_sequence,
                        heading_path=r_chunk.heading_path,
                        content_type=r_chunk.content_type,
                        chunk_text=r_chunk.chunk_text,
                        status="READY_FOR_REVIEW",
                    )
                    self.db.add(chunk)
                    created_chunks.append(chunk)

                await self.db.flush()

        # 4. Front Matter Chunks (metadata reference only)
        if front_matter and created_chapters:
            first_ch = created_chapters[0]
            fm_blocks = []
            for fm in front_matter:
                for item in fm.text_blocks:
                    if isinstance(item, tuple):
                        fm_blocks.append(item)
                    else:
                        fm_blocks.append((fm.start_page, str(item)))

            if fm_blocks:
                fm_chunks = SemanticChunker.chunk_front_matter(fm_blocks, mapper, starting_sequence=seq)
                seq += len(fm_chunks)
                for r_fm in fm_chunks:
                    chunk = ContentChunk(
                        book_id=book.id,
                        chapter_id=first_ch.id,
                        document_id=document.id,
                        page_number=r_fm.pdf_page_start,
                        pdf_page_number=r_fm.pdf_page_start,
                        printed_page_number=None,
                        source_sequence=r_fm.source_sequence,
                        heading_path=r_fm.heading_path,
                        content_type="FRONT_MATTER",
                        chunk_text=r_fm.chunk_text,
                        status="READY_FOR_REVIEW",
                    )
                    self.db.add(chunk)
                    created_chunks.append(chunk)

                await self.db.flush()

        return created_chapters, created_chunks, created_concepts
