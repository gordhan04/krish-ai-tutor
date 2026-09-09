import io
import re
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader


class ExtractedPage:
    def __init__(self, page_number: int, text: str):
        self.page_number = page_number
        self.text = text
        self.char_count = len(text.strip())
        self.lines = [line.strip() for line in text.splitlines() if line.strip()]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "char_count": self.char_count,
            "line_count": len(self.lines),
        }


class PDFExtractor:
    """
    Extracts text page-by-page from PDF while preserving page numbers, boundaries,
    and verifying whether text is selectable or requires OCR.
    """

    MIN_AVERAGE_CHARS_PER_PAGE = 50
    MIN_TOTAL_CHARS = 120

    @classmethod
    def extract_from_bytes(cls, content: bytes) -> Tuple[List[ExtractedPage], bool, List[str]]:
        """
        Extracts pages from raw PDF bytes.
        Returns:
            - pages: List of ExtractedPage objects
            - requires_ocr: bool (True if text is insufficient or empty)
            - warnings: List of warning strings
        """
        warnings = []
        pages: List[ExtractedPage] = []

        try:
            reader = PdfReader(io.BytesIO(content))
            num_pages = len(reader.pages)

            if num_pages == 0:
                return [], True, ["PDF contains 0 pages."]

            total_chars = 0
            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                try:
                    text = page.extract_text() or ""
                    cleaned_text = text.replace("\x00", "").strip()
                    extracted_page = ExtractedPage(page_number=page_num, text=cleaned_text)
                    pages.append(extracted_page)
                    total_chars += extracted_page.char_count
                except Exception as e:
                    warnings.append(f"Failed to extract text from page {page_num}: {str(e)}")
                    pages.append(ExtractedPage(page_number=page_num, text=""))

            avg_chars = total_chars / max(num_pages, 1)

            # Check if scanned / image-only
            if total_chars < cls.MIN_TOTAL_CHARS or avg_chars < cls.MIN_AVERAGE_CHARS_PER_PAGE:
                return pages, True, [
                    f"Insufficient selectable text detected (avg {round(avg_chars, 1)} chars/page). Document appears scanned and requires OCR."
                ] + warnings

            return pages, False, warnings

        except Exception as e:
            return [], False, [f"Critical error reading PDF structure: {str(e)}"]
