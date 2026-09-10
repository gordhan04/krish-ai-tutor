import hashlib
import os
import re
import uuid
from typing import Tuple, Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import CurriculumDocument
from app.core.config import settings


class IngestionValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DocumentValidator:
    """
    Validates uploaded textbook documents:
    - MIME type & file extension
    - Magic bytes (%PDF-)
    - File size limits
    - Path traversal defense
    - Duplicate detection via SHA-256 content hashing
    """

    PDF_MAGIC_BYTES = b"%PDF-"

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Strips directory traversal sequences and special characters."""
        basename = os.path.basename(filename)
        cleaned = re.sub(r"[^\w\.\-\s]", "_", basename).strip()
        return cleaned or "textbook.pdf"

    @classmethod
    def compute_sha256(cls, content: bytes) -> str:
        """Calculates hexadecimal SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def validate_file_content(cls, content: bytes, filename: str, content_type: Optional[str] = None) -> Tuple[str, str]:
        """
        Validates the raw file content and returns (sanitized_name, sha256_hash).
        Raises IngestionValidationError on failure.
        """
        # 1. Extension check
        sanitized_name = cls.sanitize_filename(filename)
        if not sanitized_name.lower().endswith(".pdf"):
            raise IngestionValidationError("Only PDF (.pdf) documents are accepted.", status_code=400)

        # 2. MIME type check
        if content_type and content_type.lower() not in ("application/pdf", "application/x-pdf", "binary/octet-stream"):
            raise IngestionValidationError(f"Invalid MIME type '{content_type}'. Must be application/pdf.", status_code=400)

        # 3. Magic bytes / file signature check
        if not content.startswith(cls.PDF_MAGIC_BYTES):
            raise IngestionValidationError("Invalid file signature. File does not appear to be a genuine PDF.", status_code=400)

        # 4. File size check
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise IngestionValidationError(
                f"File size ({round(len(content) / (1024 * 1024), 2)} MB) exceeds maximum allowed ({settings.MAX_UPLOAD_SIZE_MB} MB).",
                status_code=413,
            )

        # 5. Non-empty check
        if len(content) < 100:
            raise IngestionValidationError("File is empty or corrupted.", status_code=400)

        content_hash = cls.compute_sha256(content)
        return sanitized_name, content_hash

    @classmethod
    async def check_duplicate(cls, db: AsyncSession, content_hash: str) -> Optional[CurriculumDocument]:
        """Checks if a document with this content hash already exists in the database."""
        stmt = select(CurriculumDocument).where(CurriculumDocument.content_hash == content_hash)
        res = await db.execute(stmt)
        return res.scalars().first()


class CurriculumQualityValidator:
    """
    Performs comprehensive post-ingestion document validation:
    - Physical vs content vs front matter page counts
    - Chapter sequence and non-contiguous chapter classification
    - Dual page mapping validation
    - Entity counts (activities, figures, sections, chunks)
    - Structural confidence level
    """

    @classmethod
    def validate_document_quality(
        cls,
        total_physical_pages: int,
        front_matter_pages: int,
        chapters: List[Any],
        chunks: List[Any],
        activities_count: int,
        figures_count: int,
        toc_entries_count: int,
        page_offset: int,
        page_mapping_confidence: str,
        total_sections: Optional[int] = None,
    ) -> Dict[str, Any]:
        ch_numbers = [c.chapter_number for c in chapters]
        is_contiguous = ch_numbers == list(range(min(ch_numbers), max(ch_numbers) + 1)) if ch_numbers else True
        missing_numbers = sorted(list(set(range(min(ch_numbers), max(ch_numbers) + 1)) - set(ch_numbers))) if ch_numbers else []

        volume_status = "VALID NON-CONTIGUOUS VOLUME" if not is_contiguous else "VALID CONTIGUOUS VOLUME"

        # Quality passes
        if total_sections is None:
            total_sections = sum(len(getattr(c, "sections", [])) for c in chapters if "sections" in getattr(c, "__dict__", {}))
        section_pass = total_sections > 0 or len(chapters) > 0
        page_mapping_pass = page_offset > 0 or total_physical_pages < 10
        chunking_pass = len(chunks) >= (total_physical_pages - front_matter_pages)

        report = {
            "physical_pages": total_physical_pages,
            "front_matter_pages": front_matter_pages,
            "content_pages": total_physical_pages - front_matter_pages,
            "expected_chapters_from_toc": toc_entries_count if toc_entries_count > 0 else len(chapters),
            "detected_chapters_count": len(chapters),
            "chapter_numbers": ch_numbers,
            "missing_chapter_numbers": missing_numbers,
            "non_contiguous_status": volume_status,
            "section_detection": "PASS" if section_pass else "FAIL",
            "page_mapping": "PASS" if page_mapping_pass else "WARNING",
            "page_offset": page_offset,
            "page_mapping_confidence": page_mapping_confidence,
            "activities_detected": activities_count,
            "figures_detected": figures_count,
            "total_sections": total_sections,
            "chunks_count": len(chunks),
            "status": "READY_FOR_REVIEW",
        }
        return report
