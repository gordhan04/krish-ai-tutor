import json
import time
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import CurriculumDocument, ContentChunk
from app.services.curriculum_ingestion.extractor import PDFExtractor
from app.services.curriculum_ingestion.toc_detector import TOCDetector
from app.services.curriculum_ingestion.page_mapper import PageMapper
from app.services.curriculum_ingestion.parser import DocumentParser
from app.services.curriculum_ingestion.builder import CurriculumBuilder
from app.services.curriculum_ingestion.embedder import CurriculumEmbedder
from app.services.curriculum_ingestion.question_generator import CurriculumQuestionGenerator
from app.services.curriculum_ingestion.validator import CurriculumQualityValidator
from app.services.ai.base import AIProvider


class IngestionPipeline:
    """
    Orchestrates the multi-stage document ingestion workflow:
    UPLOADED -> VALIDATING -> EXTRACTING -> STRUCTURING -> CHUNKING -> EMBEDDING -> GENERATING_CONTENT -> READY_FOR_REVIEW
    """

    def __init__(self, db: AsyncSession, ai_provider: AIProvider):
        self.db = db
        self.ai_provider = ai_provider

    async def process_document(self, document_id: str) -> CurriculumDocument:
        """
        Executes the entire ingestion pipeline for the specified document ID.
        Ensures stage updates and error isolation.
        """
        start_time = time.time()
        stmt = select(CurriculumDocument).where(CurriculumDocument.id == document_id)
        res = await self.db.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        warnings = []
        try:
            # Stage 1: VALIDATING
            doc.status = "VALIDATING"
            doc.processing_stage = "validating"
            await self.db.commit()

            with open(doc.storage_path, "rb") as f:
                content = f.read()

            if len(content) < 100 or not content.startswith(b"%PDF-"):
                doc.status = "FAILED"
                doc.error_message = "File does not contain valid PDF binary signature."
                await self.db.commit()
                return doc

            # Stage 2: EXTRACTING
            doc.status = "EXTRACTING"
            doc.processing_stage = "extracting_text"
            await self.db.commit()

            pages, requires_ocr, ext_warnings = PDFExtractor.extract_from_bytes(content)
            warnings.extend(ext_warnings)
            doc.page_count = len(pages)

            if requires_ocr:
                doc.status = "OCR_REQUIRED"
                doc.processing_stage = "ocr_needed"
                doc.warnings = "; ".join(warnings)
                await self.db.commit()
                return doc

            # Stage 3: STRUCTURING
            doc.status = "STRUCTURING"
            doc.processing_stage = "parsing_hierarchy"
            await self.db.commit()

            # Detect TOC
            toc_pages = TOCDetector.find_toc_pages(pages)
            toc_entries = TOCDetector.parse_toc_entries(toc_pages) if toc_pages else []

            parsed_chapters, front_matter, parse_warnings, parse_meta = DocumentParser.parse_pages(
                pages=pages,
                toc_entries=toc_entries,
                fallback_title=doc.original_filename.replace(".pdf", "").title(),
                return_full=True,
            )
            warnings.extend(parse_warnings)

            # Reconstruct page mapper
            offset = parse_meta.get("page_offset", 0)
            front_matter_pages = parse_meta.get("front_matter_pages", 0)
            mapper = PageMapper(offset=offset, front_matter_end_pdf=front_matter_pages)

            # Set Document Scope and Part Metadata
            is_non_contiguous = parse_meta.get("volume_status") == "VALID NON-CONTIGUOUS VOLUME"
            doc.part = "Part I" if is_non_contiguous or "part" in doc.original_filename.lower() else None
            doc.document_scope = {
                "type": "PARTIAL_TEXTBOOK" if is_non_contiguous else "FULL_TEXTBOOK",
                "part": doc.part or "Full",
                "subject": "Science",
                "grade": 8,
                "volume_status": parse_meta.get("volume_status", "VALID"),
            }
            doc.grade_level = 8
            if mapper.offset > 0:
                doc.printed_page_start = 1
                doc.printed_page_end = len(pages) - mapper.offset

            # Stage 4: CHUNKING & HIERARCHY PERSISTENCE
            doc.status = "CHUNKING"
            doc.processing_stage = "chunking_and_linking"
            await self.db.commit()

            builder = CurriculumBuilder(self.db, self.ai_provider)
            chapters, chunks, concepts = await builder.build_curriculum(
                document=doc,
                parsed_chapters=parsed_chapters,
                front_matter=front_matter,
                page_mapper=mapper,
            )

            # Stage 5: EMBEDDING
            doc.status = "EMBEDDING"
            doc.processing_stage = "generating_embeddings"
            await self.db.commit()

            embedder = CurriculumEmbedder(self.db, self.ai_provider)
            embedded_count = await embedder.embed_chunks(chunks)

            # Stage 6: GENERATING_CONTENT (Candidate questions)
            doc.status = "GENERATING_CONTENT"
            doc.processing_stage = "generating_questions"
            await self.db.commit()

            q_gen = CurriculumQuestionGenerator(self.db, self.ai_provider)
            q_count = await q_gen.generate_questions_for_concepts(concepts, chunks)

            # Stage 7: VALIDATION & READY_FOR_REVIEW
            duration = round((time.time() - start_time) * 1000, 2)
            quality_report = CurriculumQualityValidator.validate_document_quality(
                total_physical_pages=len(pages),
                front_matter_pages=front_matter_pages,
                chapters=chapters,
                chunks=chunks,
                activities_count=parse_meta.get("total_activities", 0),
                figures_count=parse_meta.get("total_figures", 0),
                toc_entries_count=len(toc_entries),
                page_offset=offset,
                page_mapping_confidence="HIGH" if offset > 0 else "LOW",
                total_sections=parse_meta.get("total_sections", 0),
            )

            doc.status = "READY_FOR_REVIEW"
            doc.processing_stage = "ready_for_review"
            doc.warnings = "; ".join(warnings) if warnings else None
            doc.validation_results = json.dumps(quality_report)
            doc.metrics_json = json.dumps({
                "duration_ms": duration,
                "pages_count": len(pages),
                "front_matter_pages": front_matter_pages,
                "content_pages": len(pages) - front_matter_pages,
                "chapters_count": len(chapters),
                "sections_count": parse_meta.get("total_sections", 0),
                "activities_count": parse_meta.get("total_activities", 0),
                "figures_count": parse_meta.get("total_figures", 0),
                "chunks_count": len(chunks),
                "embedded_count": embedded_count,
                "questions_count": q_count,
                "volume_status": parse_meta.get("volume_status", "VALID"),
                "page_offset": offset,
            })
            await self.db.commit()
            await self.db.refresh(doc)
            return doc

        except Exception as e:
            doc.status = "FAILED"
            doc.processing_stage = "failed"
            doc.error_message = f"Pipeline failure: {str(e)}"
            doc.warnings = "; ".join(warnings) if warnings else None
            await self.db.commit()
            return doc
