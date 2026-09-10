import logging
import sqlite3
import os
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal, is_sqlite, engine, Base
from app.models.curriculum import (
    CurriculumDocument,
    ContentChunk,
    Chapter,
    Section,
    CurriculumActivity,
    CurriculumFigure,
    Book,
    Subject,
)

logger = logging.getLogger("krish_ai_tutor.db_rebuilder")


def migrate_sqlite_schema(db_path: str):
    """
    Applies non-destructive schema migrations for SQLite database:
    Adds missing columns to curriculum_documents, chapters, sections, content_chunks,
    and creates new tables if not present.
    """
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. curriculum_documents columns
    cursor.execute("PRAGMA table_info(curriculum_documents);")
    doc_cols = {row[1] for row in cursor.fetchall()}
    needed_doc_cols = {
        "part": "VARCHAR(50)",
        "grade_level": "INTEGER DEFAULT 8",
        "document_scope": "TEXT",
        "printed_page_start": "INTEGER",
        "printed_page_end": "INTEGER",
        "validation_results": "TEXT",
    }
    for col, col_type in needed_doc_cols.items():
        if col not in doc_cols:
            cursor.execute(f"ALTER TABLE curriculum_documents ADD COLUMN {col} {col_type};")
            logger.info(f"Added column {col} to curriculum_documents")

    # 2. chapters columns
    cursor.execute("PRAGMA table_info(chapters);")
    chap_cols = {row[1] for row in cursor.fetchall()}
    needed_chap_cols = {
        "pdf_page_start": "INTEGER",
        "pdf_page_end": "INTEGER",
        "printed_page_start": "INTEGER",
        "printed_page_end": "INTEGER",
        "source_sequence": "INTEGER DEFAULT 0",
    }
    for col, col_type in needed_chap_cols.items():
        if col not in chap_cols:
            cursor.execute(f"ALTER TABLE chapters ADD COLUMN {col} {col_type};")
            logger.info(f"Added column {col} to chapters")

    # 3. sections columns
    cursor.execute("PRAGMA table_info(sections);")
    sec_cols = {row[1] for row in cursor.fetchall()}
    needed_sec_cols = {
        "start_pdf_page": "INTEGER",
        "end_pdf_page": "INTEGER",
        "start_printed_page": "INTEGER",
        "end_printed_page": "INTEGER",
        "source_sequence": "INTEGER DEFAULT 0",
    }
    for col, col_type in needed_sec_cols.items():
        if col not in sec_cols:
            cursor.execute(f"ALTER TABLE sections ADD COLUMN {col} {col_type};")
            logger.info(f"Added column {col} to sections")

    # 4. content_chunks columns
    cursor.execute("PRAGMA table_info(content_chunks);")
    chk_cols = {row[1] for row in cursor.fetchall()}
    needed_chk_cols = {
        "pdf_page_number": "INTEGER DEFAULT 1",
        "printed_page_number": "INTEGER",
        "source_sequence": "INTEGER DEFAULT 0",
        "heading_path": "VARCHAR(512)",
        "parent_block_id": "VARCHAR(36)",
    }
    for col, col_type in needed_chk_cols.items():
        if col not in chk_cols:
            cursor.execute(f"ALTER TABLE content_chunks ADD COLUMN {col} {col_type};")
            logger.info(f"Added column {col} to content_chunks")

    # 5. Create curriculum_activities if missing
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS curriculum_activities (
        id VARCHAR(36) PRIMARY KEY,
        chapter_id VARCHAR(36) NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        section_id VARCHAR(36) REFERENCES sections(id) ON DELETE SET NULL,
        activity_number VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        instructions TEXT NOT NULL,
        expected_observation TEXT,
        safety_notes TEXT,
        pdf_page INTEGER DEFAULT 1,
        printed_page INTEGER,
        source_sequence INTEGER DEFAULT 0
    );
    """)

    # 6. Create curriculum_figures if missing
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS curriculum_figures (
        id VARCHAR(36) PRIMARY KEY,
        chapter_id VARCHAR(36) NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        section_id VARCHAR(36) REFERENCES sections(id) ON DELETE SET NULL,
        figure_number VARCHAR(50) NOT NULL,
        caption TEXT NOT NULL,
        image_reference VARCHAR(255),
        pdf_page INTEGER DEFAULT 1,
        printed_page INTEGER,
        source_sequence INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()
    logger.info("SQLite schema migration complete.")


class RAGIndexDiagnostics:
    """
    Diagnostics service to verify RAG Index Integrity and detect orphaned
    or out-of-bounds chunks/embeddings.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_document_index_integrity(self, document_id: str) -> Dict[str, Any]:
        """
        Validates index integrity for a specific document:
        - Checks chunk counts
        - Checks embeddings count and identifies orphans
        - Verifies that all chunk pdf_page_numbers <= document.page_count
        - Verifies that all chunk printed_page_numbers <= document.printed_page_end
        - Checks that all chunks strictly match document_id
        """
        doc = await self.db.get(CurriculumDocument, document_id)
        if not doc:
            return {
                "document_id": document_id,
                "status": "NOT_FOUND",
                "healthy": False,
                "error": f"Document {document_id} does not exist.",
            }

        # Query all chunks for this document
        stmt = (
            select(ContentChunk)
            .where(ContentChunk.document_id == document_id)
        )
        res = await self.db.execute(stmt)
        chunks = list(res.scalars().all())

        total_chunks = len(chunks)
        embedded_chunks = sum(1 for c in chunks if c.embedding is not None)
        missing_embeddings = total_chunks - embedded_chunks

        # Boundary checks
        max_physical = doc.page_count or 9999
        max_printed = doc.printed_page_end or 9999
        min_printed = doc.printed_page_start or 1

        invalid_pdf_pages = []
        invalid_printed_pages = []
        wrong_doc_chunks = []

        for c in chunks:
            if c.document_id != document_id:
                wrong_doc_chunks.append(c.id)

            pdf_p = getattr(c, "pdf_page_number", None) or c.page_number
            if pdf_p < 1 or pdf_p > max_physical:
                invalid_pdf_pages.append({
                    "chunk_id": c.id,
                    "pdf_page": pdf_p,
                    "limit": max_physical,
                })

            pr_p = getattr(c, "printed_page_number", None)
            if pr_p is not None:
                if pr_p < min_printed or pr_p > max_printed:
                    invalid_printed_pages.append({
                        "chunk_id": c.id,
                        "printed_page": pr_p,
                        "limit": max_printed,
                    })

        # Check for orphan embeddings across DB that claim this doc or point to non-existent chunks
        orphan_embeddings_stmt = select(func.count(ContentChunk.id)).where(
            ContentChunk.document_id.is_(None)
        )
        orphan_res = await self.db.execute(orphan_embeddings_stmt)
        global_orphan_chunks = orphan_res.scalar() or 0

        is_healthy = (
            len(invalid_pdf_pages) == 0
            and len(invalid_printed_pages) == 0
            and len(wrong_doc_chunks) == 0
            and total_chunks > 0
        )

        status_str = "HEALTHY" if is_healthy else "CORRUPTED"

        return {
            "document_id": document_id,
            "filename": doc.original_filename,
            "status": status_str,
            "healthy": is_healthy,
            "total_physical_pages": doc.page_count,
            "printed_page_range": f"{doc.printed_page_start}–{doc.printed_page_end}",
            "chunks_count": total_chunks,
            "embeddings_count": embedded_chunks,
            "missing_embeddings_count": missing_embeddings,
            "orphan_chunks_in_doc": len(wrong_doc_chunks),
            "global_orphan_chunks": global_orphan_chunks,
            "invalid_pdf_page_references": len(invalid_pdf_pages),
            "invalid_printed_page_references": len(invalid_printed_pages),
            "details": {
                "invalid_pdf_pages": invalid_pdf_pages[:5],
                "invalid_printed_pages": invalid_printed_pages[:5],
            },
        }

    async def reset_and_rebuild_document_index(self, document_id: str) -> Dict[str, Any]:
        """
        Safely clears and re-embeds all chunks for a document without destroying curriculum hierarchy.
        """
        from app.services.curriculum_ingestion.embedder import ChunkEmbedder
        from app.services.ai import get_ai_provider

        doc = await self.db.get(CurriculumDocument, document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        # Re-embed all chunks
        ai_provider = get_ai_provider()
        embedder = ChunkEmbedder(self.db, ai_provider)
        count = await embedder.embed_document_chunks(document_id)

        # Re-check integrity
        return await self.check_document_index_integrity(document_id)
