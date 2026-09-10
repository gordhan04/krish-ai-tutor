import re
from typing import List, Dict, Any, Optional, Tuple
from app.services.curriculum_ingestion.extractor import ExtractedPage


class TOCEntry:
    def __init__(self, entry_type: str, number: int, title: str, target_page: int, toc_page: int):
        self.entry_type = entry_type  # "chapter", "unit", "section", "preface"
        self.number = number
        self.title = title.strip()
        self.target_page = target_page
        self.toc_page = toc_page

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_type": self.entry_type,
            "number": self.number,
            "title": self.title,
            "target_page": self.target_page,
            "toc_page": self.toc_page,
        }


class TOCDetector:
    """
    Detects Table of Contents pages, parses structured syllabus entries (chapters, units, starting pages),
    and determines whether the document is a Prelims-only catalog or contains full chapter bodies.
    """

    TOC_PAGE_HEADER_KEYWORDS = [
        "contents",
        "table of contents",
        "index of chapters",
        "syllabus",
        "brief contents",
    ]

    # Pattern for single-line TOC entries: e.g. "Chapter 4: Combustion and Flame ... 46" or "1. Chemical Effects ... 140"
    SINGLE_LINE_TOC_PATTERN = re.compile(
        r"^(?:(Chapter|Unit|Lesson|Module)\s+(\d+|[IVXLCDM]+)[:\.\-\s]+)?([A-Za-z0-9\s,\:\-'\(\)]+?)\s*[\.\s\-_]{2,}\s*(\d+)\s*$",
        re.IGNORECASE
    )

    # Pattern for standalone chapter/unit header lines in TOC: e.g. "Chapter 1" or "CHAPTER IV"
    TOC_CHAPTER_HEADER = re.compile(
        r"^(?:Chapter|CHAPTER|Unit|UNIT|Lesson|LESSON)\s+(\d+|[IVXLCDM]+)\s*$",
        re.IGNORECASE
    )

    # Pattern for title + page number following chapter header: e.g. "Exploring the Investigative World of Science 01"
    TOC_TITLE_AND_PAGE = re.compile(
        r"^([A-Za-z0-9\s,\:\-'\(\)\?]+?)\s+(\d{1,4})\s*$"
    )

    @classmethod
    def find_toc_pages(cls, pages: List[ExtractedPage]) -> List[ExtractedPage]:
        """Identifies pages that function as Table of Contents."""
        toc_pages = []
        for p in pages:
            lines = p.lines
            if not lines:
                continue

            # Check if any line in the top 5 or bottom 3 contains TOC keywords
            has_toc_keyword = any(
                kw in line.lower() for line in lines[:5] + lines[-3:]
                for kw in cls.TOC_PAGE_HEADER_KEYWORDS
            )

            # Check for density of chapter references or dotted page lines
            ch_refs = sum(1 for line in lines if re.match(r"^(?:Chapter|Unit|Lesson)\s+\d+", line, re.IGNORECASE))
            numbered_endings = sum(1 for line in lines if re.search(r"\s+\d{1,4}$", line))

            if has_toc_keyword or (ch_refs >= 2 and numbered_endings >= 2):
                toc_pages.append(p)

        return toc_pages

    @classmethod
    def parse_toc_entries(cls, toc_pages: List[ExtractedPage]) -> List[TOCEntry]:
        """Parses structured chapter/unit entries from detected TOC pages."""
        entries: List[TOCEntry] = []
        roman_map = {
            "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
            "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16
        }

        for p in toc_pages:
            lines = p.lines
            idx = 0
            while idx < len(lines):
                line = lines[idx].strip()

                # Case A: Two- or multi-line pattern (e.g. "Chapter 1" followed by "Exploring the World ... 01")
                ch_hdr_match = cls.TOC_CHAPTER_HEADER.match(line)
                if ch_hdr_match:
                    raw_num = ch_hdr_match.group(1).upper()
                    ch_num = roman_map.get(raw_num, int(raw_num) if raw_num.isdigit() else len(entries) + 1)
                    
                    # Look ahead up to 3 lines for the line containing the target page number
                    title_parts = []
                    found_target = False
                    for lookahead in range(1, 4):
                        if idx + lookahead >= len(lines):
                            break
                        next_line = lines[idx + lookahead].strip()
                        if cls.TOC_CHAPTER_HEADER.match(next_line):
                            break
                        page_match = re.search(r"\s+(\d{1,4})$", next_line)
                        if page_match:
                            target_page = int(page_match.group(1))
                            title_part = next_line[:page_match.start()].strip()
                            if title_part:
                                title_parts.append(title_part)
                            full_title = "".join(title_parts).strip() if (len(title_parts) > 1 and len(title_parts[0]) <= 3) else " ".join(title_parts).strip()
                            entries.append(TOCEntry(
                                entry_type="chapter",
                                number=ch_num,
                                title=full_title,
                                target_page=target_page,
                                toc_page=p.page_number,
                            ))
                            idx += lookahead + 1
                            found_target = True
                            break
                        else:
                            title_parts.append(next_line)
                    if found_target:
                        continue

                # Case B: Single-line pattern with dotted lead or trailing page
                single_match = cls.SINGLE_LINE_TOC_PATTERN.match(line)
                if single_match:
                    e_type = (single_match.group(1) or "chapter").lower()
                    raw_num = (single_match.group(2) or "").upper()
                    ch_num = roman_map.get(raw_num, int(raw_num) if raw_num.isdigit() else len(entries) + 1)
                    title = single_match.group(3).strip()
                    target_page = int(single_match.group(4))

                    # Filter out non-chapter noise
                    if len(title) > 2 and target_page > 0:
                        entries.append(TOCEntry(
                            entry_type=e_type,
                            number=ch_num,
                            title=title,
                            target_page=target_page,
                            toc_page=p.page_number,
                        ))
                        idx += 1
                        continue

                idx += 1

        return entries

    @classmethod
    def evaluate_document_context(
        cls,
        pages: List[ExtractedPage],
        toc_entries: List[TOCEntry],
    ) -> Dict[str, Any]:
        """
        Evaluates whether this document is a Prelims-only catalog, an excerpt, or a full textbook.
        """
        total_pages = len(pages)
        has_toc = len(toc_entries) > 0

        if not has_toc:
            return {
                "has_toc": False,
                "toc_entries_count": 0,
                "is_prelims_catalog": False,
                "max_target_page": 0,
                "total_document_pages": total_pages,
            }

        max_target_page = max(e.target_page for e in toc_entries)
        # If TOC references pages far beyond document length (e.g. Chapter 13 at p. 210, but doc is 20 pages)
        is_prelims_catalog = max_target_page > total_pages + 5

        return {
            "has_toc": True,
            "toc_entries_count": len(toc_entries),
            "is_prelims_catalog": is_prelims_catalog,
            "max_target_page": max_target_page,
            "total_document_pages": total_pages,
        }
