import re
from typing import List, Set, Dict
from collections import Counter
from app.services.curriculum_ingestion.extractor import ExtractedPage


class HeaderFooterDetector:
    """
    Identifies and suppresses repeated page headers, footers, page numbers,
    and publication/typesetting artifacts across multi-page textbook documents.
    """

    KNOWN_ARTIFACT_PATTERNS = [
        # InDesign export marks: e.g. "0_Prelims.indd 180_Prelims.indd 18 6/30/2025 1:56:17 PM"
        r"[\w\.\-]+\.indd\s+\d+",
        # Reprint notices: e.g. "Reprint 2026-27"
        r"^(?:Reprint|Revised\s+Edition|First\s+Edition)\s+\d{4}(?:-\d{2,4})?",
        # Standalone page numbers (Arabic or Roman)
        r"^(?:\d+|[ivxlcdm]+)$",
        # Barcodes / production codes: e.g. "PD 730T SM"
        r"^[A-Z0-9]{2,8}\s+[A-Z0-9]{2,8}(?:\s+[A-Z0-9]{2,8})?$",
    ]

    @classmethod
    def detect_repeated_lines(cls, pages: List[ExtractedPage], threshold_ratio: float = 0.15, min_occurrences: int = 3) -> Set[str]:
        """
        Detects lines appearing repeatedly in header (first 3 lines)
        or footer (last 3 lines) positions across multiple pages.
        """
        if len(pages) < 3:
            return set()

        header_footer_candidates: List[str] = []
        for p in pages:
            lines = p.lines
            if not lines:
                continue
            # Check top 3 lines
            top_slice = lines[:min(3, len(lines))]
            # Check bottom 3 lines
            bottom_slice = lines[max(0, len(lines) - 3):]
            
            for l in set(top_slice + bottom_slice):
                normalized = l.strip().lower()
                if len(normalized) > 2:
                    header_footer_candidates.append(normalized)

        counts = Counter(header_footer_candidates)
        required_count = max(min_occurrences, int(len(pages) * threshold_ratio))
        
        repeated = {
            line for line, count in counts.items()
            if count >= required_count
        }
        return repeated

    @classmethod
    def is_artifact_line(cls, line: str, repeated_lines: Set[str]) -> bool:
        """Determines whether an individual line is a running header, footer, or print artifact."""
        stripped = line.strip()
        if not stripped:
            return True

        lower = stripped.lower()
        if lower in repeated_lines:
            return True

        for pattern in cls.KNOWN_ARTIFACT_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                return True

        return False

    @classmethod
    def clean_page(cls, page: ExtractedPage, repeated_lines: Set[str]) -> ExtractedPage:
        """Returns a new ExtractedPage with running headers, footers, and artifacts stripped."""
        cleaned_lines = [
            l for l in page.lines
            if not cls.is_artifact_line(l, repeated_lines)
        ]
        cleaned_text = "\n".join(cleaned_lines)
        new_page = ExtractedPage(page_number=page.page_number, text=cleaned_text)
        new_page.lines = cleaned_lines
        return new_page

    @classmethod
    def clean_document_pages(cls, pages: List[ExtractedPage]) -> List[ExtractedPage]:
        """Cleans all pages in the document by removing identified headers, footers, and artifacts."""
        repeated = cls.detect_repeated_lines(pages)
        return [cls.clean_page(p, repeated) for p in pages]
