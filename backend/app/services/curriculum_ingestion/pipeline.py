import json
import time
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import CurriculumDocument, ContentChunk
from app.services.curriculum_ingestion.extractor import PDFExtractor
from app.services.curriculum_ingestion.parser import DocumentParser
from app.services.curriculum_ingestion.builder import CurriculumBuilder
from app.services.curriculum_ingestion.embedder import CurriculumEmbedder
from app.services.curriculum_ingestion.question_generator import CurriculumQuestionGenerator
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

            parsed_chapters, parse_warnings = DocumentParser.parse_pages(
                pages=pages,
                fallback_title=doc.original_filename.replace(".pdf", "").title(),
            )
            warnings.extend(parse_warnings)

            # Stage 4: CHUNKING & HIERARCHY PERSISTENCE
            doc.status = "CHUNKING"
            doc.processing_stage = "chunking_and_linking"
            await self.db.commit()

            builder = CurriculumBuilder(self.db, self.ai_provider)
            chapters, chunks, concepts = await builder.build_curriculum(doc, parsed_chapters)

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

            # Stage 7: READY_FOR_REVIEW
            duration = round((time.time() - start_time) * 1000, 2)
            doc.status = "READY_FOR_REVIEW"
            doc.processing_stage = "ready_for_review"
            doc.warnings = "; ".join(warnings) if warnings else None
            doc.metrics_json = json.dumps({
                "duration_ms": duration,
                "pages_count": len(pages),
                "chapters_count": len(chapters),
                "chunks_count": len(chunks),
                "embedded_count": embedded_count,
                "questions_count": q_count,
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
