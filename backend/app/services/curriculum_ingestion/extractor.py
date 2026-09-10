import io
import re
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader


KTBS_PUA_CHARMAP = {
    0x20: ' ', 0xF2: '.', 0xF4: ',', 0xF5: ';', 0xF6: ':', 0xE1: '?', 0xFF: '?',
    0xE2: '!', 0xE3: '-', 0xF3: '-', 0xE6: ' : ', 0xF8: '(', 0xF7: ')',
    0xC5: '(', 0xC3: ')', 0x8E: "'", 0x8F: "'", 0x89: '"', 0x8A: '"',
    0xC1: '"', 0xC2: "'",
}


def normalize_extracted_text(text: str) -> str:
    """
    Normalizes extracted text. If text contains custom/InDesign PUA-encoded
    characters (0xF000-0xF0FF) from legacy fonts (e.g. KTBS / Softland),
    decodes them using reverse-byte substitution.
    Standard text without PUA characters passes through untouched.
    """
    if not text:
        return text
    pua_count = sum(1 for c in text if 0xF000 <= ord(c) <= 0xF0FF)
    if pua_count == 0:
        return text

    decoded = []
    for c in text:
        code = ord(c)
        if 0xF000 <= code <= 0xF0FF:
            b = code - 0xF000
            if 0xC6 <= b <= 0xDF:
                decoded.append(chr(ord('A') + (0xDF - b)))
            elif 0xA6 <= b <= 0xBF:
                decoded.append(chr(ord('a') + (0xBF - b)))
            elif 0xE7 <= b <= 0xF0:
                decoded.append(chr(ord('0') + (0xF0 - b)))
            elif b in KTBS_PUA_CHARMAP:
                decoded.append(KTBS_PUA_CHARMAP[b])
            else:
                decoded.append(' ')
        else:
            decoded.append(c)
    return "".join(decoded)


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
                    cleaned_text = normalize_extracted_text(text.replace("\x00", "")).strip()
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
