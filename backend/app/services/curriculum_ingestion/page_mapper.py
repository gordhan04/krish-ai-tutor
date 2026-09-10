import re
from typing import List, Dict, Optional, Tuple, Any
from app.services.curriculum_ingestion.extractor import ExtractedPage
from app.services.curriculum_ingestion.toc_detector import TOCEntry


class PageMapper:
    """
    Computes the mapping between physical PDF page numbers and printed textbook page numbers.
    Reconciles TOC printed page targets with detected chapter start PDF pages to determine
    front matter boundary and deterministic page offset.
    """

    def __init__(
        self,
        offset: int = 0,
        front_matter_end_pdf: int = 0,
        confidence: str = "LOW",
        direct_mappings: Optional[Dict[int, int]] = None,
    ):
        self.offset = offset
        self.front_matter_end_pdf = front_matter_end_pdf
        self.confidence = confidence
        self.direct_mappings = direct_mappings or {}

    def pdf_to_printed(self, pdf_page: int) -> Optional[int]:
        """Convert physical PDF page to printed page number."""
        if pdf_page <= self.front_matter_end_pdf:
            return None
        if pdf_page in self.direct_mappings and self.direct_mappings[pdf_page] > 0:
            return self.direct_mappings[pdf_page]
        printed = pdf_page - self.offset
        return printed if printed > 0 else None

    def printed_to_pdf(self, printed_page: int) -> int:
        """Convert printed page number to physical PDF page."""
        for pdf_p, pr_p in self.direct_mappings.items():
            if pr_p == printed_page:
                return pdf_p
        return printed_page + self.offset

    def is_front_matter(self, pdf_page: int) -> bool:
        """Returns True if the given physical PDF page belongs to front matter."""
        return pdf_page <= self.front_matter_end_pdf

    @classmethod
    def analyze_pages(
        cls,
        pages: List[ExtractedPage],
        toc_entries: Optional[List[TOCEntry]] = None,
        chapter_candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> "PageMapper":
        """
        Analyzes extracted pages, TOC targets, and candidate chapter locations to infer
        the page mapping and offset.
        """
        if not pages:
            return cls(offset=0, front_matter_end_pdf=0, confidence="LOW")

        detected_direct: Dict[int, int] = {}
        offsets: List[int] = []

        # 1. Look for explicit printed page numbers on pages (headers/footers)
        for page in pages:
            lines = page.lines
            if not lines:
                continue

            # Check header (first 3 lines) and footer (last 3 lines)
            boundary_lines = lines[:3] + lines[-3:]
            for line in boundary_lines:
                # Match "SCIENCE4" or "4 SCIENCE" or isolated "4"
                m_num = re.search(r'(?:SCIENCE|CHAPTER\s*\d+)?\s*(\d{1,4})\s*(?:SCIENCE)?$', line, re.IGNORECASE)
                if m_num:
                    val = int(m_num.group(1))
                    # Basic sanity check: printed page should be <= pdf_page
                    if 0 < val <= page.page_number:
                        detected_direct[page.page_number] = val
                        offsets.append(page.page_number - val)
                        break

        # 2. Correlate TOC target pages with detected chapter start pages
        if toc_entries and chapter_candidates:
            toc_map = {e.number: e.target_page for e in toc_entries if e.target_page and e.target_page > 0}
            for ch in chapter_candidates:
                num = ch.get("chapter_number")
                pdf_start = ch.get("start_page")
                if num in toc_map and pdf_start:
                    target_pr = toc_map[num]
                    computed_offset = pdf_start - target_pr
                    if computed_offset >= 0:
                        offsets.append(computed_offset)

        # 3. Determine consensus offset
        if offsets:
            from collections import Counter
            counts = Counter(offsets)
            best_offset, count = counts.most_common(1)[0]
            confidence = "HIGH" if count >= 3 else ("MEDIUM" if count >= 1 else "LOW")
            front_matter_end = best_offset
            return cls(
                offset=best_offset,
                front_matter_end_pdf=front_matter_end,
                confidence=confidence,
                direct_mappings=detected_direct,
            )

        # Fallback: assume 0 offset (1:1 mapping)
        return cls(offset=0, front_matter_end_pdf=0, confidence="LOW", direct_mappings={})
